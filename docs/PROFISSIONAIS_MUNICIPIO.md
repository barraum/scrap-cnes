# Módulo de Extração de Profissionais de Saúde por Município (CNES)

Este documento registra a implementação e documentação técnica do módulo de **Extração em Lote e Consolidação de Profissionais de Saúde por Município** do Cadastro Nacional de Estabelecimentos de Saúde (CNES/DATASUS).

---

## 🎯 Objetivo

Permitir que o usuário consulte, filtre por especialidade (CBO), analise cargas horárias e tipos de vínculos de **todos os profissionais de saúde** cadastrados nos estabelecimentos de um determinado município (ex: Franca/SP), com suporte a:
- **Consolidação em Tabela Única & Persistência Local (SQLite)**: Gravação automática no banco de dados local (`historico_cnes.db`) para acesso instantâneo sem necessidade de re-extração.
- **Detalhamento das Ocupações (CBO)**: Identificação da especialidade (ex: *Médico Clínico, Enfermeiro, Psicólogo, Técnico de Enfermagem*).
- **Detalhamento de Cargas Horárias**: Divisão da carga horária semanal em *Ambulatorial*, *Hospitalar*, *Outras* e *Total Semanal*.
- **Auditoria de Acúmulo de Vínculos & Carga Horária**: Detecção automática de profissionais que atuam em múltiplos estabelecimentos simultaneamente, com somatório total de horas semanais (com alerta para cargas excessivas > 60h).
- **Vínculos Empregatícios**: Identificação de *Vinculação* (ex: Vínculo Empregatício, Autônomo) e *Tipo de Vínculo* (ex: Celetista, Estatutário).
- **Indicador SUS**: Confirmação se o profissional presta atendimento pelo SUS.

---

## 🏗️ Arquitetura e Fluxo de Dados

A extração e armazenamento funcionam em três camadas:

1. **Listagem dos Estabelecimentos com Pré-Filtragem**:
   - Endpoint: `GET /services/estabelecimentos?municipio={codigo_ibge_6digitos}`
   - O usuário pode pré-filtrar por **Natureza Jurídica** (ex: *1 - Administração Pública*), **Gestão** ou **Atendimento SUS** para reduzir o universo de estabelecimentos antes do download.
   - *Exemplo*: Em Franca/SP, selecionar *Administração Pública* reduz os estabelecimentos de **1.333** para apenas **81**, tornando a extração de profissionais públicos ultrarrápida (~20 segundos).

2. **Extração de Profissionais por Estabelecimento**:
   - Endpoint: `GET /services/estabelecimentos-profissionais/{coUnidade}`
   - Retorna a ficha completa dos profissionais vinculados a cada estabelecimento (`coUnidade`).
   - O sistema enriquece cada registro profissional anexando o código `cnes`, `noFantasia` (Nome Fantasia) e `noEmpresarial` (Razão Social) do estabelecimento onde atua.

3. **Persistência Estruturada no SQLite (`historico_cnes.db`)**:
   - Tabela `profissionais`: armazena todos os registros vinculados por município e competência com índices de alta performance para `cns`, `nome`, `cbo` e `(municipio, competencia)`.
   - Permite consultas locais em milissegundos através da aba **"📂 Consultar Base Local Salva"**.

---

## 📂 Arquivos Modificados / Criados

| Arquivo | Descrição das Alterações |
|---|---|
| [cnes_core/database.py](../cnes_core/database.py) | Criada a tabela `profissionais`, índices e métodos `save_professionals()`, `get_saved_professionals()`, `list_saved_professional_municipalities()` e `get_multiple_bonds_analysis()`. |
| [cnes_core/client.py](../cnes_core/client.py) | Métodos `fetch_establishment_professionals()` e `fetch_municipality_professionals()`. |
| [cnes_core/exporter.py](../cnes_core/exporter.py) | Método `export_municipality_professionals_report()` com aba dedicada para **Acúmulo de Vínculos**. |
| [app.py](../app.py) | Menu **`👥 Profissionais por Município`** com opções de extração da API ou carregamento da base local, KPIs, busca por Nome/CNS, multiselect por CBO/Vínculo, gráficos estatísticos e aba de **Auditoria de Acúmulo de Vínculos & Carga Horária**. |
| [docs/PROFISSIONAIS_MUNICIPIO.md](PROFISSIONAIS_MUNICIPIO.md) | Documentação técnica e registro histórico. |

---

## 🖥️ Como Utilizar no Dashboard Streamlit

1. Execute a aplicação (via `iniciar.bat` ou `streamlit run app.py`).
2. No menu lateral, acesse **`👥 Profissionais por Município`**.
3. Escolha a origem dos dados:
   - **🌐 Nova Extração da API**: Informe o código IBGE (ex: `351620`), aplique os pré-filtros e clique em **Extrair e Salvar no Banco Local**.
   - **📂 Consultar Base Local Salva**: Selecione um município/competência já salvo anteriormente e clique em **Carregar Dados do Banco Local** para abertura instantânea.
4. Explore as abas de resultados:
   - **📊 Top Especialidades**: Gráficos de barras com as especialidades mais comuns.
   - **📊 Por Tipo de Vínculo**: Distribuição entre vínculos estatutários, celetistas, autônomos, etc.
   - **📋 Tabela de Profissionais**: Consulta completa com filtros dinâmicos por CBO ou Nome/CNS.
   - **⚠️ Auditoria de Vínculos Múltiplos & Carga Horária**: Painel com filtros de quantidade mínima de vínculos e carga horária semanal para detectar acúmulo de cargos e sobrecargas de jornada (> 60h).
5. Baixe o relatório completo em Excel (`.xlsx`) clicando em **`📥 Baixar Relatório Completo de Profissionais em Excel`**.
