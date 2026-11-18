# 🏥 Extrator & Histórico CNES (DATASUS)

Solução inteligente, enxuta e de alto desempenho para consulta, histórico por competência (`YYYYMM`) e exportação de dados públicos de estabelecimentos de saúde cadastrados no CNES (Cadastro Nacional de Estabelecimentos de Saúde / DATASUS).

## ⚡ Inicialização Rápida no Windows (.bat)

Basta dar um duplo clique nos arquivos executáveis na pasta do projeto:

- **`iniciar.bat`**: Menu principal interativo (Painel Web, Consulta CLI, Histórico).
- **`iniciar_dashboard.bat`**: Abre diretamente o Painel Web no navegador.

---

## 🌟 Principais Recursos

- **Extração Pontual & Polida:** Sem raspagem massiva em lote. Respeita a infraestrutura do DATASUS com requisições suaves.
- **Biblioteca DRS VIII Integrada:** Acesso imediato aos 22 municípios da região de Franca/SP sem necessidade de pesquisar códigos IBGE na internet.
- **Módulo de Equipes de Saúde (ESF / EAP / ESB / EMULTI):** Quantificação e detalhamento por unidade básica de saúde, com código INE e situação de ativação.
- **Módulo de Profissionais por Município:** Detalhamento de vínculos, CBOs e auditoria de acúmulo de vínculos e carga horária semanal (> 60h).
- **Módulo de Consulta por Município:** Classificação de estabelecimentos (UBS, Hospitais, Ambulatórios, etc.) e tipo de gestão.
- **Histórico Local por Competência (`YYYYMM`) / Modo Offline:** Armazena pesquisas em banco SQLite local (`data/historico_cnes.db`) para consultas instantâneas mesmo com a API do DATASUS fora do ar.
- **Exportação Profissional em Excel (`.xlsx`):** Planilhas formatadas e padronizadas com abas de resumos estatísticos e listagens completas.

---

## 🚀 Como Usar via Terminal

### 1. Dashboard Web (Streamlit)
```bash
streamlit run app.py
```

### 2. Interface de Linha de Comando (CLI)
```bash
# Consultar e exportar Excel
python cnes_cli.py --cnes 2705982 --export

# Ver histórico de competências salvas
python cnes_cli.py --history 2705982

# Listar todos os estabelecimentos no banco local
python cnes_cli.py --list
```

---

## 📁 Estrutura do Projeto

```
SCRAP CNES/
├── iniciar.bat              # Menu de inicialização rápida (Windows)
├── iniciar_dashboard.bat    # Atalho direto para o Painel Web (Streamlit)
├── app.py                   # Dashboard Web Interativo
├── cnes_cli.py              # Interface CLI de linha de comando
├── requirements.txt         # Dependências do projeto (Pip / Streamlit Cloud)
├── .gitignore               # Regras de exclusão de arquivos no Git
├── .streamlit/              # Configurações de tema e servidor do Streamlit
├── cnes_core/               # Módulos centrais da aplicação
│   ├── __init__.py
│   ├── client.py            # Cliente HTTP para a API REST do DATASUS
│   ├── database.py          # Gerenciador de persistência de dados (SQLite / Nuvem)
│   ├── exporter.py          # Exportador de relatórios estilizados em Excel (.xlsx)
│   ├── ibge.py              # Integração de dados populacionais do Censo IBGE 2022
│   └── municipios.py        # Biblioteca dos 22 municípios do DRS VIII (Franca/SP)
├── data/                    # Banco de dados local (historico_cnes.db)
├── output/                  # Diretório de relatórios gerados em Excel
└── docs/                    # 📚 Central de Documentações do Projeto
    ├── README.md            # Índice geral de documentações técnicas
    ├── GUIA_COMPARTILHAMENTO_NUVEM_LOCAL.md # Guia de implantação em Nuvem + Git + DB
    ├── EQUIPES_MUNICIPIO.md # Módulo de Equipes de Saúde (ESF, EAP, etc.)
    ├── PROFISSIONAIS_MUNICIPIO.md # Módulo de Profissionais e Auditoria de Vínculos
    └── CONSULTA_MUNICIPIO.md # Módulo de Consulta de Estabelecimentos por Município
```

---

## 📚 Documentação Técnica Completa

Para guias aprofundados sobre cada módulo e instruções de compartilhamento em nuvem, acesse a pasta [`docs/`](docs/).

