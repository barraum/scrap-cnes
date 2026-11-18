import urllib.request
import ssl
import json
import time
from typing import Dict, Any, Optional, List, Callable

class CNESClient:
    """
    Cliente HTTP leve e polido para comunicação com a API REST do CNES (DATASUS).
    Desenvolvido para requisições pontuais e seguras por código CNES.
    """
    BASE_URL = "https://cnes.datasus.gov.br/services"
    
    def __init__(self, delay_between_requests: float = 0.15, timeout: int = 15):
        self.delay = delay_between_requests
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://cnes.datasus.gov.br/'
        }

    def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None, retries: int = 2) -> Any:
        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v)
            if query:
                url += f"?{query}"
                
        req = urllib.request.Request(url, headers=self.headers)
        
        for attempt in range(retries + 1):
            if self.delay > 0:
                time.sleep(self.delay)

            try:
                with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as resp:
                    raw = resp.read().decode('utf-8')
                    if not raw or not raw.strip():
                        return {}
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                if e.code in (400, 404):
                    return [] if 'estabelecimentos-' in endpoint else {}
                if attempt == retries:
                    print(f"[CNESClient Warning] HTTP {e.code} para {endpoint}")
                    return [] if 'estabelecimentos-' in endpoint else {}
            except Exception as e:
                if attempt == retries:
                    print(f"[CNESClient Error] Falha ao acessar {endpoint}: {e}")
                    return [] if 'estabelecimentos-' in endpoint else {}

    def resolve_co_unidade(self, cnes_or_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolve o código CNES (7 dígitos) ou ID da unidade (13 dígitos) para obter os dados básicos e o ID único (coUnidade).
        """
        clean_input = str(cnes_or_id).strip()
        
        # 1. Se for ID completo de 13 dígitos
        if len(clean_input) == 13 and clean_input.isdigit():
            res = self._make_request(f"estabelecimentos/{clean_input}")
            if isinstance(res, dict) and res.get('id'):
                return res
        
        # 2. Busca por código CNES (7 dígitos)
        pesquisa = self._make_request(f"estabelecimentos?cnes={clean_input}")
        if isinstance(pesquisa, list) and len(pesquisa) > 0:
            first_found = pesquisa[0]
            co_unidade = str(first_found['id'])
            full_basic = self._make_request(f"estabelecimentos/{co_unidade}")
            if isinstance(full_basic, dict) and full_basic.get('id'):
                return full_basic
            return first_found
            
        # 3. Fallback: tentativa de busca direta caso o usuário tenha passado o coUnidade diretamente
        fallback = self._make_request(f"estabelecimentos/{clean_input}")
        if isinstance(fallback, dict) and fallback.get('id'):
            return fallback

        return None

    def fetch_full_establishment(self, cnes_or_id: str, competencia: Optional[str] = None) -> Dict[str, Any]:
        """
        Extrai a totalidade dos dados públicos do estabelecimento de saúde para a competência indicada (ou atual).
        Retorna um dicionário estruturado com todos os 14 módulos.
        """
        base_info = self.resolve_co_unidade(cnes_or_id)
        if not base_info:
            raise ValueError(f"Estabelecimento com CNES/ID '{cnes_or_id}' não foi encontrado no DATASUS.")
            
        co_unidade = str(base_info['id'])
        cnes_code = str(base_info.get('cnes', cnes_or_id))
        
        comp_clean = str(competencia).strip() if competencia else None
        param_comp = {'competencia': comp_clean} if comp_clean and comp_clean.isdigit() and len(comp_clean) == 6 else None
        
        data = {
            'metadata': {
                'cnes': cnes_code,
                'coUnidade': co_unidade,
                'nomeFantasia': base_info.get('noFantasia'),
                'razaoSocial': base_info.get('noEmpresarial'),
                'competencia': competencia or 'Atual',
                'municipio': base_info.get('noMunicipio'),
                'uf': base_info.get('uf'),
            },
            'dados_gerais': base_info,
            'informacoes_gerais': self._make_request(f"estabelecimentos/informacoesGerais/{co_unidade}", param_comp),
            'profissionais': self._make_request(f"estabelecimentos-profissionais/{co_unidade}", param_comp),
            'profissionais_desligados': self._make_request(f"estabelecimentos-profissionais/desligados/{co_unidade}", param_comp),
            'leitos': self._make_request(f"estabelecimentos-hospitalar/{co_unidade}", param_comp),
            'equipamentos': self._make_request(f"estabelecimentos-equipamento/{co_unidade}", param_comp),
            'servicos_classificacao': self._make_request(f"estabelecimentos/servicos-classificacao/{co_unidade}", param_comp),
            'servicos_apoio': self._make_request(f"estabelecimentos/servicos-apoio/{co_unidade}", param_comp),
            'instalacoes': self._make_request(f"estabelecimentos/instalacoes/{co_unidade}", param_comp),
            'comissoes': self._make_request(f"estabelecimentos/comissoes/{co_unidade}", param_comp),
            'habilitacoes': self._make_request(f"estabelecimentos-habilitacoes/{co_unidade}", param_comp),
            'incentivos': self._make_request(f"estabelecimentos-incentivo/{co_unidade}", param_comp),
            'equipes': self._make_request(f"estabelecimentos-equipes/{co_unidade}", param_comp),
            'mantenedora': self._make_request(f"estabelecimentos-mantenedora/{co_unidade}", param_comp),
        }
        
        return data

    # -------------------------------------------------------------------------
    # Métodos para Consulta por Município (extração em lote)
    # -------------------------------------------------------------------------

    def list_by_municipality(
        self,
        codigo_municipio: str,
        estado: Optional[str] = None,
        gestao: Optional[str] = None,
        nat_juridica: Optional[str] = None,
        atende_sus: Optional[str] = None,
        status: Optional[str] = "1",
    ) -> List[Dict[str, Any]]:
        """
        Lista TODOS os estabelecimentos de um município via API CNES.
        Retorna uma lista com dados básicos (sem classificação de tipo).

        Args:
            codigo_municipio: Código IBGE do município (6 dígitos, sem DV).
            estado: Código UF (ex: '35' para SP). Opcional.
            gestao: Filtro de gestão ('M'=Municipal, 'E'=Estadual, 'D'=Dupla). Opcional.
            nat_juridica: Filtro natureza jurídica ('1'=Pub, '2'=Priv). Opcional.
            atende_sus: Filtro SUS ('S'=Sim, 'N'=Não). Opcional.
            status: '1' para ativos (padrão), None para todos.
        """
        params = {'municipio': str(codigo_municipio).strip()}
        if estado:
            params['estado'] = estado
        if gestao:
            params['gestao'] = gestao
        if nat_juridica:
            params['natJuridica'] = nat_juridica
        if atende_sus:
            params['atendeSus'] = atende_sus
        if status:
            params['status'] = status

        result = self._make_request("estabelecimentos", params)
        if isinstance(result, list):
            # Filtragem adicional no cliente para garantir reduções exatas caso a API do CNES ignore alguns parâmetros de busca
            filtered = result
            if gestao:
                filtered = [e for e in filtered if str(e.get('gestao', '')).strip() == gestao]
            if nat_juridica:
                filtered = [e for e in filtered if str(e.get('natJuridica', '')).strip() == nat_juridica]
            if atende_sus:
                filtered = [e for e in filtered if str(e.get('atendeSus', '')).strip() == atende_sus]
            return filtered
        return []

    def fetch_establishment_detail(self, co_unidade: str) -> Optional[Dict[str, Any]]:
        """
        Busca os dados detalhados de um único estabelecimento pelo seu ID (coUnidade de 13 dígitos).
        Retorna campos como dsTipoEstabelecimento, dsTpUnidade, endereço, coordenadas, etc.
        """
        result = self._make_request(f"estabelecimentos/{co_unidade}")
        if isinstance(result, dict) and result.get('id'):
            return result
        return None

    def fetch_municipality_details(
        self,
        establishments: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enriquece uma lista de estabelecimentos buscando o detalhe de cada um.
        Adiciona campos de classificação/tipo, endereço, coordenadas, etc.

        Args:
            establishments: Lista retornada por list_by_municipality().
            progress_callback: Função opcional chamada a cada item processado.
                               Recebe (indice_atual, total, nome_fantasia).

        Returns:
            Lista de dicionários com dados completos (merge da listagem + detalhe).
        """
        enriched = []
        total = len(establishments)

        for i, est in enumerate(establishments):
            co_unidade = str(est.get('id', ''))
            nome = est.get('noFantasia', 'Desconhecido')

            if progress_callback:
                progress_callback(i, total, nome)

            detail = self.fetch_establishment_detail(co_unidade)

            if detail:
                # Mescla dados básicos com detalhes
                merged = {**est, **detail}
            else:
                # Mantém só os dados básicos se o detalhe falhar
                merged = {**est}
                merged['dsTipoEstabelecimento'] = 'NÃO DISPONÍVEL'
                merged['coTipoEstabelecimento'] = ''
                merged['dsTpUnidade'] = ''

            enriched.append(merged)

        # Progresso final
        if progress_callback:
            progress_callback(total, total, "Concluído")

        return enriched

    def fetch_competencia_history(
        self,
        cnes_code: str,
        competencias: List[str],
        db_instance: Any,
        delay_between_requests: float = 0.3,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extrai em lote os dados de um CNES para um intervalo de competências (ex: de 2020 a 2026)
        com delay configurável entre requisições para respeitar os servidores do DATASUS.
        Salva cada competência automaticamente no banco SQLite local.
        """
        saved_snapshots = []
        total = len(competencias)

        # Atualizar temporariamente o delay do cliente se informado
        original_delay = self.delay
        if delay_between_requests is not None and delay_between_requests >= 0:
            self.delay = delay_between_requests

        try:
            for i, comp in enumerate(competencias):
                if progress_callback:
                    progress_callback(i, total, f"Competência {comp}")
                try:
                    data = self.fetch_full_establishment(cnes_code, competencia=comp)
                    if data and data.get('dados_gerais'):
                        db_instance.save_snapshot(data)
                        saved_snapshots.append(data)
                except Exception as e:
                    print(f"[CNESClient Warning] Não foi possível extrair a competência {comp} para o CNES {cnes_code}: {e}")

            if progress_callback:
                progress_callback(total, total, "Extração de competências concluída!")
        finally:
            self.delay = original_delay

        return saved_snapshots

    def fetch_establishment_professionals(self, co_unidade: str, competencia: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca a lista de profissionais vinculados a um único estabelecimento pelo seu ID (coUnidade de 13 dígitos).
        """
        comp_clean = str(competencia).strip() if competencia else None
        param_comp = {'competencia': comp_clean} if comp_clean and comp_clean.isdigit() and len(comp_clean) == 6 else None
        result = self._make_request(f"estabelecimentos-profissionais/{co_unidade}", param_comp)
        if isinstance(result, list):
            return result
        return []

    def fetch_municipality_professionals(
        self,
        establishments: List[Dict[str, Any]],
        competencia: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extrai em lote todos os profissionais dos estabelecimentos informados de um município.
        Enriquece cada registro profissional com dados do estabelecimento de atuação.

        Args:
            establishments: Lista de estabelecimentos retornada por list_by_municipality().
            competencia: Competência desejada (opcional, AAAAMM).
            progress_callback: Função opcional chamada a cada estabelecimento processado.

        Returns:
            Lista consolidada de dicionários contendo profissionais e dados do estabelecimento.
        """
        all_professionals = []
        total = len(establishments)

        for i, est in enumerate(establishments):
            co_unidade = str(est.get('id', ''))
            cnes_code = str(est.get('cnes', ''))
            nome_fantasia = str(est.get('noFantasia', ''))
            razao_social = str(est.get('noEmpresarial', ''))

            if progress_callback:
                progress_callback(i, total, nome_fantasia or cnes_code)

            profs = self.fetch_establishment_professionals(co_unidade, competencia=competencia)

            if profs and isinstance(profs, list):
                for p in profs:
                    rec = {
                        **p,
                        'cnes': cnes_code,
                        'coUnidade': co_unidade,
                        'noFantasia': nome_fantasia,
                        'noEmpresarial': razao_social,
                        'noMunicipio': est.get('noMunicipio', ''),
                        'uf': est.get('uf', ''),
                        'gestao': est.get('gestao', ''),
                        'natJuridica': est.get('natJuridica', ''),
                    }
                    all_professionals.append(rec)

        if progress_callback:
            progress_callback(total, total, "Extração de profissionais concluída!")

        return all_professionals

    def fetch_establishment_teams(self, co_unidade: str, competencia: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Consulta as equipes de saúde vinculadas a um estabelecimento (coUnidade de 13 dígitos).
        Retorna registros com tpEquipe, dsEquipe, coEquipe (INE), nomeEquipe, datas de ativação/desativação, etc.
        """
        comp_clean = str(competencia).strip() if competencia else None
        param_comp = {'competencia': comp_clean} if comp_clean and comp_clean.isdigit() and len(comp_clean) == 6 else None
        result = self._make_request(f"estabelecimentos-equipes/{co_unidade}", param_comp)
        if isinstance(result, list):
            return result
        return []

    def fetch_municipality_teams(
        self,
        establishments: List[Dict[str, Any]],
        competencia: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extrai em lote todas as equipes de saúde (ESF, EAP, ESB, EMULTI, etc.) dos estabelecimentos informados.
        Enriquece cada registro de equipe com os dados da unidade básica ou estabelecimento de saúde.

        Args:
            establishments: Lista de estabelecimentos (geralmente filtrados por administração pública / SUS).
            competencia: Competência desejada (opcional, AAAAMM).
            progress_callback: Callback para acompanhamento do progresso em tempo real.

        Returns:
            Lista consolidada de dicionários contendo os dados de cada equipe e da respectiva unidade.
        """
        all_teams = []
        total = len(establishments)

        for i, est in enumerate(establishments):
            co_unidade = str(est.get('id', ''))
            cnes_code = str(est.get('cnes', ''))
            nome_fantasia = str(est.get('noFantasia', ''))
            razao_social = str(est.get('noEmpresarial', ''))

            if progress_callback:
                progress_callback(i, total, nome_fantasia or cnes_code)

            teams = self.fetch_establishment_teams(co_unidade, competencia=competencia)

            if teams and isinstance(teams, list):
                for t in teams:
                    dt_desat = t.get('dtDesativacao')
                    is_ativa = (dt_desat is None or str(dt_desat).strip() == '' or str(dt_desat).strip().lower() == 'none')
                    rec = {
                        **t,
                        'cnes': cnes_code,
                        'coUnidade': co_unidade,
                        'competencia': competencia or 'Atual',
                        'noFantasia': nome_fantasia,
                        'noEmpresarial': razao_social,
                        'noMunicipio': est.get('noMunicipio', ''),
                        'uf': est.get('uf', ''),
                        'gestao': est.get('gestao', ''),
                        'natJuridica': est.get('natJuridica', ''),
                        'status': 'Ativa' if is_ativa else 'Desativada'
                    }
                    all_teams.append(rec)

        if progress_callback:
            progress_callback(total, total, "Extração de equipes concluída!")

        return all_teams




