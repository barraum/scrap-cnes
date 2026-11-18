"""
Módulo de Integração com a API do IBGE (Serviço de Dados e SIDRA).
Fornece dados de População Residente (Censo Demográfico 2022) e Estimativas Populacionais,
além do cálculo de indicadores de cobertura e dimensionamento de equipes da Atenção Básica (SUS/PNAB).
"""

import urllib.request
import ssl
import json
import gzip
import unicodedata
import re
import math
from typing import Dict, Any, List, Optional, Tuple


def normalize_str(s: str) -> str:
    """Normaliza texto removendo acentos e caracteres especiais para casamento de nomes de cidades."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(s))
    ascii_str = nfkd.encode("ASCII", "ignore").decode("ASCII").upper()
    return re.sub(r"[^A-Z0-9 ]", "", ascii_str).strip()


class IBGEClient:
    """
    Cliente HTTP para APIs oficiais do IBGE:
    - Agregado 4714: População Residente no Censo Demográfico 2022.
    - Agregado 6579: Estimativas Anuais de População Residente.
    """

    BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ScrapCNES/1.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate"
        }

    def _make_request(self, url: str) -> Any:
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as resp:
                raw = resp.read()
                if resp.info().get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except Exception as e:
            print(f"[IBGEClient Error] Falha ao consultar {url}: {e}")
            return None

    def fetch_sp_municipalities_population(self) -> Dict[str, Dict[str, Any]]:
        """
        Extrai de uma só vez a população (Censo 2022 e Estimativa mais recente)
        de TODOS os 645 municípios do Estado de São Paulo.
        Retorna dicionário indexado pelo código IBGE de 6 dígitos.
        """
        # 1. Censo 2022 (Agregado 4714, Variável 93) para todo o Estado de SP (N3[35])
        url_censo = f"{self.BASE_URL}/4714/periodos/2022/variaveis/93?localidades=N6[N3[35]]"
        censo_data = self._make_request(url_censo)

        pop_map: Dict[str, Dict[str, Any]] = {}

        if censo_data and isinstance(censo_data, list) and len(censo_data) > 0:
            series = censo_data[0].get("resultados", [{}])[0].get("series", [])
            for s in series:
                loc = s.get("localidade", {})
                cod7 = str(loc.get("id", ""))
                cod6 = cod7[:6]
                nome_bruto = loc.get("nome", "").replace(" - SP", "").strip()
                val_censo = s.get("serie", {}).get("2022")
                try:
                    p_censo = int(val_censo) if val_censo and val_censo != "-" else 0
                except (ValueError, TypeError):
                    p_censo = 0

                pop_map[cod6] = {
                    "codigo_ibge_6": cod6,
                    "codigo_ibge_7": cod7,
                    "municipio": nome_bruto,
                    "uf": "SP",
                    "pop_censo_2022": p_censo,
                    "pop_estimada": p_censo,
                    "ano_estimativa": "2022"
                }

        # 2. Estimativa mais recente (Agregado 6579, Variável 9324)
        url_est = f"{self.BASE_URL}/6579/periodos/-1/variaveis/9324?localidades=N6[N3[35]]"
        est_data = self._make_request(url_est)

        if est_data and isinstance(est_data, list) and len(est_data) > 0:
            resultados = est_data[0].get("resultados", [{}])[0]
            series_est = resultados.get("series", [])
            for s in series_est:
                cod7 = str(s.get("localidade", {}).get("id", ""))
                cod6 = cod7[:6]
                serie_dict = s.get("serie", {})
                if serie_dict:
                    periodo_recente = list(serie_dict.keys())[-1]
                    val_est = serie_dict.get(periodo_recente)
                    try:
                        p_est = int(val_est) if val_est and val_est != "-" else 0
                    except (ValueError, TypeError):
                        p_est = 0

                    if cod6 in pop_map and p_est > 0:
                        pop_map[cod6]["pop_estimada"] = p_est
                        pop_map[cod6]["ano_estimativa"] = str(periodo_recente)

        return pop_map

    def fetch_single_municipality_population(self, codigo_ibge_ou_nome: str) -> Optional[Dict[str, Any]]:
        """
        Consulta a população de um único município fora de SP ou consulta pontual.
        Aceita código IBGE de 6 ou 7 dígitos (ou nome do município como fallback).
        """
        clean_input = str(codigo_ibge_ou_nome).strip()
        if not clean_input:
            return None

        target_cod6 = ""
        data = None

        if clean_input.isdigit():
            if len(clean_input) == 7:
                url = f"{self.BASE_URL}/4714/periodos/2022/variaveis/93?localidades=N6[{clean_input}]"
                data = self._make_request(url)
            elif len(clean_input) == 6:
                target_cod6 = clean_input
                uf_code = clean_input[:2]
                url = f"{self.BASE_URL}/4714/periodos/2022/variaveis/93?localidades=N6[N3[{uf_code}]]"
                data = self._make_request(url)
        else:
            # Fallback por nome: busca na lista nacional de municípios do IBGE para descobrir o código de 7 dígitos
            loc_url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
            muns = self._make_request(loc_url)
            if isinstance(muns, list):
                norm_target = normalize_str(clean_input)
                match = next((m for m in muns if normalize_str(m.get("nome", "")) == norm_target), None)
                if match and match.get("id"):
                    cod7_found = str(match["id"])
                    url = f"{self.BASE_URL}/4714/periodos/2022/variaveis/93?localidades=N6[{cod7_found}]"
                    data = self._make_request(url)

        if data and isinstance(data, list) and len(data) > 0:
            series = data[0].get("resultados", [{}])[0].get("series", [])
            selected = None
            if target_cod6:
                selected = next(
                    (s for s in series if str(s.get("localidade", {}).get("id", ""))[:6] == target_cod6),
                    None
                )
            elif series:
                selected = series[0]

            if selected:
                cod7 = str(selected.get("localidade", {}).get("id", ""))
                nome_raw = selected.get("localidade", {}).get("nome", "")
                nome = nome_raw.split(" - ")[0].strip()
                uf = nome_raw.split(" - ")[-1].strip() if " - " in nome_raw else ("SP" if cod7.startswith("35") else "")
                val = selected.get("serie", {}).get("2022")
                p = int(val) if val and val != "-" else 0
                return {
                    "codigo_ibge_6": cod7[:6],
                    "codigo_ibge_7": cod7,
                    "municipio": nome,
                    "uf": uf,
                    "pop_censo_2022": p,
                    "pop_estimada": p,
                    "ano_estimativa": "2022"
                }

        return None

    @staticmethod
    def calculate_health_coverage(
        populacao: int,
        qtd_esf: int,
        qtd_eap: int = 0,
        qtd_esb: int = 0,
        qtd_emulti: int = 0,
        param_esf: int = 3000,
        param_eap: int = 2000,
        param_esb: int = 3500
    ) -> Dict[str, Any]:
        """
        Calcula os indicadores oficiais de cobertura e dimensionamento da Atenção Básica (SUS/PNAB):
        - Parâmetro PNAB (Ministério da Saúde): Média de 2.000 a 3.500 pessoas por ESF (referência padrão: 3.000 hab/ESF).
        - Parâmetro EAP: Referência de 2.000 pessoas por EAP (compatível com cargas de 20h/30h).
        - Parâmetro ESB: Referência de 3.500 pessoas por Equipe de Saúde Bucal.
        """
        pop = max(populacao, 1)

        # Capacidade potencial de atendimento
        cap_esf = qtd_esf * param_esf
        cap_eap = qtd_eap * param_eap
        cap_total_ab = cap_esf + cap_eap
        cap_esb = qtd_esb * param_esb

        # Percentuais de Cobertura Potencial (limitados a 100% para evitar distorções estatísticas)
        cobertura_esf_pct = min(100.0, round((cap_esf / pop) * 100.0, 1))
        cobertura_total_pct = min(100.0, round((cap_total_ab / pop) * 100.0, 1))
        cobertura_esb_pct = min(100.0, round((cap_esb / pop) * 100.0, 1))

        # População coberta e desassistida estimada
        pop_coberta = min(pop, cap_total_ab)
        pop_descoberta = max(0, pop - cap_total_ab)

        # Déficit estimado de equipes para atingir 100% de cobertura
        deficit_esf = max(0, math.ceil(pop_descoberta / param_esf)) if pop_descoberta > 0 else 0

        # Habitantes por equipe
        hab_por_esf = round(pop / qtd_esf) if qtd_esf > 0 else None
        hab_por_equipe_total = round(pop / (qtd_esf + qtd_eap)) if (qtd_esf + qtd_eap) > 0 else None
        hab_por_esb = round(pop / qtd_esb) if qtd_esb > 0 else None

        # Diagnóstico Qualitativo de Cobertura
        if cobertura_total_pct >= 90.0:
            diagnostico = "🟢 Ótima / Plena (>= 90%)"
            cor = "#28a745"
        elif cobertura_total_pct >= 70.0:
            diagnostico = "🟡 Regular / Boa (70% - 89%)"
            cor = "#ffc107"
        elif cobertura_total_pct >= 50.0:
            diagnostico = "🟠 Parcial / Alerta (50% - 69%)"
            cor = "#fd7e14"
        else:
            diagnostico = "🔴 Baixa / Crítica (< 50%)"
            cor = "#dc3545"

        return {
            "populacao": populacao,
            "qtd_esf": qtd_esf,
            "qtd_eap": qtd_eap,
            "total_equipes_ab": qtd_esf + qtd_eap,
            "qtd_esb": qtd_esb,
            "qtd_emulti": qtd_emulti,
            "hab_por_esf": hab_por_esf,
            "hab_por_equipe_total": hab_por_equipe_total,
            "hab_por_esb": hab_por_esb,
            "cobertura_esf_pct": cobertura_esf_pct,
            "cobertura_total_pct": cobertura_total_pct,
            "cobertura_esb_pct": cobertura_esb_pct,
            "pop_coberta": pop_coberta,
            "pop_descoberta": pop_descoberta,
            "deficit_esf": deficit_esf,
            "diagnostico": diagnostico,
            "cor_diagnostico": cor
        }
