# Módulo de Extração de Equipes de Saúde por Município (CNES)

Este documento registra a implementação técnica e o guia de uso do módulo de **Extração, Quantificação e Repositório Histórico de Equipes de Saúde por Município** (ESF, EAP, ESB, EMULTI, etc.) do Cadastro Nacional de Estabelecimentos de Saúde (CNES/DATASUS), com suporte à biblioteca de municípios do **DRS VIII (Franca e Região)**.

---

## 🎯 Objetivos do Módulo

1. **Quantificação e Detalhamento de Equipes de Saúde:**
   - **ESF (Estratégia Saúde da Família)**: Equipes completas da Saúde da Família.
   - **EAP (Equipe de Atenção Primária)**: Equipes médicas/de enfermagem da Atenção Primária em UBSs e unidades correlatas.
   - **ESB (Equipe de Saúde Bucal)**: Equipes de odontologia da Atenção Básica.
   - **EMULTI (Equipe Multiprofissional)**: Equipes multiprofissionais (antigo NASF).
   - **EMAD / EMAP**: Atenção Domiciliar (Melhor em Casa).
   - **Outras Equipes**: EAPP (Prisional), ECR (Consultório na Rua), etc.

2. **Biblioteca Integrada do DRS VIII (Franca e Região):**
   - Elimina a necessidade de pesquisar códigos IBGE na internet.
   - Menu com seleção direta dos **22 municípios** pertencentes ao DRS VIII (com Franca/SP como padrão).
   - Opção para digitar manualmente o código IBGE de 6 dígitos de qualquer outro município do Brasil.
   - Componente reutilizado também nos módulos de *Consulta por Município* e *Profissionais por Município*.

3. **Repositório Estruturado por Competência (Modo Offline / Resiliência de API):**
   - Persistência automática no banco SQLite local (`data/historico_cnes.db`).
   - Armazenamento particionado por município e competência (`YYYYMM` ou `Atual`).
   - Permite consultas e análises instantâneas mesmo quando a API do DATASUS estiver fora do ar ou com lentidão.

4. **Repositório de População IBGE & Indicadores de Cobertura (SUS/PNAB):**
   - Integração com as APIs oficiais do IBGE (Censo Demográfico 2022 e Estimativas Recentes).
   - Tabela local `populacao_ibge` persistida no SQLite com todos os municípios de São Paulo.
   - Cálculo automático dos indicadores normativos da Política Nacional de Atenção Básica (Portaria GM/MS nº 2.436/2017):
     - Habitantes por ESF (parâmetro: média recomendada de até 3.500 hab/ESF).
     - Habitantes por Equipe de Atenção Básica (ESF + EAP).
     - Cobertura Potencial da Atenção Básica (%).
     - População Coberta vs População Descoberta.
     - Déficit Estimado de Equipes para atingir 100% de cobertura.
     - Diagnóstico de Cobertura (🟢 Plena, 🟡 Regular, 🔴 Crítica).
   - **Panorama Regional DRS VIII**: Visão unificada com ranking de cobertura dos 22 municípios e exportação consolidada em Excel.

5. **Exportação Profissional em Excel (`.xlsx`):**
   - Planilhas estilizadas com:
     - **Panorama Regional DRS VIII (Cobertura & População)**: Visão de todos os municípios da região;
     - **Resumo por Tipo de Equipe** (Quantitativo de ativas, desativadas e total);
     - **Equipes por Unidade Básica** (Consolidação por UBS com número de ESF, EAP, ESB e EMULTI);
     - **Todas as Equipes (Listagem Completa)** (Código INE, Nome da Equipe, Tipo, Área de Atuação, Datas de Ativação/Desativação e Status).

---

## 🏛️ Municípios do DRS VIII (Franca e Região)

O módulo já possui cadastrado todos os 22 municípios que compõem o Departamento Regional de Saúde VIII da Secretaria de Estado da Saúde de SP:

| Município | Código IBGE (CNES) | UF |
| :--- | :---: | :---: |
| **Franca** | `351620` | SP |
| Aramina | `350300` | SP |
| Buritizal | `350820` | SP |
| Cristais Paulista | `351320` | SP |
| Guará | `351770` | SP |
| Igarapava | `352010` | SP |
| Ipuã | `352130` | SP |
| Itirapuã | `352370` | SP |
| Ituverava | `352410` | SP |
| Jeriquara | `352540` | SP |
| Miguelópolis | `352970` | SP |
| Morro Agudo | `353190` | SP |
| Nuporanga | `353360` | SP |
| Orlândia | `353430` | SP |
| Patrocínio Paulista | `353630` | SP |
| Pedregulho | `353700` | SP |
| Restinga | `354270` | SP |
| Ribeirão Corrente | `354310` | SP |
| Rifaina | `354360` | SP |
| Sales Oliveira | `354490` | SP |
| São Joaquim da Barra | `354940` | SP |
| São José da Bela Vista | `354950` | SP |

---

## 🏗️ Arquitetura Técnica

### 1. Endpoints Utilizados no DATASUS
- **Listagem de Estabelecimentos:**
  `GET https://cnes.datasus.gov.br/services/estabelecimentos?municipio={ibge6}`
- **Equipes por Estabelecimento:**
  `GET https://cnes.datasus.gov.br/services/estabelecimentos-equipes/{coUnidade}`
  - Suporta parâmetro `?competencia=AAAAMM` quando informado.
  - Campos extraídos: `tpEquipe`, `dsEquipe`, `coEquipe` (INE), `nomeEquipe`, `coArea`, `dsArea`, `dtAtivacao`, `dtDesativacao`, `quilombola`, `assentada`, `geral`, `escola`, `indigena`, `ribeirinha`.

### 2. Tabela no Banco de Dados SQLite (`data/historico_cnes.db`)
```sql
CREATE TABLE IF NOT EXISTS equipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnes TEXT,
    co_unidade TEXT,
    competencia TEXT,
    co_equipe TEXT,              -- INE (Identificador Nacional de Equipe)
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
);
```

---

## 🖥️ Como Utilizar no Painel Streamlit

1. Execute a aplicação via `iniciar.bat` ou `streamlit run app.py`.
2. No menu lateral, acesse **`🩺 Equipes por Município`**.
3. Escolha o modo de consulta:
   - **`🌐 Nova Extração da API (DATASUS)`**: Selecione um município do DRS VIII (ou digite um IBGE), aplique os pré-filtros (ex: *Administração Pública*) e clique em **`🩺 Extrair Equipes e Salvar no Repositório Local`**.
   - **`📂 Repositório Local Salvo (Histórico por Competência / Modo Offline)`**: Visualize o histórico de municípios e competências já salvas e clique em **`📂 Carregar Equipes`** para consulta instantânea sem necessidade de conexão com a API.
4. Visualize os KPIs de **Total**, **ESF**, **EAP**, **ESB**, **EMULTI** e **Equipes Ativas**.
5. Navegue pelas abas:
   - **📊 Indicadores & Gráficos**: Distribuição por tipo e ranking das unidades com mais equipes.
   - **🏥 Equipes por Unidade Básica**: Tabela consolidada por UBS com contagem de ESF, EAP, ESB, EMULTI.
   - **📋 Todas as Equipes**: Filtros dinâmicos por tipo, unidade, status e busca por nome ou código INE.
6. Baixe a planilha formatada clicando em **`📥 Baixar Relatório Completo de Equipes em Excel (.xlsx)`**.
