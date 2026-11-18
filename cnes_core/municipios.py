"""
Módulo de constante e utilitários para municípios do DRS VIII (Franca e Região).
DRS VIII - Departamento Regional de Saúde VIII (Franca/SP), composto por 22 municípios.
"""

from typing import List, Dict, Tuple, Optional
import streamlit as st

MUNICIPIOS_DRS_VIII: List[Dict[str, str]] = [
    {"nome": "Aramina", "ibge": "350300", "uf": "SP"},
    {"nome": "Buritizal", "ibge": "350820", "uf": "SP"},
    {"nome": "Cristais Paulista", "ibge": "351320", "uf": "SP"},
    {"nome": "Franca", "ibge": "351620", "uf": "SP"},
    {"nome": "Guará", "ibge": "351770", "uf": "SP"},
    {"nome": "Igarapava", "ibge": "352010", "uf": "SP"},
    {"nome": "Ipuã", "ibge": "352130", "uf": "SP"},
    {"nome": "Itirapuã", "ibge": "352370", "uf": "SP"},
    {"nome": "Ituverava", "ibge": "352410", "uf": "SP"},
    {"nome": "Jeriquara", "ibge": "352540", "uf": "SP"},
    {"nome": "Miguelópolis", "ibge": "352970", "uf": "SP"},
    {"nome": "Morro Agudo", "ibge": "353190", "uf": "SP"},
    {"nome": "Nuporanga", "ibge": "353360", "uf": "SP"},
    {"nome": "Orlândia", "ibge": "353430", "uf": "SP"},
    {"nome": "Patrocínio Paulista", "ibge": "353630", "uf": "SP"},
    {"nome": "Pedregulho", "ibge": "353700", "uf": "SP"},
    {"nome": "Restinga", "ibge": "354270", "uf": "SP"},
    {"nome": "Ribeirão Corrente", "ibge": "354310", "uf": "SP"},
    {"nome": "Rifaina", "ibge": "354360", "uf": "SP"},
    {"nome": "Sales Oliveira", "ibge": "354490", "uf": "SP"},
    {"nome": "São Joaquim da Barra", "ibge": "354940", "uf": "SP"},
    {"nome": "São José da Bela Vista", "ibge": "354950", "uf": "SP"},
]

# Mapa rápido de Código IBGE (6 dígitos) -> Nome do Município
IBGE_TO_NAME: Dict[str, str] = {m["ibge"]: m["nome"] for m in MUNICIPIOS_DRS_VIII}


def render_municipio_selector(
    key_prefix: str = "mun",
    default_ibge: str = "351620"
) -> Tuple[str, str]:
    """
    Renderiza um seletor interativo em Streamlit com duas opções:
    1. Biblioteca dos 22 municípios do DRS VIII (Franca e Região) com seleção direta.
    2. Digitação manual do código IBGE de 6 dígitos para qualquer município do Brasil.

    Retorna uma tupla (codigo_ibge, nome_municipio).
    """
    modo = st.radio(
        "Forma de identificação do município:",
        options=[
            "🏛️ Biblioteca DRS VIII (Franca e Região - 22 Municípios)",
            "✏️ Digitar outro Código IBGE (Brasil)"
        ],
        horizontal=True,
        key=f"{key_prefix}_modo_selecao"
    )

    if "DRS VIII" in modo:
        # Prepara lista de opções com Franca como padrão
        opcoes = [f"{m['nome']} ({m['ibge']})" for m in MUNICIPIOS_DRS_VIII]
        default_index = next(
            (i for i, m in enumerate(MUNICIPIOS_DRS_VIII) if m["ibge"] == default_ibge),
            3 # Franca é índice 3 na lista alfabética
        )
        escolha = st.selectbox(
            "Selecione o Município do DRS VIII:",
            options=opcoes,
            index=default_index,
            key=f"{key_prefix}_select_drs"
        )
        # Extrai o código IBGE dentro dos parênteses
        codigo_ibge = escolha.split("(")[-1].replace(")", "").strip()
        nome_mun = escolha.split(" (")[0].strip()
        return codigo_ibge, nome_mun
    else:
        col1, col2 = st.columns([2, 3])
        with col1:
            codigo_ibge = st.text_input(
                "Código IBGE (6 dígitos, sem DV):",
                value=default_ibge,
                help="Ex: 351620 (Franca), 355030 (São Paulo), 330455 (Rio de Janeiro).",
                key=f"{key_prefix}_input_ibge"
            ).strip()
        with col2:
            nome_sug = IBGE_TO_NAME.get(codigo_ibge, "")
            nome_manual = st.text_input(
                "Nome do Município (Opcional):",
                value=nome_sug,
                help="Identificador textual para exibição e relatórios.",
                key=f"{key_prefix}_input_nome"
            ).strip()
        return codigo_ibge, (nome_manual or f"Município {codigo_ibge}")
