import sqlite3
import json
import os
import gzip
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

class CNESDatabase:
    """
    Gerenciador de banco de dados SQLite local para histórico por CNES e Competência (YYYYMM).
    Utiliza caminhos relativos para funcionar em qualquer máquina/usuário Windows.
    Suporta inicialização automática via snapshot compactado (.gz de ~7.6MB) para deploy na nuvem.
    """
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Resolve o caminho do banco relativo à raiz do projeto
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "historico_cnes.db")
            
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Auto-descompactação na nuvem (Streamlit Community Cloud):
        # Se o banco .db não existir mas existir o snapshot compactado .gz, descompacta em ~0.2s
        gz_path = self.db_path + ".gz"
        if not os.path.exists(self.db_path) and os.path.exists(gz_path):
            try:
                with gzip.open(gz_path, "rb") as f_in:
                    with open(self.db_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            except Exception as e:
                print(f"[CNESDatabase] Erro ao descompactar snapshot inicial (.gz): {e}")

        self._init_db()

    @classmethod
    def compress_db(cls, db_path: Optional[str] = None) -> str:
        """
        Compacta o banco de dados SQLite local em um arquivo .gz de ~7.6MB pronto para o Git / Nuvem.
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "historico_cnes.db")
        gz_path = db_path + ".gz"
        if os.path.exists(db_path):
            with open(db_path, "rb") as f_in:
                with gzip.open(gz_path, "wb", compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
        return gz_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de Estabelecimentos cadastrados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS estabelecimentos (
                    cnes TEXT PRIMARY KEY,
                    co_unidade TEXT,
                    nome_fantasia TEXT,
                    razao_social TEXT,
                    municipio TEXT,
                    uf TEXT,
                    ultima_atualizacao TIMESTAMP
                )
            """)
            
            # Tabela de Snapshots Históricos por Competência
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cnes TEXT,
                    competencia TEXT,
                    data_extracao TIMESTAMP,
                    num_profissionais INTEGER,
                    num_leitos INTEGER,
                    num_equipamentos INTEGER,
                    num_servicos INTEGER,
                    json_payload TEXT,
                    UNIQUE(cnes, competencia),
                    FOREIGN KEY(cnes) REFERENCES estabelecimentos(cnes)
                )
            """)

            # Tabela de Profissionais de Saúde Persistente
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profissionais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cnes TEXT,
                    co_unidade TEXT,
                    competencia TEXT,
                    nome TEXT,
                    cns TEXT,
                    cbo TEXT,
                    ds_cbo TEXT,
                    ch_amb INTEGER,
                    ch_hosp INTEGER,
                    ch_outros INTEGER,
                    ch_total INTEGER,
                    vinculacao TEXT,
                    vinculo TEXT,
                    sub_vinculo TEXT,
                    atende_sus TEXT,
                    nome_fantasia TEXT,
                    razao_social TEXT,
                    municipio TEXT,
                    uf TEXT,
                    data_extracao TIMESTAMP,
                    UNIQUE(cnes, competencia, cns, cbo) ON CONFLICT REPLACE
                )
            """)

            # Tabela de Equipes de Saúde Persistente (Repositório Local por Município e Competência)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cnes TEXT,
                    co_unidade TEXT,
                    competencia TEXT,
                    co_equipe TEXT,
                    seq_equipe TEXT,
                    nome_equipe TEXT,
                    tp_equipe TEXT,
                    ds_equipe TEXT,
                    co_area TEXT,
                    ds_area TEXT,
                    dt_ativacao TEXT,
                    dt_desativacao TEXT,
                    quilombola TEXT,
                    assentada TEXT,
                    geral TEXT,
                    escola TEXT,
                    pronasci TEXT,
                    indigena TEXT,
                    ribeirinha TEXT,
                    complem TEXT,
                    nome_fantasia TEXT,
                    razao_social TEXT,
                    municipio TEXT,
                    uf TEXT,
                    gestao TEXT,
                    nat_juridica TEXT,
                    status TEXT,
                    data_extracao TIMESTAMP,
                    UNIQUE(cnes, competencia, co_equipe) ON CONFLICT REPLACE
                )
            """)

            # Índices para consultas de alta performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prof_cns ON profissionais(cns)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prof_nome ON profissionais(nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prof_mun_comp ON profissionais(municipio, competencia)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prof_cbo ON profissionais(cbo)")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eq_cnes ON equipes(cnes)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eq_ine ON equipes(co_equipe)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eq_mun_comp ON equipes(municipio, competencia)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eq_tipo ON equipes(tp_equipe)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eq_status ON equipes(status)")

            # Tabela de População IBGE (Censo 2022 & Estimativas)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS populacao_ibge (
                    codigo_ibge_6 TEXT PRIMARY KEY,
                    codigo_ibge_7 TEXT,
                    municipio TEXT,
                    uf TEXT,
                    pop_censo_2022 INTEGER,
                    pop_estimada INTEGER,
                    ano_estimativa TEXT,
                    data_atualizacao TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pop_mun ON populacao_ibge(municipio)")
            conn.commit()

    def save_snapshot(self, full_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Salva ou atualiza o snapshot de um estabelecimento no banco local.
        """
        meta = full_data.get('metadata', {})
        cnes = meta.get('cnes')
        competencia = meta.get('competencia') or datetime.now().strftime("%Y%m")
        co_unidade = meta.get('coUnidade')
        nome_fantasia = meta.get('nomeFantasia')
        razao_social = meta.get('razaoSocial')
        municipio = meta.get('municipio')
        uf = meta.get('uf')
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not cnes:
            return False, "CNES ausente no payload."

        profissionais = full_data.get('profissionais', [])
        leitos = full_data.get('leitos', [])
        equipamentos = full_data.get('equipamentos', [])
        servicos = full_data.get('servicos_classificacao', [])

        num_prof = len(profissionais) if isinstance(profissionais, list) else 0
        num_leit = sum(int(l.get('qtExistente', 0)) for l in leitos) if isinstance(leitos, list) else 0
        num_equip = len(equipamentos) if isinstance(equipamentos, list) else 0
        num_serv = len(servicos) if isinstance(servicos, list) else 0

        payload_json = json.dumps(full_data, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Upsert na tabela estabelecimentos
            cursor.execute("""
                INSERT INTO estabelecimentos (cnes, co_unidade, nome_fantasia, razao_social, municipio, uf, ultima_atualizacao)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cnes) DO UPDATE SET
                    co_unidade=excluded.co_unidade,
                    nome_fantasia=excluded.nome_fantasia,
                    razao_social=excluded.razao_social,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    ultima_atualizacao=excluded.ultima_atualizacao
            """, (cnes, co_unidade, nome_fantasia, razao_social, municipio, uf, now_str))

            # Upsert na tabela historico_snapshots
            cursor.execute("""
                INSERT INTO historico_snapshots 
                (cnes, competencia, data_extracao, num_profissionais, num_leitos, num_equipamentos, num_servicos, json_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cnes, competencia) DO UPDATE SET
                    data_extracao=excluded.data_extracao,
                    num_profissionais=excluded.num_profissionais,
                    num_leitos=excluded.num_leitos,
                    num_equipamentos=excluded.num_equipamentos,
                    num_servicos=excluded.num_servicos,
                    json_payload=excluded.json_payload
            """, (cnes, competencia, now_str, num_prof, num_leit, num_equip, num_serv, payload_json))

            conn.commit()

        return True, f"Snapshot CNES {cnes} (Competência {competencia}) salvo com sucesso no banco de histórico."

    def list_estabelecimentos(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, COUNT(h.competencia) as total_competencias, MAX(h.competencia) as ultima_comp
                FROM estabelecimentos e
                LEFT JOIN historico_snapshots h ON e.cnes = h.cnes
                GROUP BY e.cnes
                ORDER BY e.nome_fantasia
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def list_competencias(self, cnes: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT competencia, data_extracao, num_profissionais, num_leitos, num_equipamentos, num_servicos
                FROM historico_snapshots
                WHERE cnes = ?
                ORDER BY competencia DESC
            """, (cnes,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_snapshot(self, cnes: str, competencia: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT json_payload FROM historico_snapshots
                WHERE cnes = ? AND competencia = ?
            """, (cnes, competencia))
            row = cursor.fetchone()
            if row and row['json_payload']:
                return json.loads(row['json_payload'])
            return None

    def compare_competencias(self, cnes: str, comp_ant: str, comp_nova: str) -> Dict[str, Any]:
        """
        Gera relatório diferencial entre duas competências do mesmo estabelecimento.
        """
        snap_ant = self.get_snapshot(cnes, comp_ant)
        snap_nov = self.get_snapshot(cnes, comp_nova)

        if not snap_ant or not snap_nov:
            return {"erro": "Uma ou ambas as competências não foram encontradas para comparação."}

        # Profissionais
        profs_ant = {f"{p.get('cns')}_{p.get('cbo')}": p for p in snap_ant.get('profissionais', [])}
        profs_nov = {f"{p.get('cns')}_{p.get('cbo')}": p for p in snap_nov.get('profissionais', [])}

        novos_profs = [p for k, p in profs_nov.items() if k not in profs_ant]
        removidos_profs = [p for k, p in profs_ant.items() if k not in profs_nov]

        # Leitos
        leitos_ant = sum(int(l.get('qtExistente', 0)) for l in snap_ant.get('leitos', []))
        leitos_nov = sum(int(l.get('qtExistente', 0)) for l in snap_nov.get('leitos', []))
        leitos_sus_ant = sum(int(l.get('qtSus', 0)) for l in snap_ant.get('leitos', []))
        leitos_sus_nov = sum(int(l.get('qtSus', 0)) for l in snap_nov.get('leitos', []))

        return {
            "cnes": cnes,
            "comp_anterior": comp_ant,
            "comp_nova": comp_nova,
            "profissionais": {
                "total_anterior": len(profs_ant),
                "total_novo": len(profs_nov),
                "diferenca": len(profs_nov) - len(profs_ant),
                "novos_ingressos": novos_profs,
                "desligados": removidos_profs
            },
            "leitos": {
                "total_existente_anterior": leitos_ant,
                "total_existente_novo": leitos_nov,
                "diferenca_existente": leitos_nov - leitos_ant,
                "sus_anterior": leitos_sus_ant,
                "sus_novo": leitos_sus_nov,
                "diferenca_sus": leitos_sus_nov - leitos_sus_ant,
            }
        }

    def get_leitos_evolution_history(self, cnes: str) -> List[Dict[str, Any]]:
        """
        Retorna todos os registros históricos de leitos salvos para um CNES, 
        desaninhando os leitos por competência (YYYYMM) com distinção entre SUS, Não-SUS e Totais.
        """
        records = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT competencia, json_payload FROM historico_snapshots
                WHERE cnes = ?
                ORDER BY competencia ASC
            """, (cnes,))
            rows = cursor.fetchall()
            
            for r in rows:
                comp = r['competencia']
                if not r['json_payload']:
                    continue
                try:
                    payload = json.loads(r['json_payload'])
                    leitos = payload.get('leitos', [])
                    if isinstance(leitos, list):
                        for l in leitos:
                            qt_exist = int(l.get('qtExistente', 0))
                            qt_sus = int(l.get('qtSus', 0))
                            qt_nao_sus = int(l.get('qtNaoSus', max(0, qt_exist - qt_sus)))
                            records.append({
                                'competencia': str(comp),
                                'cnes': str(cnes),
                                'coLeito': str(l.get('coLeito', '')),
                                'dsLeito': str(l.get('dsLeito', 'NÃO INFORMADO')),
                                'dsAtributo': str(l.get('dsAtributo', 'OUTROS')),
                                'qtExistente': qt_exist,
                                'qtSus': qt_sus,
                                'qtNaoSus': qt_nao_sus
                            })
                except Exception as e:
                    print(f"[CNESDatabase Error] Erro ao decodificar leitos na competência {comp}: {e}")
                    
        return records

    def save_professionals(
        self,
        records: List[Dict[str, Any]],
        competencia: Optional[str] = None,
        default_municipio: Optional[str] = None,
        default_uf: Optional[str] = None
    ) -> int:
        """
        Salva ou atualiza uma lista de profissionais no banco SQLite local em lote.
        Retorna a quantidade de registros inseridos/atualizados.
        """
        if not records:
            return 0

        comp_default = competencia or datetime.now().strftime("%Y%m")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_to_insert = []

        for p in records:
            ch_amb = int(p.get('chAmb', 0) or 0)
            ch_hosp = int(p.get('chHosp', 0) or 0)
            ch_out = int(p.get('chOutros', 0) or 0)
            ch_tot = ch_amb + ch_hosp + ch_out

            comp_val = p.get('competencia') or comp_default
            mun_val = p.get('noMunicipio') or p.get('municipio') or default_municipio or ''
            uf_val = p.get('uf') or default_uf or ''

            data_to_insert.append((
                str(p.get('cnes', '')),
                str(p.get('coUnidade', '')),
                str(comp_val),
                str(p.get('nome', '')).strip(),
                str(p.get('cns', '')).strip(),
                str(p.get('cbo', '')).strip(),
                str(p.get('dsCbo', '')).strip(),
                ch_amb,
                ch_hosp,
                ch_out,
                ch_tot,
                str(p.get('vinculacao', '')).strip(),
                str(p.get('vinculo', '')).strip(),
                str(p.get('subVinculo', '')).strip(),
                str(p.get('tpSusNaoSus', 'S')).strip(),
                str(p.get('noFantasia', '')).strip(),
                str(p.get('noEmpresarial', '')).strip(),
                str(mun_val).strip(),
                str(uf_val).strip(),
                now_str
            ))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO profissionais (
                    cnes, co_unidade, competencia, nome, cns, cbo, ds_cbo,
                    ch_amb, ch_hosp, ch_outros, ch_total,
                    vinculacao, vinculo, sub_vinculo, atende_sus,
                    nome_fantasia, razao_social, municipio, uf, data_extracao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cnes, competencia, cns, cbo) DO UPDATE SET
                    nome=excluded.nome,
                    ds_cbo=excluded.ds_cbo,
                    ch_amb=excluded.ch_amb,
                    ch_hosp=excluded.ch_hosp,
                    ch_outros=excluded.ch_outros,
                    ch_total=excluded.ch_total,
                    vinculacao=excluded.vinculacao,
                    vinculo=excluded.vinculo,
                    sub_vinculo=excluded.sub_vinculo,
                    atende_sus=excluded.atende_sus,
                    nome_fantasia=excluded.nome_fantasia,
                    razao_social=excluded.razao_social,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    data_extracao=excluded.data_extracao
            """, data_to_insert)
            conn.commit()

        return len(data_to_insert)

    def list_saved_professional_municipalities(self) -> List[Dict[str, Any]]:
        """
        Retorna a lista de municípios e competências que possuem profissionais persistidos no banco local.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    municipio, 
                    uf, 
                    competencia, 
                    COUNT(*) as total_vinculos,
                    COUNT(DISTINCT cns) as total_profissionais,
                    COUNT(DISTINCT cnes) as total_estabelecimentos,
                    MAX(data_extracao) as ultima_atualizacao
                FROM profissionais
                WHERE municipio != ''
                GROUP BY municipio, uf, competencia
                ORDER BY municipio ASC, competencia DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_saved_professionals(
        self,
        municipio: Optional[str] = None,
        competencia: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recupera os registros consolidados de profissionais salvos para um determinado município/competência.
        """
        query = """
            SELECT 
                cnes, co_unidade as coUnidade, competencia, nome, cns, cbo, ds_cbo as dsCbo,
                ch_amb as chAmb, ch_hosp as chHosp, ch_outros as chOutros, ch_total as chTotal,
                vinculacao, vinculo, sub_vinculo as subVinculo, atende_sus as tpSusNaoSus,
                nome_fantasia as noFantasia, razao_social as noEmpresarial,
                municipio as noMunicipio, uf, data_extracao
            FROM profissionais
            WHERE 1=1
        """
        params = []
        if municipio:
            query += " AND (UPPER(municipio) = UPPER(?) OR cnes IN (SELECT cnes FROM estabelecimentos WHERE UPPER(municipio) = UPPER(?)))"
            params.extend([municipio, municipio])
        if competencia:
            query += " AND competencia = ?"
            params.append(competencia)

        query += " ORDER BY nome ASC, ds_cbo ASC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_multiple_bonds_analysis(
        self,
        municipio: Optional[str] = None,
        competencia: Optional[str] = None,
        min_vinculos: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Auditoria de acúmulo de vínculos: Identifica profissionais com múltiplos vínculos no mesmo município/competência,
        calculando a soma da carga horária semanal e listando todos os estabelecimentos de atuação.
        """
        query = """
            SELECT 
                cns,
                nome,
                COUNT(DISTINCT cnes) as qtd_estabelecimentos,
                COUNT(*) as qtd_vinculos,
                SUM(ch_amb) as soma_ch_amb,
                SUM(ch_hosp) as soma_ch_hosp,
                SUM(ch_outros) as soma_ch_outros,
                SUM(ch_total) as soma_ch_total,
                GROUP_CONCAT(DISTINCT ds_cbo) as especialidades,
                GROUP_CONCAT(DISTINCT nome_fantasia || ' (' || ch_total || 'h)') as locais_atuacao
            FROM profissionais
            WHERE cns IS NOT NULL AND cns != '' AND cns != 'None'
        """
        params = []
        if municipio:
            query += " AND UPPER(municipio) = UPPER(?)"
            params.append(municipio)
        if competencia:
            query += " AND competencia = ?"
            params.append(competencia)

        query += f"""
            GROUP BY cns, nome
            HAVING qtd_vinculos >= {min_vinculos}
            ORDER BY soma_ch_total DESC, qtd_vinculos DESC
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Métodos para Repositório de Equipes por Município e Competência
    # -------------------------------------------------------------------------

    def save_teams(
        self,
        records: List[Dict[str, Any]],
        default_competencia: str = "Atual",
        default_municipio: str = "",
        default_uf: str = ""
    ) -> int:
        """
        Salva ou atualiza em lote as equipes de saúde de um município no banco local.
        Garante persistência por competência para consultas offline e relatórios.
        """
        if not records:
            return 0

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_to_insert = []

        for eq in records:
            comp_val = str(eq.get('competencia') or default_competencia).strip()
            mun_val = str(eq.get('noMunicipio') or eq.get('municipio') or default_municipio or '').strip()
            uf_val = str(eq.get('uf') or default_uf or '').strip()
            dt_desat = eq.get('dtDesativacao')
            is_ativa = (dt_desat is None or str(dt_desat).strip() == '' or str(dt_desat).strip().lower() == 'none')
            status = 'Ativa' if is_ativa else 'Desativada'

            data_to_insert.append((
                str(eq.get('cnes', '')).strip(),
                str(eq.get('coUnidade', '')).strip(),
                comp_val,
                str(eq.get('coEquipe', '')).strip(),
                str(eq.get('seqEquipe', '')).strip(),
                str(eq.get('nomeEquipe', '')).strip(),
                str(eq.get('tpEquipe', '')).strip(),
                str(eq.get('dsEquipe', '')).strip(),
                str(eq.get('coArea', '')).strip(),
                str(eq.get('dsArea', '')).strip(),
                str(eq.get('dtAtivacao', '') or '').strip(),
                str(dt_desat or '').strip(),
                str(eq.get('quilombola', '')).strip(),
                str(eq.get('assentada', '')).strip(),
                str(eq.get('geral', '')).strip(),
                str(eq.get('escola', '')).strip(),
                str(eq.get('pronasci', '')).strip(),
                str(eq.get('indigena', '')).strip(),
                str(eq.get('ribeirinha', '')).strip(),
                str(eq.get('complem', '')).strip(),
                str(eq.get('noFantasia', '')).strip(),
                str(eq.get('noEmpresarial', '')).strip(),
                mun_val,
                uf_val,
                str(eq.get('gestao', '')).strip(),
                str(eq.get('natJuridica', '')).strip(),
                status,
                now_str
            ))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO equipes (
                    cnes, co_unidade, competencia, co_equipe, seq_equipe,
                    nome_equipe, tp_equipe, ds_equipe, co_area, ds_area,
                    dt_ativacao, dt_desativacao, quilombola, assentada,
                    geral, escola, pronasci, indigena, ribeirinha, complem,
                    nome_fantasia, razao_social, municipio, uf, gestao,
                    nat_juridica, status, data_extracao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cnes, competencia, co_equipe) DO UPDATE SET
                    seq_equipe=excluded.seq_equipe,
                    nome_equipe=excluded.nome_equipe,
                    tp_equipe=excluded.tp_equipe,
                    ds_equipe=excluded.ds_equipe,
                    co_area=excluded.co_area,
                    ds_area=excluded.ds_area,
                    dt_ativacao=excluded.dt_ativacao,
                    dt_desativacao=excluded.dt_desativacao,
                    quilombola=excluded.quilombola,
                    assentada=excluded.assentada,
                    geral=excluded.geral,
                    escola=excluded.escola,
                    pronasci=excluded.pronasci,
                    indigena=excluded.indigena,
                    ribeirinha=excluded.ribeirinha,
                    complem=excluded.complem,
                    nome_fantasia=excluded.nome_fantasia,
                    razao_social=excluded.razao_social,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    gestao=excluded.gestao,
                    nat_juridica=excluded.nat_juridica,
                    status=excluded.status,
                    data_extracao=excluded.data_extracao
            """, data_to_insert)
            conn.commit()

        return len(data_to_insert)

    def list_saved_team_municipalities(self) -> List[Dict[str, Any]]:
        """
        Retorna a lista de municípios e competências com equipes salvas no banco local,
        com métricas consolidadas (Total, ESF, EAP, ESB, EMULTI, Estabelecimentos e data da extração).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    municipio, 
                    uf, 
                    competencia, 
                    COUNT(*) as total_equipes,
                    SUM(CASE WHEN ds_equipe LIKE '%ESF%' OR tp_equipe = '70' THEN 1 ELSE 0 END) as total_esf,
                    SUM(CASE WHEN (ds_equipe LIKE '%EAP%' OR ds_equipe LIKE '%ATENCAO PRIMARIA%') AND ds_equipe NOT LIKE '%EMULTI%' THEN 1 ELSE 0 END) as total_eap,
                    SUM(CASE WHEN ds_equipe LIKE '%ESB%' OR ds_equipe LIKE '%SAUDE BUCAL%' THEN 1 ELSE 0 END) as total_esb,
                    SUM(CASE WHEN ds_equipe LIKE '%EMULTI%' OR ds_equipe LIKE '%MULTIPROFISSIONAL%' THEN 1 ELSE 0 END) as total_emulti,
                    SUM(CASE WHEN status = 'Ativa' THEN 1 ELSE 0 END) as total_ativas,
                    COUNT(DISTINCT cnes) as total_estabelecimentos,
                    MAX(data_extracao) as ultima_atualizacao
                FROM equipes
                WHERE municipio != ''
                GROUP BY municipio, uf, competencia
                ORDER BY municipio ASC, competencia DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_saved_teams(
        self,
        municipio: Optional[str] = None,
        competencia: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recupera as equipes salvas para um determinado município e competência.
        Mapeia os campos para o mesmo formato utilizado pela extração direta da API.
        """
        query = """
            SELECT 
                cnes, 
                co_unidade as coUnidade, 
                competencia, 
                co_equipe as coEquipe, 
                seq_equipe as seqEquipe,
                nome_equipe as nomeEquipe, 
                tp_equipe as tpEquipe, 
                ds_equipe as dsEquipe, 
                co_area as coArea, 
                ds_area as dsArea,
                dt_ativacao as dtAtivacao, 
                dt_desativacao as dtDesativacao, 
                quilombola, 
                assentada,
                geral, 
                escola, 
                pronasci, 
                indigena, 
                ribeirinha, 
                complem,
                nome_fantasia as noFantasia, 
                razao_social as noEmpresarial, 
                municipio as noMunicipio, 
                uf, 
                gestao, 
                nat_juridica as natJuridica, 
                status, 
                data_extracao as dataExtracao
            FROM equipes
            WHERE 1=1
        """
        params = []
        if municipio:
            query += " AND (UPPER(municipio) = UPPER(?) OR cnes IN (SELECT cnes FROM estabelecimentos WHERE UPPER(municipio) = UPPER(?)))"
            params.extend([municipio, municipio])
        if competencia:
            query += " AND competencia = ?"
            params.append(competencia)

        query += " ORDER BY nome_fantasia ASC, ds_equipe ASC, nome_equipe ASC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_saved_teams(self, municipio: str, competencia: str) -> int:
        """
        Remove os registros de equipes salvas de um município e competência específica.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM equipes 
                WHERE UPPER(municipio) = UPPER(?) AND competencia = ?
            """, (municipio, competencia))
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    # -------------------------------------------------------------------------
    # Métodos para População IBGE e Cruzamento de Cobertura
    # -------------------------------------------------------------------------

    def save_population_batch(self, records: List[Dict[str, Any]]) -> int:
        """
        Salva ou atualiza em lote os dados populacionais (Censo 2022 e Estimativas) no banco local.
        """
        if not records:
            return 0

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_to_insert = []

        for r in records:
            cod6 = str(r.get("codigo_ibge_6", "")).strip()
            if not cod6:
                continue
            cod7 = str(r.get("codigo_ibge_7", "")).strip()
            mun = str(r.get("municipio", "")).strip()
            uf = str(r.get("uf", "SP")).strip()
            p_censo = int(r.get("pop_censo_2022", 0) or 0)
            p_est = int(r.get("pop_estimada", p_censo) or p_censo)
            ano_est = str(r.get("ano_estimativa", "2022")).strip()

            data_to_insert.append((cod6, cod7, mun, uf, p_censo, p_est, ano_est, now_str))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO populacao_ibge (
                    codigo_ibge_6, codigo_ibge_7, municipio, uf, pop_censo_2022, pop_estimada, ano_estimativa, data_atualizacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo_ibge_6) DO UPDATE SET
                    codigo_ibge_7=excluded.codigo_ibge_7,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    pop_censo_2022=excluded.pop_censo_2022,
                    pop_estimada=excluded.pop_estimada,
                    ano_estimativa=excluded.ano_estimativa,
                    data_atualizacao=excluded.data_atualizacao
            """, data_to_insert)
            conn.commit()

        return len(data_to_insert)

    def get_population(self, codigo_ibge_6: Optional[str] = None, municipio_nome: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Recupera os dados populacionais de um município pelo código IBGE ou nome aproximado.
        """
        query = "SELECT * FROM populacao_ibge WHERE 1=1"
        params = []

        if codigo_ibge_6:
            query += " AND (codigo_ibge_6 = ? OR codigo_ibge_7 = ?)"
            params.extend([str(codigo_ibge_6).strip(), str(codigo_ibge_6).strip()])
        elif municipio_nome:
            query += " AND UPPER(municipio) = UPPER(?)"
            params.append(str(municipio_nome).strip())
        else:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                return dict(row)

        # Fallback por busca aproximada / LIKE se não achou exato
        if municipio_nome:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM populacao_ibge WHERE UPPER(municipio) LIKE ? LIMIT 1", (f"%{str(municipio_nome).strip().upper()}%",))
                row = cursor.fetchone()
                if row:
                    return dict(row)

        return None

    def list_saved_populations(self) -> List[Dict[str, Any]]:
        """Retorna todos os municípios com população cadastrada."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM populacao_ibge ORDER BY municipio ASC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_regional_coverage_panorama(self, competencia: str = "Atual", usar_estimativa: bool = True) -> List[Dict[str, Any]]:
        """
        Cruza os dados consolidados de equipes salvas no banco com o repositório de população do IBGE.
        Calcula os indicadores oficiais da PNAB / Ministério da Saúde (Cobertura %, Habitantes/ESF, Déficit).
        """
        from cnes_core.ibge import IBGEClient, normalize_str

        saved_teams = self.list_saved_team_municipalities()
        # Filtra pela competência selecionada se houver registros
        comp_records = [r for r in saved_teams if str(r.get("competencia", "")).strip() == str(competencia).strip()]
        if not comp_records and saved_teams:
            # Se não achou na competência exata, usa todas
            comp_records = saved_teams

        # Carrega todas as populações do banco
        all_pops = self.list_saved_populations()
        pop_by_cod6 = {p["codigo_ibge_6"]: p for p in all_pops}
        pop_by_norm_name = {normalize_str(p["municipio"]): p for p in all_pops}

        panorama = []

        for r in comp_records:
            mun_nome = str(r.get("municipio", "")).strip()
            norm_nome = normalize_str(mun_nome)

            # Busca população correspondente
            pop_info = pop_by_norm_name.get(norm_nome)
            if not pop_info:
                # Procura por correspondência parcial
                for k, v in pop_by_norm_name.items():
                    if k in norm_nome or norm_nome in k:
                        pop_info = v
                        break

            p_censo = pop_info.get("pop_censo_2022", 0) if pop_info else 0
            p_est = pop_info.get("pop_estimada", p_censo) if pop_info else 0
            ano_est = pop_info.get("ano_estimativa", "2022") if pop_info else "2022"
            cod6 = pop_info.get("codigo_ibge_6", "") if pop_info else ""

            pop_usada = p_est if (usar_estimativa and p_est > 0) else (p_censo if p_censo > 0 else 0)

            # Extração de quantidades
            q_esf = int(r.get("total_esf", 0) or 0)
            q_eap = int(r.get("total_eap", 0) or 0)
            q_esb = int(r.get("total_esb", 0) or 0)
            q_emulti = int(r.get("total_emulti", 0) or 0)
            q_total_eq = int(r.get("total_equipes", 0) or 0)

            indicadores = IBGEClient.calculate_health_coverage(
                populacao=pop_usada,
                qtd_esf=q_esf,
                qtd_eap=q_eap,
                qtd_esb=q_esb,
                qtd_emulti=q_emulti
            )

            panorama.append({
                "municipio": mun_nome,
                "uf": r.get("uf", "SP"),
                "competencia": r.get("competencia", competencia),
                "codigo_ibge_6": cod6,
                "pop_censo_2022": p_censo,
                "pop_estimada": p_est,
                "ano_estimativa": ano_est,
                "populacao_usada": pop_usada,
                "total_equipes": q_total_eq,
                "total_esf": q_esf,
                "total_eap": q_eap,
                "total_ab": q_esf + q_eap,
                "total_esb": q_esb,
                "total_emulti": q_emulti,
                "hab_por_esf": indicadores["hab_por_esf"],
                "hab_por_equipe_total": indicadores["hab_por_equipe_total"],
                "hab_por_esb": indicadores["hab_por_esb"],
                "cobertura_esf_pct": indicadores["cobertura_esf_pct"],
                "cobertura_total_pct": indicadores["cobertura_total_pct"],
                "cobertura_esb_pct": indicadores["cobertura_esb_pct"],
                "pop_coberta": indicadores["pop_coberta"],
                "pop_descoberta": indicadores["pop_descoberta"],
                "deficit_esf": indicadores["deficit_esf"],
                "diagnostico": indicadores["diagnostico"],
                "cor_diagnostico": indicadores["cor_diagnostico"],
                "total_estabelecimentos": r.get("total_estabelecimentos", 0),
                "ultima_atualizacao": r.get("ultima_atualizacao", "")
            })

        # Ordena alfabeticamente por município
        panorama.sort(key=lambda x: x["municipio"])
        return panorama


