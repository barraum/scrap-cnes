import streamlit as st
import pandas as pd
import math
import os
from datetime import datetime

from cnes_core.client import CNESClient
from cnes_core.database import CNESDatabase
from cnes_core.exporter import CNESExporter
from cnes_core.municipios import render_municipio_selector, MUNICIPIOS_DRS_VIII
from cnes_core.ibge import IBGEClient

# Configuração da página Streamlit (deve ser a primeira chamada Streamlit)
st.set_page_config(
    page_title="Painel CNES - Extração & Histórico",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS customizada
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F4C81;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        background-color: #0F4C81;
        color: white;
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Inicializa banco de dados e cliente
db = CNESDatabase()
client = CNESClient()

# Header principal
st.markdown('<div class="main-title">🏥 CNES DATASUS - Extrator & Histórico Público</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Ferramenta pontual de acompanhamento, tratamento e monitoramento de estabelecimentos de saúde.</div>', unsafe_allow_html=True)

# Sidebar de Navegação
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Selecione a Módulo:", [
    "🔍 Consultar CNES",
    "🏙️ Consulta por Município",
    "👥 Profissionais por Município",
    "🩺 Equipes por Município",
    "🛏️ Evolução de Leitos",
    "📚 Histórico Local",
    "📊 Comparar Competências",
    "ℹ️ Informações Técnicas"
])

st.sidebar.markdown("---")
is_cloud = os.environ.get("STREAMLIT_SERVER_HEADLESS", "").lower() == "true" or os.path.exists("/mount/src")
if is_cloud:
    st.sidebar.caption("☁️ **Ambiente: Nuvem** (Leitura & Consulta ao Vivo)")
else:
    st.sidebar.caption("💻 **Ambiente: Local** (Base Persistente Ativa)")

# -----------------------------------------------------------------------------
# 1. CONSULTAR CNES
# -----------------------------------------------------------------------------
if menu == "🔍 Consultar CNES":
    st.subheader("Extração de Dados do Estabelecimento")
    
    col_input1, col_input2, col_btn = st.columns([3, 2, 2])
    with col_input1:
        cnes_code = st.text_input("Código CNES (7 dígitos) ou ID de 13 dígitos:", value="2705982", help="Exemplo: 2705982 (Santa Casa de Franca)")
    with col_input2:
        competencia_input = st.text_input("Competência (Opcional - AAAAMM):", value="", help="Deixe em branco para a competência mais recente disponível no DATASUS.")
    with col_btn:
        st.write("")
        st.write("")
        buscar_clicked = st.button("🚀 Extrair Dados", use_container_width=True)

    if buscar_clicked or 'current_data' in st.session_state:
        if buscar_clicked:
            with st.spinner(f"Consultando microserviços do DATASUS para o CNES {cnes_code}..."):
                try:
                    comp_val = competencia_input.strip() if competencia_input.strip() else None
                    full_data = client.fetch_full_establishment(cnes_code.strip(), comp_val)
                    st.session_state['current_data'] = full_data
                    
                    # Salva no banco de dados local
                    db.save_snapshot(full_data)
                    st.toast("✅ Dados salvos com sucesso no histórico local!", icon="💾")
                except Exception as e:
                    st.error(f"Erro ao consultar o CNES: {e}")
                    st.stop()

        data = st.session_state.get('current_data')
        if data:
            meta = data['metadata']
            
            # Painel de Resumo
            st.markdown("---")
            st.markdown(f"### 🏥 {meta.get('nomeFantasia') or meta.get('razaoSocial')}")
            st.caption(f"**Razão Social:** {meta.get('razaoSocial')} | **CNES:** {meta.get('cnes')} | **ID:** {meta.get('coUnidade')} | **Competência:** {meta.get('competencia')} | **Município:** {meta.get('municipio')}/{meta.get('uf')}")

            # KPI Metrics
            profs = data.get('profissionais', [])
            leitos = data.get('leitos', [])
            equip = data.get('equipamentos', [])
            servs = data.get('servicos_classificacao', [])
            habs = data.get('habilitacoes', [])

            num_profs = len(profs) if isinstance(profs, list) else 0
            num_leitos = sum(int(l.get('qtExistente', 0)) for l in leitos) if isinstance(leitos, list) else 0
            num_leitos_sus = sum(int(l.get('qtSus', 0)) for l in leitos) if isinstance(leitos, list) else 0
            num_equip = len(equip) if isinstance(equip, list) else 0
            num_servs = len(servs) if isinstance(servs, list) else 0
            num_habs = len(habs) if isinstance(habs, list) else 0

            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            kpi1.metric("👥 Profissionais", num_profs)
            kpi2.metric("🛏️ Leitos Totais", num_leitos, f"SUS: {num_leitos_sus}")
            kpi3.metric("🔬 Equipamentos", num_equip)
            kpi4.metric("🏥 Serviços", num_servs)
            kpi5.metric("📜 Habilitações", num_habs)

            # Botão de Download Excel
            st.markdown("")
            excel_bytes = CNESExporter.export_to_excel(data)
            st.download_button(
                label=f"📥 Baixar Relatório Excel Completo (CNES {meta.get('cnes')} - {meta.get('competencia')}).xlsx",
                data=excel_bytes,
                file_name=f"CNES_{meta.get('cnes')}_{meta.get('competencia')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # Abas para os módulos
            tab_prof, tab_leit, tab_equip, tab_serv, tab_hab, tab_inst, tab_geral = st.tabs([
                "👥 Profissionais",
                "🛏️ Leitos",
                "🔬 Equipamentos",
                "🏥 Serviços Especializados",
                "📜 Habilitações & Incentivos",
                "🏛️ Instalações & Comissões",
                "📋 Dados Gerais"
            ])

            with tab_prof:
                if profs:
                    df_p = pd.DataFrame(profs)
                    cols_map_p = {
                        'nome': 'Nome do Profissional',
                        'cns': 'CNS/CPF',
                        'dsCbo': 'Descrição CBO / Especialidade',
                        'cbo': 'Código CBO',
                        'chAmb': 'Carga Horária Ambulatorial',
                        'chHosp': 'Carga Horária Hospitalar',
                        'chOutros': 'Carga Horária Outros',
                        'vinculacao': 'Tipo de Vínculo',
                        'tpSusNaoSus': 'Atende SUS'
                    }
                    present_p = [c for c in cols_map_p.keys() if c in df_p.columns]
                    if present_p:
                        df_p = df_p[present_p].rename(columns=cols_map_p)
                    st.dataframe(df_p, use_container_width=True)
                else:
                    st.info("Nenhum profissional cadastrado.")

            with tab_leit:
                if leitos:
                    st.info("💡 **Nota Explicativa:** A coluna **Quantidade Existente** e **Quantidade SUS** indicam o total de leitos. A coluna **Código do Tipo (ID)** é o código de referência do DATASUS (ex: 33 = Clínica Geral), não devendo ser somada.")
                    df_l = pd.DataFrame(leitos)
                    
                    # Garantir ordenação e nomes claros
                    cols_map_l = {
                        'dsLeito': 'Tipo de Leito',
                        'dsAtributo': 'Especialidade / Categoria',
                        'qtExistente': 'Quantidade Existente',
                        'qtSus': 'Quantidade SUS',
                        'qtNaoSus': 'Quantidade Não SUS',
                        'coLeito': 'Código do Tipo (ID DATASUS)'
                    }
                    present_l = [c for c in cols_map_l.keys() if c in df_l.columns]
                    if present_l:
                        df_l = df_l[present_l].rename(columns=cols_map_l)
                        
                    # Converter tipo de leito ID para texto visualmente claro
                    if 'Código do Tipo (ID DATASUS)' in df_l.columns:
                        df_l['Código do Tipo (ID DATASUS)'] = df_l['Código do Tipo (ID DATASUS)'].astype(str).apply(lambda x: f"Código {x}")
                        
                    st.dataframe(df_l, use_container_width=True)
                else:
                    st.info("Nenhum leito hospitalar cadastrado.")

            with tab_equip:
                if equip:
                    df_e = pd.DataFrame(equip)
                    cols_map_e = {
                        'dsEquipamento': 'Descrição do Equipamento',
                        'dsTipoEquipamento': 'Categoria / Tipo',
                        'qtExistente': 'Quantidade Existente',
                        'qtEmUso': 'Quantidade em Uso',
                        'tpSus': 'Atende SUS',
                        'coEquipamento': 'Código Equipamento (ID DATASUS)'
                    }
                    present_e = [c for c in cols_map_e.keys() if c in df_e.columns]
                    if present_e:
                        df_e = df_e[present_e].rename(columns=cols_map_e)
                    if 'Código Equipamento (ID DATASUS)' in df_e.columns:
                        df_e['Código Equipamento (ID DATASUS)'] = df_e['Código Equipamento (ID DATASUS)'].astype(str).apply(lambda x: f"Código {x}")
                    st.dataframe(df_e, use_container_width=True)
                else:
                    st.info("Nenhum equipamento cadastrado.")

            with tab_serv:
                if servs:
                    df_s = pd.DataFrame(servs)
                    cols_map_s = {
                        'dsServico': 'Serviço',
                        'dsServicoEspecializado': 'Classificação Especializada',
                        'tpCaracteristica': 'Característica',
                        'cnpj': 'CNPJ Prestador',
                        'coServico': 'Código Serviço (ID)',
                        'coClassificacao': 'Código Classificação (ID)'
                    }
                    present_s = [c for c in cols_map_s.keys() if c in df_s.columns]
                    if present_s:
                        df_s = df_s[present_s].rename(columns=cols_map_s)
                    st.dataframe(df_s, use_container_width=True)
                else:
                    st.info("Nenhum serviço especializado cadastrado.")

            with tab_hab:
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    st.markdown("#### Habilitações Ministeriais")
                    if habs:
                        st.dataframe(pd.DataFrame(habs), use_container_width=True)
                    else:
                        st.info("Nenhuma habilitação cadastrada.")
                with col_h2:
                    st.markdown("#### Incentivos Financeiros")
                    inc = data.get('incentivos', [])
                    if inc:
                        st.dataframe(pd.DataFrame(inc), use_container_width=True)
                    else:
                        st.info("Nenhum incentivo cadastrado.")

            with tab_inst:
                col_i1, col_i2 = st.columns(2)
                with col_i1:
                    st.markdown("#### Instalações Físicas")
                    inst = data.get('instalacoes', [])
                    if inst:
                        st.dataframe(pd.DataFrame(inst), use_container_width=True)
                    else:
                        st.info("Nenhuma instalação informada.")
                with col_i2:
                    st.markdown("#### Comissões Institucionais")
                    comiss = data.get('comissoes', [])
                    if comiss:
                        st.dataframe(pd.DataFrame(comiss), use_container_width=True)
                    else:
                        st.info("Nenhuma comissão informada.")

            with tab_geral:
                st.json(data.get('dados_gerais', {}))

# -----------------------------------------------------------------------------
# 2. CONSULTA POR MUNICÍPIO
# -----------------------------------------------------------------------------
elif menu == "🏙️ Consulta por Município":
    st.subheader("Extração em Lote — Todos os Estabelecimentos de um Município")
    st.caption("Extraia todos os estabelecimentos de saúde de um município, com classificação (UBS, Hospital, Ambulatório, etc.) e filtros interativos.")

    # --- Inputs do usuário com Biblioteca DRS VIII ---
    cod_municipio, nome_mun_sug = render_municipio_selector(key_prefix="mun_consulta", default_ibge="351620")

    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        modo_extracao = st.radio(
            "Modo de Extração:",
            ["🚀 Completo (com classificação)", "⚡ Rápido (sem classificação)"],
            help="O modo Completo busca o detalhe de cada estabelecimento para obter a Classificação e Tipo de Unidade. Pode levar alguns minutos para municípios grandes."
        )
    with col_m2:
        st.write("")

    st.markdown("##### Filtros Opcionais")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_gestao = st.selectbox("Gestão:", ["Todos", "Municipal", "Estadual", "Dupla"], index=0)
    with col_f2:
        filtro_nat = st.selectbox("Natureza Jurídica:", ["Todos", "Administração Pública", "Entidades Empresariais", "Entidades sem Fins Lucrativos", "Pessoas Físicas"], index=0)
    with col_f3:
        filtro_sus = st.selectbox("Atende SUS:", ["Todos", "Sim", "Não"], index=0)

    st.write("")
    btn_municipio = st.button("🏙️ Extrair Estabelecimentos do Município", use_container_width=True)

    # Mapeamentos de filtros
    gestao_map_input = {"Todos": None, "Municipal": "M", "Estadual": "E", "Dupla": "D"}
    nat_map_input = {"Todos": None, "Administração Pública": "1", "Entidades Empresariais": "2", "Entidades sem Fins Lucrativos": "3", "Pessoas Físicas": "4"}
    sus_map_input = {"Todos": None, "Sim": "S", "Não": "N"}

    if btn_municipio or 'mun_data' in st.session_state:
        if btn_municipio:
            cod_clean = cod_municipio.strip()
            if not cod_clean or len(cod_clean) != 6 or not cod_clean.isdigit():
                st.error("⚠️ Informe um código IBGE válido com 6 dígitos numéricos.")
                st.stop()

            with st.spinner(f"Listando estabelecimentos do município {cod_clean}..."):
                basic_list = client.list_by_municipality(
                    codigo_municipio=cod_clean,
                    gestao=gestao_map_input.get(filtro_gestao),
                    nat_juridica=nat_map_input.get(filtro_nat),
                    atende_sus=sus_map_input.get(filtro_sus),
                )

            if not basic_list:
                st.warning("Nenhum estabelecimento encontrado para este município com os filtros informados.")
                st.stop()

            st.success(f"✅ {len(basic_list)} estabelecimentos encontrados!")

            modo_completo = "Completo" in modo_extracao

            if modo_completo:
                st.info(f"🔄 Buscando detalhes de {len(basic_list)} estabelecimentos... Isso pode levar alguns minutos.")
                progress_bar = st.progress(0, text="Iniciando extração detalhada...")
                status_text = st.empty()

                def update_progress(current, total, nome):
                    if total > 0:
                        pct = min(current / total, 1.0)
                        progress_bar.progress(pct, text=f"[{current}/{total}] {nome}")

                enriched = client.fetch_municipality_details(basic_list, progress_callback=update_progress)
                progress_bar.progress(1.0, text="✅ Extração concluída!")
                st.session_state['mun_data'] = enriched
                st.session_state['mun_modo'] = 'completo'
            else:
                st.session_state['mun_data'] = basic_list
                st.session_state['mun_modo'] = 'rapido'

            # Identificar nome do município a partir dos dados
            if basic_list:
                mun_nome = basic_list[0].get('noMunicipio', cod_clean)
                uf_nome = basic_list[0].get('uf', '')
                st.session_state['mun_nome'] = mun_nome
                st.session_state['mun_uf'] = uf_nome

            st.toast("✅ Extração concluída com sucesso!", icon="🏙️")

        # --- Exibir resultados ---
        mun_results = st.session_state.get('mun_data', [])
        mun_modo = st.session_state.get('mun_modo', 'rapido')
        mun_nome = st.session_state.get('mun_nome', '')
        mun_uf = st.session_state.get('mun_uf', '')

        if mun_results:
            df_mun = pd.DataFrame(mun_results)

            st.markdown("---")
            st.markdown(f"### 🏙️ {mun_nome}/{mun_uf} — {len(mun_results)} Estabelecimentos")

            # --- KPIs ---
            total_est = len(mun_results)
            atende_sus_count = len([e for e in mun_results if str(e.get('atendeSus', '')).strip() == 'S'])
            nao_sus_count = total_est - atende_sus_count

            kpi_cols = st.columns(4)
            kpi_cols[0].metric("🏥 Total Estabelecimentos", total_est)
            kpi_cols[1].metric("✅ Atendem SUS", atende_sus_count)
            kpi_cols[2].metric("❌ Não Atendem SUS", nao_sus_count)

            if mun_modo == 'completo' and 'dsTipoEstabelecimento' in df_mun.columns:
                tipos_unicos = df_mun['dsTipoEstabelecimento'].nunique()
                kpi_cols[3].metric("📋 Tipos Distintos", tipos_unicos)
            else:
                gestao_col = 'tpGestao' if 'tpGestao' in df_mun.columns else 'gestao'
                if gestao_col in df_mun.columns:
                    mun_count = len(df_mun[df_mun[gestao_col].astype(str).str.strip() == 'M'])
                    kpi_cols[3].metric("🏛️ Gestão Municipal", mun_count)

            # --- Download Excel ---
            st.markdown("")
            excel_bytes = CNESExporter.export_municipality_report(mun_results, mun_nome, mun_uf)
            st.download_button(
                label=f"📥 Baixar Relatório Excel — {mun_nome}/{mun_uf} ({total_est} estabelecimentos)",
                data=excel_bytes,
                file_name=f"CNES_Municipio_{mun_nome}_{mun_uf}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # --- Filtros Interativos nos Resultados ---
            if mun_modo == 'completo' and 'dsTipoEstabelecimento' in df_mun.columns:
                st.markdown("---")
                st.markdown("### 🔎 Filtrar Resultados")

                col_filt1, col_filt2 = st.columns(2)

                with col_filt1:
                    # Filtro por Classificação
                    tipos_disponiveis = sorted(df_mun['dsTipoEstabelecimento'].dropna().unique().tolist())
                    filtro_classif = st.multiselect(
                        "Classificação do Estabelecimento:",
                        options=tipos_disponiveis,
                        default=[],
                        help="Selecione uma ou mais classificações para filtrar. Deixe vazio para ver todos."
                    )

                with col_filt2:
                    # Filtro por Gestão
                    gestao_col_det = 'tpGestao' if 'tpGestao' in df_mun.columns else 'gestao'
                    gestao_labels = {'M': 'Municipal', 'E': 'Estadual', 'D': 'Dupla', 'S': 'Sem Gestão'}
                    df_mun['_gestao_label'] = df_mun[gestao_col_det].map(lambda x: gestao_labels.get(str(x).strip(), str(x)))
                    gestoes_disponiveis = sorted(df_mun['_gestao_label'].dropna().unique().tolist())
                    filtro_gestao_res = st.multiselect(
                        "Tipo de Gestão:",
                        options=gestoes_disponiveis,
                        default=[],
                        help="Selecione um ou mais tipos de gestão para filtrar."
                    )

                # Aplicar filtros
                df_filtered = df_mun.copy()
                if filtro_classif:
                    df_filtered = df_filtered[df_filtered['dsTipoEstabelecimento'].isin(filtro_classif)]
                if filtro_gestao_res:
                    df_filtered = df_filtered[df_filtered['_gestao_label'].isin(filtro_gestao_res)]

                if len(df_filtered) != len(df_mun):
                    st.info(f"Exibindo **{len(df_filtered)}** de {len(df_mun)} estabelecimentos após filtros.")

                # --- Gráficos ---
                st.markdown("---")
                tab_chart1, tab_chart2, tab_table = st.tabs(["📊 Por Classificação", "📊 Por Gestão", "📋 Tabela Completa"])

                with tab_chart1:
                    st.markdown("#### Estabelecimentos por Classificação")
                    chart_classif = df_filtered.groupby('dsTipoEstabelecimento').size().reset_index(name='Quantidade')
                    chart_classif = chart_classif.sort_values('Quantidade', ascending=True)
                    st.bar_chart(chart_classif, x='dsTipoEstabelecimento', y='Quantidade', horizontal=True, use_container_width=True)

                with tab_chart2:
                    st.markdown("#### Estabelecimentos por Gestão")
                    chart_gestao = df_filtered.groupby('_gestao_label').size().reset_index(name='Quantidade')
                    chart_gestao = chart_gestao.sort_values('Quantidade', ascending=False)
                    st.bar_chart(chart_gestao, x='_gestao_label', y='Quantidade', use_container_width=True)

                with tab_table:
                    st.markdown("#### Listagem Completa")
                    # Selecionar e renomear colunas para exibição
                    cols_show = {
                        'cnes': 'CNES',
                        'noFantasia': 'Nome Fantasia',
                        'dsTipoEstabelecimento': 'Classificação',
                        'dsTpUnidade': 'Tipo Unidade',
                        '_gestao_label': 'Gestão',
                        'atendeSus': 'SUS',
                        'noEmpresarial': 'Nome Empresarial',
                        'bairro': 'Bairro',
                        'noLogradouro': 'Logradouro',
                    }
                    present_show = [c for c in cols_show.keys() if c in df_filtered.columns]
                    df_display = df_filtered[present_show].rename(columns=cols_show)
                    if 'SUS' in df_display.columns:
                        df_display['SUS'] = df_display['SUS'].map(lambda x: 'Sim' if str(x).strip() == 'S' else ('Não' if str(x).strip() == 'N' else str(x)))
                    st.dataframe(df_display, use_container_width=True, height=600)

            else:
                # Modo rápido — sem classificação
                st.markdown("---")
                st.markdown("### 📋 Listagem (Modo Rápido — sem classificação)")
                st.caption("💡 Para ver a classificação (UBS, Hospital, etc.) e os filtros interativos, use o **Modo Completo**.")
                cols_rapido = {
                    'cnes': 'CNES',
                    'noFantasia': 'Nome Fantasia',
                    'noEmpresarial': 'Nome Empresarial',
                    'gestao': 'Gestão',
                    'atendeSus': 'Atende SUS',
                }
                present_r = [c for c in cols_rapido.keys() if c in df_mun.columns]
                df_rapido = df_mun[present_r].rename(columns=cols_rapido)
                if 'Gestão' in df_rapido.columns:
                    gestao_labels = {'M': 'Municipal', 'E': 'Estadual', 'D': 'Dupla', 'S': 'Sem Gestão'}
                    df_rapido['Gestão'] = df_rapido['Gestão'].map(lambda x: gestao_labels.get(str(x).strip(), str(x)))
                if 'Atende SUS' in df_rapido.columns:
                    df_rapido['Atende SUS'] = df_rapido['Atende SUS'].map(lambda x: 'Sim' if str(x).strip() == 'S' else ('Não' if str(x).strip() == 'N' else str(x)))
                st.dataframe(df_rapido, use_container_width=True, height=600)

# -----------------------------------------------------------------------------
# 3. PROFISSIONAIS POR MUNICÍPIO
# -----------------------------------------------------------------------------
elif menu == "👥 Profissionais por Município":
    st.subheader("Profissionais de Saúde por Município (Extração & Base Local)")
    st.caption("Consolide a lista de profissionais de todos os estabelecimentos do município, consulte bases salvas no banco SQLite local e realize auditoria de acúmulo de vínculos e carga horária semanal.")

    # --- Seleção de Origem dos Dados ---
    aba_origem = st.radio(
        "Selecione a Origem dos Dados:",
        ["🌐 Nova Extração da API (DATASUS)", "📂 Consultar Base Local Salva (SQLite)"],
        horizontal=True
    )

    if aba_origem == "🌐 Nova Extração da API (DATASUS)":
        cod_municipio_prof, nome_mun_prof_sug = render_municipio_selector(
            key_prefix="prof_api",
            default_ibge="351620"
        )
        comp_prof_input = st.text_input(
            "Competência (Opcional - AAAAMM):",
            value="",
            key="input_comp_prof",
            help="Deixe em branco para a competência mais recente disponível no DATASUS."
        )

        st.markdown("##### Pré-Filtros de Estabelecimentos (Recomendado para Reduzir o Tempo de Extração)")
        col_pf1, col_pf2, col_pf3 = st.columns(3)
        with col_pf1:
            filtro_gestao_prof = st.selectbox("Gestão:", ["Todos", "Municipal", "Estadual", "Dupla"], index=0, key="sel_gestao_prof")
        with col_pf2:
            filtro_nat_prof = st.selectbox("Natureza Jurídica:", ["Todos", "Administração Pública", "Entidades Empresariais", "Entidades sem Fins Lucrativos", "Pessoas Físicas"], index=0, key="sel_nat_prof")
        with col_pf3:
            filtro_sus_prof = st.selectbox("Atende SUS:", ["Todos", "Sim", "Não"], index=0, key="sel_sus_prof")

        st.write("")
        btn_prof_municipio = st.button("👥 Extrair e Salvar no Banco Local", use_container_width=True)

        # Mapeamentos de filtros
        gestao_map_input = {"Todos": None, "Municipal": "M", "Estadual": "E", "Dupla": "D"}
        nat_map_input = {"Todos": None, "Administração Pública": "1", "Entidades Empresariais": "2", "Entidades sem Fins Lucrativos": "3", "Pessoas Físicas": "4"}
        sus_map_input = {"Todos": None, "Sim": "S", "Não": "N"}

        if btn_prof_municipio:
            cod_clean_p = cod_municipio_prof.strip()
            if not cod_clean_p or len(cod_clean_p) != 6 or not cod_clean_p.isdigit():
                st.error("⚠️ Informe um código IBGE válido com 6 dígitos numéricos.")
                st.stop()

            with st.spinner(f"Listando estabelecimentos do município {cod_clean_p}..."):
                est_list = client.list_by_municipality(
                    codigo_municipio=cod_clean_p,
                    gestao=gestao_map_input.get(filtro_gestao_prof),
                    nat_juridica=nat_map_input.get(filtro_nat_prof),
                    atende_sus=sus_map_input.get(filtro_sus_prof),
                )

            if not est_list:
                st.warning("Nenhum estabelecimento encontrado para este município com os filtros informados.")
                st.stop()

            st.info(f"🔄 Extraindo profissionais de **{len(est_list)} estabelecimentos**... Isso pode levar de alguns segundos a alguns minutos.")
            progress_bar_p = st.progress(0, text="Iniciando extração em lote...")

            def update_progress_prof(current, total, nome):
                if total > 0:
                    pct = min(current / total, 1.0)
                    progress_bar_p.progress(pct, text=f"[{current}/{total}] {nome}")

            comp_val = comp_prof_input.strip() if comp_prof_input.strip() else None
            prof_results = client.fetch_municipality_professionals(
                establishments=est_list,
                competencia=comp_val,
                progress_callback=update_progress_prof
            )
            progress_bar_p.progress(1.0, text="✅ Extração concluída!")

            # Identificar nome do município
            mun_n = est_list[0].get('noMunicipio', cod_clean_p) if est_list else cod_clean_p
            uf_n = est_list[0].get('uf', '') if est_list else ''

            # Salva na base de dados persistente SQLite
            qtd_salva = db.save_professionals(prof_results, competencia=comp_val, default_municipio=mun_n, default_uf=uf_n)

            st.session_state['prof_data'] = prof_results
            st.session_state['prof_mun_nome'] = mun_n
            st.session_state['prof_mun_uf'] = uf_n
            st.session_state['prof_comp'] = comp_val or 'Atual'

            st.toast(f"💾 {qtd_salva} registros salvos no banco SQLite local!", icon="✅")

    else:
        # Modo: Consultar Base Local
        saved_muns = db.list_saved_professional_municipalities()
        if not saved_muns:
            st.info("Nenhum município com profissionais foi salvo ainda no banco SQLite local. Execute uma extração da API primeiro.")
        else:
            options_map = {
                f"{r['municipio']}/{r['uf']} - Comp: {r['competencia']} ({r['total_vinculos']} vínculos, {r['total_profissionais']} profissionais)": r
                for r in saved_muns
            }
            sel_opt = st.selectbox("Selecione a Base Local Salva:", list(options_map.keys()))
            col_b_carregar, col_b_info = st.columns([2, 3])
            with col_b_carregar:
                if st.button("📂 Carregar Dados do Banco Local", use_container_width=True):
                    chosen = options_map[sel_opt]
                    loaded = db.get_saved_professionals(chosen['municipio'], chosen['competencia'])
                    st.session_state['prof_data'] = loaded
                    st.session_state['prof_mun_nome'] = chosen['municipio']
                    st.session_state['prof_mun_uf'] = chosen['uf']
                    st.session_state['prof_comp'] = chosen['competencia']
                    st.toast(f"📂 {len(loaded)} profissionais carregados do banco SQLite local!", icon="⚡")

    # --- Exibir Resultados do Profissional ---
    prof_records = st.session_state.get('prof_data', [])
    mun_nome_p = st.session_state.get('prof_mun_nome', '')
    mun_uf_p = st.session_state.get('prof_mun_uf', '')
    comp_p = st.session_state.get('prof_comp', '')

    if prof_records:
        df_prof = pd.DataFrame(prof_records)

        # Garantir colunas numéricas de carga horária
        for ch_col in ['chAmb', 'chHosp', 'chOutros']:
            if ch_col in df_prof.columns:
                df_prof[ch_col] = pd.to_numeric(df_prof[ch_col], errors='coerce').fillna(0).astype(int)
            else:
                df_prof[ch_col] = 0
        df_prof['chTotal'] = df_prof['chAmb'] + df_prof['chHosp'] + df_prof['chOutros']

        st.markdown("---")
        st.markdown(f"### 👥 {mun_nome_p}/{mun_uf_p} — {len(prof_records)} Vínculos de Profissionais (Comp: `{comp_p}`)")

        # --- KPIs ---
        tot_vinculos = len(prof_records)
        tot_unicos = df_prof['cns'].nunique() if 'cns' in df_prof.columns else tot_vinculos
        cbos_unicos = df_prof['dsCbo'].nunique() if 'dsCbo' in df_prof.columns else 0
        ests_unicos = df_prof['cnes'].nunique() if 'cnes' in df_prof.columns else 0

        # Análise rápida de múltiplos vínculos
        cns_counts = df_prof.groupby('cns').agg(
            qtd_v=('cnes', 'count'),
            ch_sum=('chTotal', 'sum')
        ).reset_index()
        mult_vinc_count = len(cns_counts[cns_counts['qtd_v'] >= 2])
        ch_alta_count = len(cns_counts[cns_counts['ch_sum'] > 60])

        kp1, kp2, kp3, kp4, kp5 = st.columns(5)
        kp1.metric("📋 Total de Vínculos", tot_vinculos)
        kp2.metric("👤 Profissionais Únicos", tot_unicos)
        kp3.metric("🩺 Especialidades (CBO)", cbos_unicos)
        kp4.metric("🏥 Estabelecimentos", ests_unicos)
        kp5.metric("⚠️ Múltiplos Vínculos", mult_vinc_count, f"{ch_alta_count} com CH > 60h" if ch_alta_count > 0 else None)

        # --- Botão Download Excel ---
        st.markdown("")
        excel_prof_bytes = CNESExporter.export_municipality_professionals_report(prof_records, mun_nome_p, mun_uf_p)
        st.download_button(
            label=f"📥 Baixar Relatório Completo de Profissionais em Excel ({mun_nome_p}/{mun_uf_p})",
            data=excel_prof_bytes,
            file_name=f"Profissionais_CNES_{mun_nome_p}_{mun_uf_p}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # --- Filtros Interativos nos Resultados ---
        st.markdown("---")
        st.markdown("### 🔎 Filtrar Resultados de Profissionais")

        col_fp1, col_fp2, col_fp3 = st.columns(3)

        with col_fp1:
            # Filtro por CBO / Especialidade
            cbos_disponiveis = sorted(df_prof['dsCbo'].dropna().unique().tolist()) if 'dsCbo' in df_prof.columns else []
            filtro_cbo_sel = st.multiselect(
                "CBO / Especialidade Ocupacional:",
                options=cbos_disponiveis,
                default=[],
                help="Selecione uma ou mais especialidades (ex: MEDICO CLINICO, ENFERMEIRO). Deixe vazio para todos."
            )

        with col_fp2:
            # Filtro por Nome ou CNS
            search_nome = st.text_input(
                "Buscar por Nome ou CNS:",
                value="",
                help="Digite parte do nome do profissional ou número do CNS para filtrar."
            )

        with col_fp3:
            # Filtro por Tipo de Vínculo
            vinc_disponiveis = sorted(df_prof['vinculacao'].dropna().unique().tolist()) if 'vinculacao' in df_prof.columns else []
            filtro_vinc_sel = st.multiselect(
                "Tipo de Vinculação:",
                options=vinc_disponiveis,
                default=[],
                help="Selecione um ou mais tipos de vinculação."
            )

        # Aplicar filtros
        df_prof_filtered = df_prof.copy()

        if filtro_cbo_sel:
            df_prof_filtered = df_prof_filtered[df_prof_filtered['dsCbo'].isin(filtro_cbo_sel)]

        if search_nome.strip():
            query_str = search_nome.strip().upper()
            cond_nome = df_prof_filtered['nome'].astype(str).str.upper().str.contains(query_str, na=False)
            cond_cns = df_prof_filtered['cns'].astype(str).str.contains(query_str, na=False)
            df_prof_filtered = df_prof_filtered[cond_nome | cond_cns]

        if filtro_vinc_sel:
            df_prof_filtered = df_prof_filtered[df_prof_filtered['vinculacao'].isin(filtro_vinc_sel)]

        if len(df_prof_filtered) != len(df_prof):
            st.info(f"Exibindo **{len(df_prof_filtered)}** de {len(df_prof)} vínculos após filtros.")

        # --- Visualizações, Tabelas e Auditoria de Vínculos ---
        st.markdown("---")
        tab_pchart1, tab_pchart2, tab_ptable, tab_multi = st.tabs([
            "📊 Top Especialidades",
            "📊 Por Tipo de Vínculo",
            "📋 Tabela de Profissionais",
            "⚠️ Auditoria de Vínculos Múltiplos & Carga Horária"
        ])

        with tab_pchart1:
            st.markdown("#### Especialidades Mais Frequentes (Top 15)")
            if 'dsCbo' in df_prof_filtered.columns:
                top_cbos = df_prof_filtered['dsCbo'].value_counts().head(15).reset_index()
                top_cbos.columns = ['Especialidade', 'Quantidade']
                top_cbos = top_cbos.sort_values('Quantidade', ascending=True)
                st.bar_chart(top_cbos, x='Especialidade', y='Quantidade', horizontal=True, use_container_width=True)

        with tab_pchart2:
            st.markdown("#### Distribuição por Vinculação Empregatícia")
            if 'vinculacao' in df_prof_filtered.columns:
                chart_vinc = df_prof_filtered['vinculacao'].value_counts().reset_index()
                chart_vinc.columns = ['Vinculação', 'Quantidade']
                st.bar_chart(chart_vinc, x='Vinculação', y='Quantidade', use_container_width=True)

        with tab_ptable:
            st.markdown("#### Tabela Consolidada de Profissionais")
            cols_show_p = {
                'nome': 'Nome do Profissional',
                'dsCbo': 'CBO / Especialidade',
                'chAmb': 'CH Amb',
                'chHosp': 'CH Hosp',
                'chOutros': 'CH Outros',
                'chTotal': 'CH Total Semanal',
                'vinculacao': 'Vinculação',
                'noFantasia': 'Estabelecimento',
                'cns': 'CNS/CPF',
                'tpSusNaoSus': 'SUS'
            }
            present_show_p = [c for c in cols_show_p.keys() if c in df_prof_filtered.columns]
            df_display_p = df_prof_filtered[present_show_p].rename(columns=cols_show_p)
            if 'SUS' in df_display_p.columns:
                df_display_p['SUS'] = df_display_p['SUS'].map(lambda x: 'Sim' if str(x).strip() == 'S' else ('Não' if str(x).strip() == 'N' else str(x)))
            st.dataframe(df_display_p, use_container_width=True, height=600)

        with tab_multi:
            st.markdown("#### ⚠️ Detecção de Acúmulo de Vínculos e Carga Horária Semanal")
            st.caption("Identifica profissionais que possuem **2 ou mais vínculos simultâneos** no município e calcula a soma total da carga horária semanal exercida.")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                min_v = st.slider("Quantidade Mínima de Vínculos:", min_value=2, max_value=10, value=2)
            with col_m2:
                min_ch = st.slider("Carga Horária Total Mínima (Semanal):", min_value=0, max_value=120, value=40, step=5)

            # Agrupar por CNS e Nome
            multi_grouped = df_prof.groupby(['cns', 'nome']).agg(
                qtd_estabelecimentos=('cnes', 'nunique'),
                qtd_vinculos=('cnes', 'count'),
                soma_ch_amb=('chAmb', 'sum'),
                soma_ch_hosp=('chHosp', 'sum'),
                soma_ch_outros=('chOutros', 'sum'),
                soma_ch_total=('chTotal', 'sum'),
                especialidades=('dsCbo', lambda x: ", ".join(sorted(set(str(v) for v in x if v)))),
                locais_atuacao=('noFantasia', lambda x: " | ".join(sorted(set(str(v) for v in x if v))))
            ).reset_index()

            # Filtrar
            multi_filtered = multi_grouped[
                (multi_grouped['qtd_vinculos'] >= min_v) &
                (multi_grouped['soma_ch_total'] >= min_ch)
            ].sort_values('soma_ch_total', ascending=False)

            if multi_filtered.empty:
                st.info(f"Nenhum profissional encontrado com pelo menos {min_v} vínculos e carga horária >= {min_ch}h semanais.")
            else:
                st.warning(f"⚠️ Encontrados **{len(multi_filtered)} profissionais** com acúmulo de vínculos atendendo aos critérios.")

                cols_multi_map = {
                    'nome': 'Nome do Profissional',
                    'cns': 'CNS/CPF',
                    'qtd_vinculos': 'Qtd Vínculos',
                    'qtd_estabelecimentos': 'Qtd Estabelecimentos',
                    'soma_ch_total': 'Soma CH Total (h/sem)',
                    'soma_ch_amb': 'CH Ambulatorial',
                    'soma_ch_hosp': 'CH Hospitalar',
                    'soma_ch_outros': 'CH Outros',
                    'especialidades': 'Especialidades Exercidas',
                    'locais_atuacao': 'Locais de Atuação'
                }
                st.dataframe(
                    multi_filtered.rename(columns=cols_multi_map),
                    use_container_width=True,
                    height=500
                )

# -----------------------------------------------------------------------------
# 4. EQUIPES DE SAÚDE POR MUNICÍPIO (ESF, EAP, ESB, EMULTI)
# -----------------------------------------------------------------------------
elif menu == "🩺 Equipes por Município":
    st.subheader("🩺 Equipes de Saúde por Município (ESF, EAP, ESB, EMULTI)")
    st.caption("Quantifique e detalhe as equipes de saúde vinculadas aos estabelecimentos (UBS/USF), com suporte à biblioteca DRS VIII, persistência estruturada por competência no repositório local e exportação em Excel.")

    aba_origem_eq = st.radio(
        "Selecione a Origem dos Dados:",
        ["🌐 Nova Extração da API (DATASUS)", "📂 Repositório Local Salvo (Histórico por Competência / Modo Offline)"],
        horizontal=True
    )

    if aba_origem_eq == "🌐 Nova Extração da API (DATASUS)":
        cod_municipio_eq, nome_mun_eq_sug = render_municipio_selector(
            key_prefix="eq_api",
            default_ibge="351620"
        )

        col_eq1, col_eq2 = st.columns([1, 1])
        with col_eq1:
            comp_eq_input = st.text_input(
                "Competência (Opcional - AAAAMM):",
                value="",
                key="input_comp_eq",
                help="Deixe em branco para a competência mais recente disponível no DATASUS."
            )
        with col_eq2:
            st.info("💡 **Dica de Performance:** As equipes de Atenção Básica (ESF, EAP, ESB, etc.) pertencem à rede pública/municipal. O pré-filtro 'Administração Pública' agiliza a consulta.")

        st.markdown("##### Pré-Filtros de Estabelecimentos (Redução do Tempo de Requisições)")
        col_ef1, col_ef2, col_ef3 = st.columns(3)
        with col_ef1:
            filtro_gestao_eq = st.selectbox("Gestão:", ["Todos", "Municipal", "Estadual", "Dupla"], index=0, key="sel_gestao_eq")
        with col_ef2:
            filtro_nat_eq = st.selectbox(
                "Natureza Jurídica:",
                ["Administração Pública (Recomendado)", "Todos", "Entidades sem Fins Lucrativos", "Entidades Empresariais", "Pessoas Físicas"],
                index=0,
                key="sel_nat_eq"
            )
        with col_ef3:
            filtro_sus_eq = st.selectbox("Atende SUS:", ["Todos", "Sim", "Não"], index=0, key="sel_sus_eq")

        st.write("")
        btn_extrair_equipes = st.button("🩺 Extrair Equipes e Salvar no Repositório Local", use_container_width=True)

        # Mapeamento de filtros
        gestao_map_eq = {"Todos": None, "Municipal": "M", "Estadual": "E", "Dupla": "D"}
        nat_map_eq = {
            "Todos": None,
            "Administração Pública (Recomendado)": "1",
            "Entidades sem Fins Lucrativos": "3",
            "Entidades Empresariais": "2",
            "Pessoas Físicas": "4"
        }
        sus_map_eq = {"Todos": None, "Sim": "S", "Não": "N"}

        if btn_extrair_equipes:
            cod_clean_eq = cod_municipio_eq.strip()
            if not cod_clean_eq or len(cod_clean_eq) != 6 or not cod_clean_eq.isdigit():
                st.error("⚠️ Informe um código IBGE válido com 6 dígitos numéricos.")
                st.stop()

            with st.spinner(f"Listando estabelecimentos de saúde para o município {cod_clean_eq}..."):
                est_list = client.list_by_municipality(
                    codigo_municipio=cod_clean_eq,
                    gestao=gestao_map_eq.get(filtro_gestao_eq),
                    nat_juridica=nat_map_eq.get(filtro_nat_eq),
                    atende_sus=sus_map_eq.get(filtro_sus_eq),
                )

            if not est_list:
                st.warning("Nenhum estabelecimento encontrado para este município com os filtros informados.")
                st.stop()

            st.info(f"🔄 Consultando equipes de **{len(est_list)} estabelecimentos**... Aguarde alguns instantes.")
            progress_bar_eq = st.progress(0, text="Iniciando extração de equipes...")

            def update_progress_eq(current, total, nome):
                if total > 0:
                    pct = min(current / total, 1.0)
                    progress_bar_eq.progress(pct, text=f"[{current}/{total}] {nome}")

            comp_val_eq = comp_eq_input.strip() if comp_eq_input.strip() else None
            teams_results = client.fetch_municipality_teams(
                establishments=est_list,
                competencia=comp_val_eq,
                progress_callback=update_progress_eq
            )
            progress_bar_eq.progress(1.0, text="✅ Extração concluída!")

            # Identificar município e UF
            mun_nome_final = est_list[0].get('noMunicipio', nome_mun_eq_sug) if est_list else nome_mun_eq_sug
            uf_nome_final = est_list[0].get('uf', 'SP') if est_list else 'SP'

            # Persistência estruturada por competência no SQLite local
            qtd_salva = db.save_teams(
                teams_results,
                default_competencia=comp_val_eq or 'Atual',
                default_municipio=mun_nome_final,
                default_uf=uf_nome_final
            )

            st.session_state['teams_data'] = teams_results
            st.session_state['teams_mun_nome'] = mun_nome_final
            st.session_state['teams_mun_uf'] = uf_nome_final
            st.session_state['teams_cod_ibge'] = cod_clean_eq
            st.session_state['teams_comp'] = comp_val_eq or 'Atual'
            st.session_state['teams_origem'] = 'API'

            st.toast(f"💾 {qtd_salva} registros de equipes salvos no repositório local!", icon="✅")

    else:
        # Modo: Repositório Local Salvo (Histórico por Competência / Modo Offline)
        saved_eq_muns = db.list_saved_team_municipalities()
        if not saved_eq_muns:
            st.info("Nenhuma pesquisa de equipes foi salva ainda no repositório local. Realize uma extração pela API primeiro para alimentar o histórico.")
        else:
            tab_repo_panorama, tab_repo_historico = st.tabs([
                "🏛️ Panorama Regional & Cobertura (IBGE)",
                "📋 Pesquisas Salvas & Carregamento Individual"
            ])

            with tab_repo_panorama:
                st.markdown("##### 🏛️ Cobertura da Atenção Básica & População — Região DRS VIII (Franca)")
                st.caption("Cruzamento automático entre o quantitativo de equipes no CNES e os dados oficiais de população do IBGE (Censo 2022 e Estimativas Recentes). Parâmetros normativos: Política Nacional de Atenção Básica (Portaria GM/MS nº 2.436/2017).")

                col_sync1, col_sync2, col_sync3 = st.columns([3, 2, 2])
                with col_sync1:
                    base_pop_escolha = st.radio(
                        "Base Populacional Utilizada:",
                        ["Estimativa Recente IBGE", "Censo Demográfico 2022"],
                        horizontal=True,
                        key="rad_base_pop"
                    )
                with col_sync2:
                    st.write("")
                    btn_sync_ibge = st.button("🔄 Sincronizar com API IBGE", use_container_width=True)

                if btn_sync_ibge:
                    with st.spinner("Consultando APIs oficiais do IBGE (Censo 2022 e Estimativas de SP)..."):
                        c_ibge = IBGEClient()
                        pop_map = c_ibge.fetch_sp_municipalities_population()
                        if pop_map:
                            salvos_ibge = db.save_population_batch(list(pop_map.values()))
                            st.toast(f"✅ {salvos_ibge} municípios sincronizados com a API do IBGE!", icon="📊")
                        else:
                            st.error("Não foi possível conectar à API do IBGE no momento.")

                usar_est = ("Estimativa" in base_pop_escolha)
                panorama = db.get_regional_coverage_panorama(competencia="Atual", usar_estimativa=usar_est)

                if panorama:
                    df_pan = pd.DataFrame(panorama)

                    # Totais Regionais Consolidados
                    pop_tot = int(df_pan['populacao_usada'].sum())
                    esf_tot = int(df_pan['total_esf'].sum())
                    eap_tot = int(df_pan['total_eap'].sum())
                    ab_tot = int(df_pan['total_ab'].sum())
                    esb_tot = int(df_pan['total_esb'].sum())
                    coberta_tot = int(df_pan['pop_coberta'].sum())
                    descoberta_tot = int(df_pan['pop_descoberta'].sum())
                    deficit_tot = int(df_pan['deficit_esf'].sum())
                    cob_media = round((coberta_tot / pop_tot) * 100, 1) if pop_tot > 0 else 0

                    kpi_r1, kpi_r2, kpi_r3, kpi_r4, kpi_r5, kpi_r6 = st.columns(6)
                    kpi_r1.metric("👥 População Regional", f"{pop_tot:,d}".replace(",", "."))
                    kpi_r2.metric("🟢 Total ESF", esf_tot)
                    kpi_r3.metric("🔵 Total EAP", eap_tot)
                    kpi_r4.metric("🩺 Cobertura Média AB", f"{cob_media}%")
                    kpi_r5.metric("🦷 Total ESB (Bucal)", esb_tot)
                    kpi_r6.metric("⚠️ Déficit Est. de ESFs", deficit_tot)

                    # Botão download Excel do Panorama Regional
                    with col_sync3:
                        st.write("")
                        excel_pan_bytes = CNESExporter.export_regional_coverage_report(panorama, competencia="Atual")
                        st.download_button(
                            label="📥 Baixar Panorama Regional em Excel (.xlsx)",
                            data=excel_pan_bytes,
                            file_name="CNES_Panorama_Regional_DRS_VIII_IBGE.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    st.markdown("")
                    # Tabela Panorâmica Formatada
                    cols_pan_show = {
                        'municipio': 'Município',
                        'populacao_usada': 'População (IBGE)',
                        'total_esf': 'ESF',
                        'total_eap': 'EAP',
                        'total_ab': 'Total AB',
                        'total_esb': 'ESB',
                        'total_emulti': 'EMULTI',
                        'hab_por_esf': 'Hab / ESF',
                        'hab_por_equipe_total': 'Hab / Equipe AB',
                        'cobertura_total_pct': 'Cobertura Total (%)',
                        'pop_descoberta': 'Pop. Descoberta',
                        'deficit_esf': 'Déficit ESF',
                        'diagnostico': 'Diagnóstico'
                    }
                    present_pan = [c for c in cols_pan_show.keys() if c in df_pan.columns]
                    df_pan_display = df_pan[present_pan].rename(columns=cols_pan_show)
                    st.dataframe(df_pan_display, use_container_width=True, height=520)

                    # Gráficos de Apoio
                    st.markdown("---")
                    st.markdown("##### 📊 Análise Gráfica Comparativa — DRS VIII")
                    col_chart1, col_chart2 = st.columns(2)

                    with col_chart1:
                        st.markdown("###### Ranking de Cobertura Potencial da Atenção Básica (%)")
                        chart_cob = df_pan.set_index('municipio')['cobertura_total_pct'].sort_values()
                        st.bar_chart(chart_cob)

                    with col_chart2:
                        st.markdown("###### Habitantes por Equipe de Saúde da Família (ESF)")
                        st.caption("Parâmetro de referência da PNAB/MS: Média recomendada até 3.500 hab/ESF.")
                        chart_hab = df_pan.dropna(subset=['hab_por_esf']).set_index('municipio')['hab_por_esf'].sort_values(ascending=False)
                        st.bar_chart(chart_hab)
                else:
                    st.warning("Nenhum dado populacional cruzado encontrado. Clique em 'Sincronizar com API IBGE' acima.")

            with tab_repo_historico:
                st.markdown("##### 📋 Pesquisas de Equipes Salvas no Repositório Local")
                
                # Tabela de resumo do histórico salvo
                df_hist_view = pd.DataFrame(saved_eq_muns)
                cols_hist_map = {
                    'municipio': 'Município',
                    'uf': 'UF',
                    'competencia': 'Competência',
                    'total_equipes': 'Total Equipes',
                    'total_esf': 'ESF',
                    'total_eap': 'EAP',
                    'total_esb': 'ESB',
                    'total_emulti': 'EMULTI',
                    'total_ativas': 'Ativas',
                    'total_estabelecimentos': 'Estabelecimentos',
                    'ultima_atualizacao': 'Data da Gravação'
                }
                cols_present = [c for c in cols_hist_map.keys() if c in df_hist_view.columns]
                st.dataframe(df_hist_view[cols_present].rename(columns=cols_hist_map), use_container_width=True)

                options_eq_map = {
                    f"{r['municipio']}/{r['uf']} - Competência: {r['competencia']} (Total: {r['total_equipes']} equipes | {r['total_esf']} ESF, {r['total_eap']} EAP, {r['total_esb']} ESB)": r
                    for r in saved_eq_muns
                }

                col_sel1, col_sel2 = st.columns([3, 1])
                with col_sel1:
                    escolha_salva = st.selectbox(
                        "Selecione a pesquisa histórica para carregar instantaneamente:",
                        options=list(options_eq_map.keys()),
                        key="sel_eq_salva"
                    )
                with col_sel2:
                    st.write("")
                    st.write("")
                    btn_carregar_eq_local = st.button("📂 Carregar Equipes", use_container_width=True)

                if btn_carregar_eq_local and escolha_salva:
                    item_sel = options_eq_map[escolha_salva]
                    with st.spinner("Carregando equipes do repositório local SQLite..."):
                        loaded_teams = db.get_saved_teams(
                            municipio=item_sel['municipio'],
                            competencia=item_sel['competencia']
                        )
                        st.session_state['teams_data'] = loaded_teams
                        st.session_state['teams_mun_nome'] = item_sel['municipio']
                        st.session_state['teams_mun_uf'] = item_sel['uf']
                        st.session_state['teams_comp'] = item_sel['competencia']
                        st.session_state['teams_origem'] = 'Repositório Local (Offline)'
                        st.toast(f"✅ {len(loaded_teams)} equipes carregadas do repositório local!", icon="📂")

    # --- Painel de Resultados de Equipes ---
    teams_data = st.session_state.get('teams_data', [])
    teams_mun_nome = st.session_state.get('teams_mun_nome', '')
    teams_mun_uf = st.session_state.get('teams_mun_uf', '')
    teams_comp = st.session_state.get('teams_comp', 'Atual')
    teams_origem = st.session_state.get('teams_origem', 'API')

    if teams_data:
        df_teams = pd.DataFrame(teams_data)

        st.markdown("---")
        st.markdown(f"### 🩺 {teams_mun_nome}/{teams_mun_uf} — Competência: {teams_comp} ({len(teams_data)} Equipes)")
        st.caption(f"**Origem dos dados:** `{teams_origem}` | **Total de Unidades com Equipes:** {df_teams['noFantasia'].nunique() if 'noFantasia' in df_teams.columns else 0}")

        # Contagens de tipos
        def is_type(df, term, code=None):
            mask = df['dsEquipe'].astype(str).str.upper().str.contains(term)
            if code and 'tpEquipe' in df.columns:
                mask = mask | (df['tpEquipe'].astype(str) == str(code))
            return mask

        mask_esf = is_type(df_teams, 'ESF', '70')
        mask_eap = (df_teams['dsEquipe'].astype(str).str.upper().str.contains('EAP') | df_teams['dsEquipe'].astype(str).str.upper().str.contains('ATENCAO PRIMARIA')) & (~df_teams['dsEquipe'].astype(str).str.upper().str.contains('EMULTI'))
        mask_esb = is_type(df_teams, 'ESB') | df_teams['dsEquipe'].astype(str).str.upper().str.contains('SAUDE BUCAL')
        mask_emulti = is_type(df_teams, 'EMULTI') | df_teams['dsEquipe'].astype(str).str.upper().str.contains('MULTIPROFISSIONAL')
        mask_ativas = df_teams['status'].astype(str) == 'Ativa'

        total_eq = len(df_teams)
        total_esf = mask_esf.sum()
        total_eap = mask_eap.sum()
        total_esb = mask_esb.sum()
        total_emulti = mask_emulti.sum()
        total_ativas = mask_ativas.sum()

        kpi_e1, kpi_e2, kpi_e3, kpi_e4, kpi_e5, kpi_e6 = st.columns(6)
        kpi_e1.metric("🩺 Total Equipes", total_eq)
        kpi_e2.metric("🟢 ESF (Saúde Família)", int(total_esf))
        kpi_e3.metric("🔵 EAP (Atenção Primária)", int(total_eap))
        kpi_e4.metric("🦷 ESB (Saúde Bucal)", int(total_esb))
        kpi_e5.metric("👥 EMULTI", int(total_emulti))
        kpi_e6.metric("✅ Equipes Ativas", int(total_ativas))

        # --- Botão Download Excel ---
        st.markdown("")
        excel_teams_bytes = CNESExporter.export_municipality_teams_report(
            teams_data,
            municipio_nome=teams_mun_nome,
            competencia=teams_comp
        )
        st.download_button(
            label=f"📥 Baixar Relatório Completo de Equipes em Excel (.xlsx) — {teams_mun_nome}/{teams_mun_uf}",
            data=excel_teams_bytes,
            file_name=f"CNES_Equipes_{teams_mun_nome}_{teams_comp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # --- Abas de visualização detalhada ---
        tab_eq_cob, tab_eq_unidades, tab_eq_graf, tab_eq_lista = st.tabs([
            "👥 Cobertura Populacional (IBGE)",
            "🏥 Equipes por Unidade Básica",
            "📊 Indicadores & Gráficos",
            "📋 Todas as Equipes (Filtros Avançados)"
        ])

        with tab_eq_cob:
            st.markdown(f"#### 👥 Análise de Cobertura e Dimensionamento Populacional — {teams_mun_nome}")
            st.caption("Cruzamento entre o contingente populacional apurado pelo IBGE e as equipes cadastradas no CNES (Portaria de Consolidação GM/MS nº 2/2017 e PNAB).")

            pop_info = db.get_population(municipio_nome=teams_mun_nome)
            if not pop_info:
                with st.spinner("Buscando dados populacionais do IBGE..."):
                    c_ibge = IBGEClient()
                    ibge_lookup = st.session_state.get('teams_cod_ibge') or teams_mun_nome
                    pop_info = c_ibge.fetch_single_municipality_population(ibge_lookup)
                    if pop_info:
                        db.save_population_batch([pop_info])

            if pop_info:
                p_censo = int(pop_info.get("pop_censo_2022", 0) or 0)
                p_est = int(pop_info.get("pop_estimada", p_censo) or p_censo)

                col_p_tipo1, col_p_tipo2 = st.columns([2, 2])
                with col_p_tipo1:
                    base_indiv_escolha = st.radio(
                        "Base Populacional para Dimensionamento:",
                        [f"Estimativa Recente ({p_est:,d} hab.)", f"Censo Demográfico 2022 ({p_censo:,d} hab.)"],
                        horizontal=True,
                        key="rad_pop_indiv"
                    )
                pop_base = p_est if "Estimativa" in base_indiv_escolha else p_censo

                indicadores_m = IBGEClient.calculate_health_coverage(
                    populacao=pop_base,
                    qtd_esf=int(total_esf),
                    qtd_eap=int(total_eap),
                    qtd_esb=int(total_esb),
                    qtd_emulti=int(total_emulti)
                )

                col_mc1, col_mc2, col_mc3, col_mc4 = st.columns(4)
                col_mc1.metric("👥 População Base", f"{pop_base:,d}".replace(",", "."))
                col_mc2.metric("🟢 Cobertura Total AB", f"{indicadores_m['cobertura_total_pct']}%", delta=indicadores_m['diagnostico'])
                col_mc3.metric("👨‍👩‍👧‍👦 População Coberta", f"{indicadores_m['pop_coberta']:,d}".replace(",", "."))
                col_mc4.metric("⚠️ População Desassistida", f"{indicadores_m['pop_descoberta']:,d}".replace(",", "."))

                st.markdown("---")
                col_md1, col_md2, col_md3, col_md4 = st.columns(4)
                hab_esf_fmt = f"{indicadores_m['hab_por_esf']:,d}".replace(",", ".") if indicadores_m['hab_por_esf'] else "Sem ESF"
                col_md1.metric("📉 Habitantes por ESF", hab_esf_fmt, help="Parâmetro PNAB/MS: Média de 3.000 pessoas por equipe (máx. 3.500).")
                
                hab_ab_fmt = f"{indicadores_m['hab_por_equipe_total']:,d}".replace(",", ".") if indicadores_m['hab_por_equipe_total'] else "-"
                col_md2.metric("🩺 Hab. / Equipe Total AB", hab_ab_fmt, help="Considerando ESF + EAP.")
                
                col_md3.metric("🦷 Cobertura Saúde Bucal", f"{indicadores_m['cobertura_esb_pct']}%")
                col_md4.metric("🚨 Déficit de Equipes ESF", f"{indicadores_m['deficit_esf']} equipes", help="Equipes adicionais de ESF necessárias para alcançar 100% de cobertura.")

                st.markdown("")
                eq_necessarias = math.ceil(pop_base / 3000) if pop_base > 0 else 0
                st.info(f"📋 **Diagnóstico da Atenção Primária:** {indicadores_m['diagnostico']}. O município de **{teams_mun_nome}** possui **{total_esf} equipes de ESF** e **{total_eap} equipes de EAP**. Para cobrir plenamente os **{pop_base:,d} habitantes**, seria necessária uma capacidade equivalente a **{eq_necessarias} equipes de Saúde da Família**.")
            else:
                st.info("População deste município não encontrada na base local do IBGE. Utilize o botão 'Sincronizar com API IBGE' no painel principal.")

        with tab_eq_graf:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("##### Distribuição por Tipo de Equipe")
                if 'dsEquipe' in df_teams.columns:
                    tipo_counts = df_teams['dsEquipe'].value_counts()
                    st.bar_chart(tipo_counts)

            with col_g2:
                st.markdown("##### Top 10 Unidades com Maior Quantidade de Equipes")
                if 'noFantasia' in df_teams.columns:
                    unidade_counts = df_teams['noFantasia'].value_counts().head(10)
                    st.bar_chart(unidade_counts)

        with tab_eq_unidades:
            st.markdown("##### Quantitativo de Equipes por Estabelecimento / UBS")
            st.caption("Consolidado de equipes por unidade básica com segregação entre ESF, EAP, ESB e EMULTI.")

            if 'noFantasia' in df_teams.columns and 'cnes' in df_teams.columns:
                def c_esf(s):
                    return s.apply(lambda x: 1 if ('ESF' in str(x).upper() or str(x) == '70') else 0).sum()
                def c_eap(s):
                    return s.apply(lambda x: 1 if ('EAP' in str(x).upper() or 'ATENCAO PRIMARIA' in str(x).upper()) and 'EMULTI' not in str(x).upper() else 0).sum()
                def c_esb(s):
                    return s.apply(lambda x: 1 if ('ESB' in str(x).upper() or 'SAUDE BUCAL' in str(x).upper()) else 0).sum()
                def c_emulti(s):
                    return s.apply(lambda x: 1 if ('EMULTI' in str(x).upper() or 'MULTIPROFISSIONAL' in str(x).upper()) else 0).sum()

                resumo_por_ubs = df_teams.groupby(['cnes', 'noFantasia']).agg(
                    Total_Equipes=('coEquipe', 'count'),
                    ESF=('dsEquipe', c_esf),
                    EAP=('dsEquipe', c_eap),
                    ESB=('dsEquipe', c_esb),
                    EMULTI=('dsEquipe', c_emulti),
                ).reset_index()

                resumo_por_ubs['Outras'] = resumo_por_ubs['Total_Equipes'] - (
                    resumo_por_ubs['ESF'] + resumo_por_ubs['EAP'] + resumo_por_ubs['ESB'] + resumo_por_ubs['EMULTI']
                )
                resumo_por_ubs = resumo_por_ubs.sort_values('Total_Equipes', ascending=False)
                resumo_por_ubs_show = resumo_por_ubs.rename(columns={
                    'cnes': 'CNES',
                    'noFantasia': 'Unidade Básica de Saúde',
                    'Total_Equipes': 'Total de Equipes',
                    'ESF': 'Qtd ESF',
                    'EAP': 'Qtd EAP',
                    'ESB': 'Qtd ESB',
                    'EMULTI': 'Qtd EMULTI',
                    'Outras': 'Outras Equipes'
                })
                st.dataframe(resumo_por_ubs_show, use_container_width=True, height=500)

        with tab_eq_lista:
            st.markdown("##### Filtros Interativos")
            col_fl1, col_fl2, col_fl3 = st.columns(3)

            with col_fl1:
                tipos_eq_disp = sorted(df_teams['dsEquipe'].dropna().unique().tolist()) if 'dsEquipe' in df_teams.columns else []
                sel_tipos_eq = st.multiselect("Filtrar Tipo de Equipe:", options=tipos_eq_disp, default=[])

            with col_fl2:
                ubs_disp = ["Todas"] + sorted(df_teams['noFantasia'].dropna().unique().tolist()) if 'noFantasia' in df_teams.columns else ["Todas"]
                sel_ubs_eq = st.selectbox("Filtrar por Unidade de Saúde:", options=ubs_disp)

            with col_fl3:
                sel_status_eq = st.radio("Status da Equipe:", ["Todas", "Apenas Ativas", "Apenas Desativadas"], horizontal=True)

            busca_eq = st.text_input("🔍 Buscar por Nome da Equipe ou Código INE:", "")

            # Aplicar filtros
            df_eq_filtered = df_teams.copy()
            if sel_tipos_eq:
                df_eq_filtered = df_eq_filtered[df_eq_filtered['dsEquipe'].isin(sel_tipos_eq)]
            if sel_ubs_eq != "Todas":
                df_eq_filtered = df_eq_filtered[df_eq_filtered['noFantasia'] == sel_ubs_eq]
            if sel_status_eq == "Apenas Ativas":
                df_eq_filtered = df_eq_filtered[df_eq_filtered['status'] == 'Ativa']
            elif sel_status_eq == "Apenas Desativadas":
                df_eq_filtered = df_eq_filtered[df_eq_filtered['status'] != 'Ativa']
            if busca_eq.strip():
                termo = busca_eq.strip().upper()
                df_eq_filtered = df_eq_filtered[
                    df_eq_filtered['nomeEquipe'].astype(str).str.upper().str.contains(termo) |
                    df_eq_filtered['coEquipe'].astype(str).str.upper().str.contains(termo)
                ]

            st.caption(f"Exibindo **{len(df_eq_filtered)}** de **{len(df_teams)}** equipes.")

            cols_eq_show = {
                'cnes': 'CNES',
                'noFantasia': 'Estabelecimento de Saúde',
                'coEquipe': 'Código INE',
                'nomeEquipe': 'Nome da Equipe',
                'dsEquipe': 'Tipo de Equipe',
                'dsArea': 'Área de Atuação',
                'dtAtivacao': 'Data Ativação',
                'dtDesativacao': 'Data Desativação',
                'status': 'Status'
            }
            present_eq_cols = [c for c in cols_eq_show.keys() if c in df_eq_filtered.columns]
            st.dataframe(df_eq_filtered[present_eq_cols].rename(columns=cols_eq_show), use_container_width=True, height=600)

# -----------------------------------------------------------------------------
# 5. EVOLUÇÃO DE LEITOS (POR GRUPO E TIPO)
# -----------------------------------------------------------------------------
elif menu == "🛏️ Evolução de Leitos":
    st.subheader("📊 Evolução Histórica do Quantitativo de Leitos")
    st.caption("Acompanhe o crescimento e a evolução progressiva dos leitos por Grupo (Atributo) e Tipo específico, com separação explícita entre Leitos SUS, Não-SUS e Totais.")

    # --- 1. Seleção de CNES e Download de Competências Históricas ---
    col_l1, col_l2 = st.columns([3, 2])
    
    with col_l1:
        cnes_input_leitos = st.text_input("Código CNES do Estabelecimento:", value="2705982", help="Ex: 2705982 (Santa Casa de Franca)")
    
    with col_l2:
        st.write("")
        st.write("")
        exp_batch = st.expander("📥 Extrair Histórico de Competências da API", expanded=False)

    with exp_batch:
        st.markdown("##### Extração de Múltiplas Competências por Período")
        st.caption("Extraia um intervalo completo de anos/meses (ex: de 2020 até o ano atual). O sistema insere um delay automático entre cada requisição para não sobrecarregar os servidores do Ministério da Saúde.")
        
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1:
            ano_ini = st.number_input("Ano Inicial:", min_value=2015, max_value=2030, value=2020, help="Ano de início da série histórica")
        with col_b2:
            ano_fim = st.number_input("Ano Final:", min_value=2015, max_value=2030, value=2026, help="Ano de término da série histórica")
        with col_b3:
            freq = st.selectbox(
                "Frequência:",
                ["Semestral (Jan/Jul - Recomendado)", "Mensal (Todos os 12 meses)", "Anual (Janeiro de cada ano)"],
                help="Selecione 'Semestral' ou 'Anual' para obter uma curva histórica representativa rapidamente."
            )
        with col_b4:
            delay_opt = st.selectbox(
                "Delay entre requisições:",
                ["0.3s (Recomendado)", "0.5s (Mais Seguro)", "1.0s (Modo Lento)", "0.15s (Rápido)"],
                help="Intervalo de pausa entre cada chamada à API CNES para evitar sobrecarga ou bloqueio no DATASUS."
            )

        delay_val_map = {
            "0.3s (Recomendado)": 0.3,
            "0.5s (Mais Seguro)": 0.5,
            "1.0s (Modo Lento)": 1.0,
            "0.15s (Rápido)": 0.15
        }
        delay_val = delay_val_map.get(delay_opt, 0.3)

        btn_fetch_batch = st.button("🚀 Iniciar Extração em Lote do Período", use_container_width=True)

        if btn_fetch_batch:
            cnes_code_clean = cnes_input_leitos.strip()
            # Montar lista de competências YYYYMM
            comps_to_fetch = []
            for ano in range(int(ano_ini), int(ano_fim) + 1):
                if "Semestral" in freq:
                    meses = [1, 7]
                elif "Anual" in freq:
                    meses = [1]
                else:
                    meses = list(range(1, 13))
                for mes in meses:
                    comp_str = f"{ano}{mes:02d}"
                    comps_to_fetch.append(comp_str)

            est_tempo_sec = len(comps_to_fetch) * (delay_val + 0.3)
            st.info(f"🔄 Agendando a extração de **{len(comps_to_fetch)} competências** (`{comps_to_fetch[0]}` a `{comps_to_fetch[-1]}`) para o CNES `{cnes_code_clean}` (Tempo estimado: ~{int(est_tempo_sec)}s)...")
            p_bar = st.progress(0, text="Iniciando download em lote...")
            
            def p_callback(curr, tot, msg):
                if tot > 0:
                    p_bar.progress(min(curr / tot, 1.0), text=f"[{curr}/{tot}] Processando {msg}")

            client.fetch_competencia_history(
                cnes_code_clean,
                comps_to_fetch,
                db,
                delay_between_requests=delay_val,
                progress_callback=p_callback
            )
            st.success(f"✅ {len(comps_to_fetch)} competências extraídas e armazenadas no banco de dados local com sucesso!")
            st.rerun()

    # --- 2. Carregar Histórico do Banco Local ---
    cnes_target = cnes_input_leitos.strip()
    history_records = db.get_leitos_evolution_history(cnes_target)

    if not history_records:
        st.warning(f"⚠️ Nenhuma competência salva no banco local para o CNES `{cnes_target}`. Clique em 'Extrair Histórico de Competências da API' acima ou consulte o CNES no menu '🔍 Consultar CNES' primeiro.")
    else:
        df_l_hist = pd.DataFrame(history_records)
        comps_salvas = sorted(df_l_hist['competencia'].unique().tolist())
        
        st.success(f"📌 {len(comps_salvas)} competências salvas no histórico local (`{comps_salvas[0]}` a `{comps_salvas[-1]}`).")

        st.markdown("---")
        st.markdown("### 🔎 Filtros de Leitos")

        col_fl1, col_fl2, col_fl3 = st.columns(3)

        with col_fl1:
            # Filtro de Grupo de Leito (dsAtributo) - Suporte a seleção múltipla
            grupos_disponiveis = sorted(df_l_hist['dsAtributo'].dropna().unique().tolist())
            grupos_sel = st.multiselect(
                "Grupo(s) de Leito (Atributo):",
                options=grupos_disponiveis,
                default=[],
                help="Selecione um ou mais grupos de leito (ex: ESPEC - CIRURGICO e ESPEC - CLINICO para somar os leitos de enfermaria). Deixe vazio para incluir Todos os Grupos."
            )

        # Filtrar por grupo(s) selecionado(s) para alimentar o próximo dropdown de tipos
        df_grupo = df_l_hist.copy()
        if grupos_sel:
            df_grupo = df_grupo[df_grupo['dsAtributo'].isin(grupos_sel)]

        with col_fl2:
            # Filtro de Tipo Específico de Leito (dsLeito)
            tipos_disponiveis = sorted(df_grupo['dsLeito'].unique().tolist())
            tipos_sel = st.multiselect(
                "Tipo Específico de Leito:",
                options=tipos_disponiveis,
                default=[],
                help="Selecione um ou mais tipos específicos de leito. Deixe vazio para incluir todos os tipos do grupo."
            )

        with col_fl3:
            # Métrica a visualizar no gráfico principal
            metrica_vis = st.radio(
                "Visualização das Métricas:",
                ["🩺 Leitos SUS", "💼 Leitos Não-SUS", "📊 Leitos Totais (Existentes)", "📈 Comparativo Completo (SUS vs Não-SUS vs Total)"],
                index=0
            )

        # Aplicar filtros ao DataFrame
        df_filtered_hist = df_grupo.copy()
        if tipos_sel:
            df_filtered_hist = df_filtered_hist[df_filtered_hist['dsLeito'].isin(tipos_sel)]

        # --- 3. KPIs Resumo Histórico ---
        st.markdown("---")
        
        # Pegar dados da competência mais recente e mais antiga para deltas
        comp_rec = comps_salvas[-1]
        comp_ant = comps_salvas[0]

        df_rec = df_filtered_hist[df_filtered_hist['competencia'] == comp_rec]
        df_ant = df_filtered_hist[df_filtered_hist['competencia'] == comp_ant]

        rec_sus = df_rec['qtSus'].sum()
        ant_sus = df_ant['qtSus'].sum()
        delta_sus = int(rec_sus - ant_sus)

        rec_nao_sus = df_rec['qtNaoSus'].sum()
        ant_nao_sus = df_ant['qtNaoSus'].sum()
        delta_nao_sus = int(rec_nao_sus - ant_nao_sus)

        rec_tot = df_rec['qtExistente'].sum()
        ant_tot = df_ant['qtExistente'].sum()
        delta_tot = int(rec_tot - ant_tot)

        kpi_l1, kpi_l2, kpi_l3, kpi_l4 = st.columns(4)
        kpi_l1.metric("🩺 Leitos SUS (Última Comp.)", rec_sus, delta=f"{delta_sus:+d} leitos (vs {comp_ant})")
        kpi_l2.metric("💼 Leitos Não-SUS (Última Comp.)", rec_nao_sus, delta=f"{delta_nao_sus:+d} leitos (vs {comp_ant})")
        kpi_l3.metric("📊 Leitos Totais (Última Comp.)", rec_tot, delta=f"{delta_tot:+d} leitos (vs {comp_ant})")
        kpi_l4.metric("📅 Intervalo Analisado", f"{comp_ant} ➔ {comp_rec}")

        # --- 4. Gráficos de Evolução Temporal ---
        st.markdown("---")
        st.markdown("### 📈 Gráfico de Evolução Temporal")

        # Agrupar por competência
        if metrica_vis == "📈 Comparativo Completo (SUS vs Não-SUS vs Total)":
            df_chart = df_filtered_hist.groupby('competencia').agg(
                Leitos_SUS=('qtSus', 'sum'),
                Leitos_Nao_SUS=('qtNaoSus', 'sum'),
                Leitos_Totais=('qtExistente', 'sum')
            )
            st.line_chart(df_chart, use_container_width=True)
        else:
            field_map = {
                "🩺 Leitos SUS": 'qtSus',
                "💼 Leitos Não-SUS": 'qtNaoSus',
                "📊 Leitos Totais (Existentes)": 'qtExistente'
            }
            target_field = field_map[metrica_vis]

            # Se houver múltiplos tipos selecionados, mostrar linhas individuais por tipo de leito
            if tipos_sel and len(tipos_sel) > 1:
                piv_chart = df_filtered_hist.pivot_table(
                    index='competencia',
                    columns='dsLeito',
                    values=target_field,
                    aggfunc='sum',
                    fill_value=0
                )
                st.line_chart(piv_chart, use_container_width=True)
            else:
                df_chart = df_filtered_hist.groupby('competencia')[target_field].sum()
                st.line_chart(df_chart, use_container_width=True)

        # --- 5. Tabela Detalhada & Download Excel ---
        st.markdown("---")
        tab_mat, tab_det = st.tabs(["📊 Matriz Comparativa por Competência", "📋 Tabela Detalhada de Leitos"])

        with tab_mat:
            st.markdown("#### Distribuição de Leitos por Tipo e Competência")
            matriz_sus = df_filtered_hist.pivot_table(
                index=['dsAtributo', 'dsLeito'],
                columns='competencia',
                values=['qtSus', 'qtExistente'],
                aggfunc='sum',
                fill_value=0
            )
            st.dataframe(matriz_sus, use_container_width=True)

        with tab_det:
            st.markdown("#### Registros Individuais por Competência")
            cols_det = {
                'competencia': 'Competência',
                'dsAtributo': 'Grupo (Atributo)',
                'dsLeito': 'Tipo de Leito',
                'qtSus': 'Leitos SUS',
                'qtNaoSus': 'Leitos Não-SUS',
                'qtExistente': 'Leitos Totais Existentes',
                'coLeito': 'Código Leito (ID)'
            }
            present_det = [c for c in cols_det.keys() if c in df_filtered_hist.columns]
            st.dataframe(df_filtered_hist[present_det].rename(columns=cols_det), use_container_width=True, height=500)

        # Download do Relatório em Excel
        excel_leitos_bytes = CNESExporter.export_leitos_evolution_report(history_records, cnes_target)
        st.download_button(
            label=f"📥 Baixar Relatório Completo de Leitos em Excel (CNES {cnes_target})",
            data=excel_leitos_bytes,
            file_name=f"Evolucao_Leitos_CNES_{cnes_target}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# -----------------------------------------------------------------------------
# 6. HISTÓRICO LOCAL
# -----------------------------------------------------------------------------
elif menu == "📚 Histórico Local":
    st.subheader("Estabelecimentos Armazenados no Histórico Local")
    
    estabelecimentos = db.list_estabelecimentos()
    if not estabelecimentos:
        st.info("Nenhum estabelecimento salvo ainda no banco SQLite local.")
    else:
        df_est = pd.DataFrame(estabelecimentos)
        st.dataframe(df_est, use_container_width=True)

        st.markdown("---")
        cnes_sel = st.selectbox("Selecione um CNES para ver suas competências salvas:", df_est['cnes'].unique())
        
        if cnes_sel:
            comps = db.list_competencias(cnes_sel)
            st.markdown(f"#### Competências Salvas para CNES `{cnes_sel}`")
            if comps:
                df_c = pd.DataFrame(comps)
                st.dataframe(df_c, use_container_width=True)

                if len(comps) > 1:
                    st.markdown("#### 📈 Evolução ao Longo do Tempo")
                    chart_data = df_c.sort_values('competencia')[['competencia', 'num_profissionais', 'num_leitos']].set_index('competencia')
                    st.line_chart(chart_data)

# -----------------------------------------------------------------------------
# 7. COMPARAR COMPETÊNCIAS
# -----------------------------------------------------------------------------
elif menu == "📊 Comparar Competências":
    st.subheader("Comparação de Evolução Histórica (Competência A vs Competência B)")
    
    estabelecimentos = db.list_estabelecimentos()
    if not estabelecimentos:
        st.warning("É necessário ter ao menos um CNES com competências salvas no banco para realizar a comparação.")
    else:
        cnes_comp = st.selectbox("Selecione o CNES para comparar:", [e['cnes'] for e in estabelecimentos])
        comps_disponiveis = [c['competencia'] for c in db.list_competencias(cnes_comp)]
        
        if len(comps_disponiveis) < 2:
            st.info(f"O CNES `{cnes_comp}` possui apenas {len(comps_disponiveis)} competência salva. Extraia outra competência na tela inicial para comparar.")
        else:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                comp_a = st.selectbox("Competência Anterior (Base):", comps_disponiveis, index=len(comps_disponiveis)-1)
            with col_c2:
                comp_b = st.selectbox("Competência Recente (Comparada):", comps_disponiveis, index=0)

            if comp_a == comp_b:
                st.warning("Selecione duas competências diferentes para visualizar o comparativo.")
            else:
                diff = db.compare_competencias(cnes_comp, comp_a, comp_b)
                if "erro" in diff:
                    st.error(diff["erro"])
                else:
                    p = diff['profissionais']
                    l = diff['leitos']

                    st.markdown("---")
                    st.markdown(f"### Relatório Comparativo: Competência `{comp_a}` ➔ `{comp_b}`")

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Profissionais (Total)", p['total_novo'], delta=p['diferenca'])
                    c2.metric("Profissionais Ingressantes", len(p['novos_ingressos']))
                    c3.metric("Profissionais Desligados", len(p['desligados']))
                    c4.metric("Leitos Existentes", l['total_existente_novo'], delta=l['diferenca_existente'])

                    if p['novos_ingressos']:
                        with st.expander("🆕 Ver Profissionais Ingressantes/Novos"):
                            st.dataframe(pd.DataFrame(p['novos_ingressos']))

                    if p['desligados']:
                        with st.expander("🚪 Ver Profissionais Desligados/Saídas"):
                            st.dataframe(pd.DataFrame(p['desligados']))

# -----------------------------------------------------------------------------
# 8. INFORMAÇÕES TÉCNICAS
# -----------------------------------------------------------------------------
elif menu == "ℹ️ Informações Técnicas":
    st.markdown("""
    ### 🛡️ Boas Práticas & Arquitetura de Dados CNES

    - **Extração Pontual & Não Invasiva:** Este extrator realiza chamadas leves e sequenciais apenas para os estabelecimentos solicitados pelo usuário, sem sobrecarregar os servidores do DATASUS.
    - **Fonte Oficial:** Os dados são provenientes dos webservices públicos de API REST do CNES (`https://cnes.datasus.gov.br/services/`).
    - **Banco de Dados Local:** Os snapshots históricos são armazenados em `data/historico_cnes.db` (SQLite local).
    - **Exportação:** Suporte completo à exportação formatada em abas de Excel (`.xlsx`).
    """)
