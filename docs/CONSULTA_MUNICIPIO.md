# Módulo de Extração de Estabelecimentos por Município (CNES)

Este documento registra a implementação e documentação técnica do módulo de **Consulta e Extração em Lote de Estabelecimentos de Saúde por Município** do Cadastro Nacional de Estabelecimentos de Saúde (CNES/DATASUS).

---

## 🎯 Objetivo

Permitir que o usuário consulte, quantifique e filtre **todos os estabelecimentos de saúde** de um município (ex: Franca/SP), identificando e classificando unidades como:
- **UBS (Unidades Básicas de Saúde)**
- Hospitais (Gerais e Especializados)
- Ambulatórios e Centros de Especialidades
- Clínicas, Farmácias e Laboratórios
- Tipo de Gestão (*Municipal*, *Estadual*, *Dupla*)
- Indicação de Atendimento ao SUS (*Sim* / *Não*)

---

## 🏗️ Arquitetura e Fluxo de Dados

A extração utiliza a API REST oficial do CNES (`https://cnes.datasus.gov.br/services/`) estruturada em duas etapas:

1. **Listagem Geral de Município e Pré-Filtragem**:
   - Endpoint: `GET /services/estabelecimentos?municipio={codigo_ibge_6digitos}`
   - Retorna a lista completa de estabelecimentos do município.
   - **Pré-Filtragem (Redução de Requisições)**: O sistema aplica filtros prévios como **Natureza Jurídica (Grupo)** (ex: *1 - Administração Pública*), **Gestão** e **Atende SUS** antes da importação detalhada. Em Franca/SP, por exemplo, selecionar *Administração Pública* reduz os requisições em lote de **1.333** para apenas **81 estabelecimentos**, tornando a extração ultrarrápida.

2. **Detalhamento e Classificação Individual (Modo Completo)**:
   - Endpoint: `GET /services/estabelecimentos/{coUnidade}`
   - Retorna a **Classificação do Estabelecimento** (`dsTipoEstabelecimento` - ex: `001 - UNIDADE BASICA DE SAUDE`), **Tipo de Unidade** (`dsTpUnidade`), Endereço Completo, Bairro, CEP, Telefone, E-mail e Coordenadas Geográficas (Latitude e Longitude).

---

## 📂 Arquivos Modificados / Criados

| Arquivo | Descrição das Alterações |
|---|---|
| [cnes_core/client.py](../cnes_core/client.py) | Adicionados os métodos `list_by_municipality()`, `fetch_establishment_detail()` e `fetch_municipality_details()` (com suporte a barra de progresso callback). |
| [cnes_core/exporter.py](../cnes_core/exporter.py) | Adicionado o método `export_municipality_report()` para gerar relatórios Excel (`.xlsx`) com abas de resumo por classificação, tipo de unidade, gestão e listagem completa. |
| [app.py](../app.py) | Criado o menu **`🏙️ Consulta por Município`** com suporte a filtros interativos, gráficos dinâmicos, métricas (KPIs) e download do relatório Excel. |
| [README.md](../README.md) | Documentação geral do projeto atualizada com o novo recurso. |

---

## 🖥️ Como Utilizar no Dashboard Streamlit

1. Execute a aplicação (via `iniciar.bat` ou `streamlit run app.py`).
2. No menu lateral, acesse **`🏙️ Consulta por Município`**.
3. Informe o código IBGE de 6 dígitos do município (exemplo: `351620` para Franca/SP ou `355030` para São Paulo/SP).
4. Escolha o modo de extração:
   - **🚀 Completo (com classificação)**: Recomendado. Traz a classificação exata (UBS, Hospital, etc.) e permite filtrar por tipo e gestão.
   - **⚡ Rápido (sem classificação)**: Retorno instantâneo para conferência de nomes e CNES.
5. Filtre os resultados diretamente na tela por **Classificação do Estabelecimento** ou **Tipo de Gestão**.
6. Baixe o relatório completo em formato Excel (`.xlsx`) pronto para uso e análises.
