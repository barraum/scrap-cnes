# 📚 Documentação Técnica — CNES DATASUS & MP Analytics

Central de documentação técnica, manuais de módulo e guias de implantação da ferramenta de extração e análise de dados do Cadastro Nacional de Estabelecimentos de Saúde (CNES/DATASUS) desenvolvida para apoio às atividades do Ministério Público.

---

## 📑 Índice de Documentos

| Documento | Descrição | Público-Alvo |
| :--- | :--- | :--- |
| [GUIA_COMPARTILHAMENTO_NUVEM_LOCAL.md](GUIA_COMPARTILHAMENTO_NUVEM_LOCAL.md) | **Guia Estratégico de Compartilhamento & Arquitetura**: Git, Streamlit Cloud, banco de dados persistente (Nuvem + Local) e opções corporativas para a equipe do MP. | Promotores, Analistas e Desenvolvedores |
| [EQUIPES_MUNICIPIO.md](EQUIPES_MUNICIPIO.md) | Mapeamento de equipes (ESF, EAP, ESB, EMULTI), cálculo de cobertura PNAB e indicadores populacionais IBGE (Censo 2022). | Promotorias de Saúde Pública e CAEx |
| [PROFISSIONAIS_MUNICIPIO.md](PROFISSIONAIS_MUNICIPIO.md) | Extração em lote de profissionais, vínculos, CBOs e auditoria de acúmulo de cargos e sobrecarga horária (>60h/sem). | Promotorias do Patrimônio Público e Saúde |
| [CONSULTA_MUNICIPIO.md](CONSULTA_MUNICIPIO.md) | Classificação de estabelecimentos de saúde (UBS, Hospitais, Clínicas) e análise de gestão municipal/estadual. | Triagem técnica e relatórios gerais |

---

## 🏛️ Contexto e Propósito no Ministério Público

A aplicação foi projetada para sanar uma das maiores dores das Promotorias de Justiça e órgãos técnicos (como CAEx/NAT): **a morosidade e a fragmentação na obtenção de dados oficiais do DATASUS**.

### Principais Casos de Uso Institucionais:
1. **Inquéritos Civis de Saúde Pública**:
   - Auditoria de cobertura populacional da Estratégia Saúde da Família (ESF).
   - Verificação de suficiência de leitos clínicos, cirúrgicos, obstétricos e UTI.
   - Avaliação da rede física instalada de Atenção Primária e Especializada.
2. **Defesa do Patrimônio Público / Probidade Administrativa**:
   - Detecção de profissionais com múltiplos vínculos públicos ou privados incompatíveis.
   - Cruzamento de cargas horárias semanais superiores ao teto físico e legal (ex: 60h, 80h ou > 100h semanais).
3. **Estudos Técnicos e Diagnósticos Regionais**:
   - Comparativo entre municípios da mesma Região de Saúde (ex: DRS VIII - Franca/SP).
   - Apoio na formulação de TACs (Termos de Ajustamento de Conduta) com metas concretas de equipes e leitos.
