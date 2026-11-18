# 🌐 Guia Estratégico: Compartilhamento do Dashboard com a Equipe do MP (Nuvem + Local)

Este documento orienta a equipe do Ministério Público sobre como disponibilizar o **Dashboard CNES Analytics** em ambiente de nuvem e local, garantindo acesso facilitado por link para os membros da equipe e **persistência de dados centralizada**.

---

## 🧭 O Cenário Atual e a Necessidade

A equipe do MP (Promotores de Justiça, Analistas Jurídicos, Assistentes Técnicos do CAEx/NAT e estagiários) precisa acessar dados do CNES para subsidiar:
- Inquéritos Civis e Procedimentos Preparatórios de Saúde Pública e Patrimônio Público;
- Ações Civis Públicas (ACP) e Audiências Públicas;
- Relatórios Técnicos e Pareceres Periciais.

**O desafio de usabilidade:** A maioria dos membros da equipe não possui Python instalado nem permissões de administrador no Windows corporativo para instalar dependências e rodar comandos de terminal. Por isso, **um link web direto no navegador é a melhor solução de usabilidade**.

---

## ⚖️ Análise da sua Ideia: "Colocar no Git e Linkar no Streamlit?"

> **Sim, essa é a abordagem padrão e mais moderna do mercado para aplicações de dados em Python!**
> Ela utiliza o **GitHub (repositório)** integrado ao **Streamlit Community Cloud** (hospedagem gratuita do próprio ecossistema Streamlit/Snowflake).

### ✅ Vantagens:
1. **Zero Instalação para a Equipe:** Os colegas acessam por uma URL simples (ex: `https://mpsp-cnes-analytics.streamlit.app`).
2. **Atualizações Automáticas:** Sempre que você atualizar o código no Git, a nuvem atualiza a aplicação em segundos.
3. **Multiplataforma:** Funciona em qualquer navegador (computador do trabalho, home office, tablet ou smartphone).
4. **Gratuito e de Alto Desempenho:** Mantido pela infraestrutura global do Streamlit.

### ⚠️ O Ponto de Atenção Crítico: Persistência do Banco de Dados
No Streamlit Community Cloud:
- Os servidores rodam em **containers Linux efêmeros**.
- Se a aplicação ficar inativa ou for reiniciada, **qualquer arquivo gravado no disco local do container é apagado**!
- O seu banco SQLite atual (`data/historico_cnes.db`) possui cerca de **90 MB**. O GitHub tem limite rígido de **100 MB por arquivo** e emite alertas com arquivos maiores que 50 MB.
- Se a equipe extrair novos dados pela web, o SQLite do container descartará essas extrações no próximo reboot da máquina virtual.

---

## 🛠️ Como Resolver: As 3 Alternativas de Arquitetura

Para que a ferramenta funcione **perfeitamente tanto na Nuvem quanto Localmente, com banco persistente**, temos 3 opções principais:

```
                  ┌───────────────────────────────────────────────┐
                  │          Usuários da Equipe do MP             │
                  │   (Navegador Web via Streamlit Cloud)         │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│  Desenvolvedor / Local   │    │  Streamlit Community Cloud       │
│  (Seu Notebook/Desktop)  │    │  (Hospedado na Nuvem)            │
└────────────┬─────────────┘    └─────────────────┬────────────────┘
             │                                    │
             └─────────────────┬──────────────────┘
                               │
                               ▼
        ┌────────────────────────────────────────────────┐
        │   Banco de Dados Centralizado e Persistente    │
        │   (Supabase Postgres / Neon / Turso Serverless)│
        │                                                │
        │   • Qualquer extração feita na nuvem ou local  │
        │     fica salva para TODOS os membros da equipe!│
        └────────────────────────────────────────────────┘
```

---

### 🥇 Alternativa 1 (Recomendada): Banco Centralizado Gratuito na Nuvem (Supabase ou Neon Postgres)

**Como funciona:**
Criamos uma instância de banco de dados relacional gratuita na nuvem:
- **[Supabase](https://supabase.com)** (PostgreSQL com 500 MB gratuitos permanentes, backups automáticos e painel visual excelente);
- OU **[Neon.tech](https://neon.tech)** (PostgreSQL Serverless com 3 GB gratuitos permanentes e alta velocidade).

**Por que é a melhor opção?**
1. **Sincronização em Tempo Real:** Se um analista em Franca extrair os profissionais de um município pelo Streamlit Cloud, os dados ficam salvos no banco. Se você abrir o dashboard localmente no seu notebook, os dados já estarão lá instantaneamente!
2. **Independente da Máquina:** O banco de dados nunca é apagado quando o container do Streamlit reinicia.
3. **Respeita o Git:** O repositório Git fica limpo e leve (apenas código Python, sem o arquivo pesado `.db`).
4. **Segurança:** A senha do banco fica gravada nos **Secrets** do Streamlit Cloud (criptografada) e no seu arquivo `.env` local.
5. **Fallback Offline:** Podemos manter o código configurado para que, se não houver internet ou variável de conexão, o sistema continue usando o SQLite local (`historico_cnes.db`).

---

### 🥈 Alternativa 2: Turso LibSQL (SQLite Serverless na Nuvem)

**Como funciona:**
O **[Turso](https://turso.tech)** é uma plataforma que transforma o SQLite tradicional em um banco na nuvem distribuído.
- **Vantagens:** 9 GB de armazenamento gratuito, suporte a 500 bancos e compatibilidade quase total com a sintaxe SQL já escrita no `database.py`.
- **Desvantagens:** Exige a biblioteca `libsql-client` em vez do módulo nativo `sqlite3`.

---

### 🥉 Alternativa 3: Infraestrutura Interna do MPSP (CTI / Docker Corporativo)

**Como funciona:**
Se houver determinação da diretoria de TI (CTI/DTI) do Ministério Público para que nenhuma aplicação ou base de dados opere em nuvem pública (mesmo sendo dados 100% públicos do DATASUS):
1. Solicita-se à CTI do MP a criação de uma Máquina Virtual interna ou container Docker na rede corporativa.
2. O banco pode ser um PostgreSQL interno do MP ou um volume montado permanente em storage de rede para o SQLite.
3. O acesso da equipe ocorre via Intranet ou VPN institucional do MP.

---

## 📋 Passo a Passo Prático para Publicar (Git + Streamlit Cloud)

### Etapa 1: Preparar o Repositório Local
Já preparamos os arquivos necessários na raiz do projeto:
1. **`requirements.txt`**: Lista as dependências necessárias para o servidor da nuvem (`streamlit`, `pandas`, `openpyxl`, `rich`, `altair`).
2. **`.gitignore`**: Impede que o banco bruto pesado (`data/historico_cnes.db`), planilhas de teste (`output/`) e arquivos temporários subam para o GitHub, permitindo apenas o snapshot compactado (`data/historico_cnes.db.gz`).
3. **`.streamlit/config.toml`**: Configuração de tema e performance da aplicação.
4. **Auto-descompactação (`cnes_core/database.py`)**: Ao iniciar na nuvem sem o arquivo `.db`, o sistema descompacta automaticamente `data/historico_cnes.db.gz` para uso imediato.

### Etapa 2: Publicar e Atualizar no GitHub
1. Crie um repositório **Private** (Recomendado) no [GitHub](https://github.com/new) e publique o código via Git (`git init`, `git add .`, `git commit`, `git push -u origin main`) ou via [GitHub Desktop](https://desktop.github.com/).
2. Para atualizar o snapshot da base local na nuvem quando houver novos dados:
   ```bash
   python -c "from cnes_core.database import CNESDatabase; CNESDatabase.compress_db()"
   git add data/historico_cnes.db.gz
   git commit -m "Atualiza snapshot da base CNES"
   git push
   ```

### Etapa 3: Publicar no Streamlit Community Cloud
1. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com sua conta do GitHub.
2. Clique no botão **"New app"**.
3. Selecione:
   - **Repository:** seu repositório criado (ex: `seu-usuario/scrap-cnes`);
   - **Branch:** `main` (ou `master`);
   - **Main file path:** `app.py`.
4. *(Opcional — caso futuramente implemente gravação remota em Postgres)* Em **Advanced settings**, você poderá informar variáveis secretas como `DATABASE_URL`. Na arquitetura atual com snapshot `.db.gz`, nenhuma variável secreta é necessária.
5. Clique em **"Deploy!"**.
6. Em cerca de 2 minutos, sua aplicação estará no ar com uma URL compartilhável!

---

## 🔒 Aspectos de Segurança e Lei Geral de Proteção de Dados (LGPD)

- **Natureza dos Dados CNES:** Os dados do CNES (nomes de profissionais, especialidades, registros de conselho, cargas horárias de servidores públicos e prestadores SUS, leitos e equipes) são **dados públicos oficiais por força da Lei de Acesso à Informação (Lei nº 12.527/2011)** e da publicidade dos atos administrativos.
- **Proteção Institucional:** O repositório no GitHub deve ser configurado como **Privado**. No Streamlit Cloud, você pode restringir o acesso apenas aos e-mails institucionais (`@mpsp.mp.br`) caso não deseje que a URL seja pública na internet.
