<div align="center">

# Observatório de Combustíveis Brasil

**Pipeline analítico de preços de combustíveis no Brasil com dados públicos oficiais da ANP**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-Modelagem%20Dimensional-336791)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811?logo=powerbi&logoColor=black)
![Data](https://img.shields.io/badge/Dados-ANP.gov.br-0B6E4F)

</div>

## Visão geral

O projeto analisa a evolução e a distribuição dos preços de combustíveis no Brasil a partir de dados públicos da Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP).

O objetivo é construir um fluxo analítico reproduzível, cobrindo aquisição, rastreabilidade, tratamento, validação, modelagem, análise exploratória, SQL e visualização em Power BI.

## Pergunta analítica

**Como os preços dos combustíveis variam ao longo do tempo e entre regiões, estados, municípios, produtos e postos revendedores?**

## Arquitetura

```mermaid
flowchart LR
    A[ANP<br/>Dados públicos] --> B[Extração<br/>Python]
    B --> C[Raw<br/>Arquivos originais]
    C --> D[Validação<br/>Qualidade e schema]
    D --> E[Transformação<br/>Pandas]
    E --> F[Modelo dimensional<br/>SQL]
    F --> G[Análise<br/>Python e SQL]
    G --> H[Power BI<br/>Dashboard]
```

## Escopo analítico

- evolução semanal, mensal e anual dos preços;
- preço médio, mediano, mínimo e máximo;
- amplitude, desvio padrão e coeficiente de variação;
- comparação entre Brasil, regiões, UFs e municípios;
- comparação entre produtos;
- distribuição de preços por posto e bandeira, quando disponível;
- diferença de cada localidade em relação à média nacional;
- análise da relação entre preços de etanol e gasolina;
- identificação e documentação de valores extremos;
- acompanhamento da cobertura da pesquisa ao longo do tempo.

## Fontes oficiais

A base principal é o Levantamento de Preços de Combustíveis da ANP. O projeto também está preparado para incorporar a série histórica e dados cadastrais dos revendedores.

As URLs oficiais e as regras de rastreabilidade estão documentadas em [`docs/fontes.md`](docs/fontes.md).

## Estrutura

```text
observatorio-combustiveis-brasil/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── fontes.md
│   └── metodologia.md
├── notebooks/
├── sql/
│   └── schema.sql
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── download_anp.py
│   └── inspect_raw.py
├── tests/
├── .gitignore
├── requirements.txt
└── README.md
```

## Primeira execução

```bash
python -m venv .venv
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.download_anp
python -m src.inspect_raw
```

O download grava os arquivos originais em `data/raw/` e cria `manifest.json` com URL de origem, data da coleta, tamanho e SHA-256. Os arquivos de dados não são versionados no Git para evitar crescimento desnecessário do repositório.

## Modelo dimensional planejado

```mermaid
erDiagram
    FATO_PRECOS }o--|| DIM_DATA : data_id
    FATO_PRECOS }o--|| DIM_PRODUTO : produto_id
    FATO_PRECOS }o--|| DIM_LOCALIDADE : localidade_id
    FATO_PRECOS }o--o| DIM_POSTO : posto_id
    FATO_PRECOS }o--o| DIM_BANDEIRA : bandeira_id
```

## Princípios do projeto

- dados reais e públicos;
- nenhuma alteração nos arquivos brutos;
- rastreabilidade da origem de cada arquivo;
- transformações reproduzíveis em código;
- validações antes da análise;
- métricas documentadas;
- separação entre dado bruto, dado tratado e camada analítica;
- conclusões baseadas somente nos dados efetivamente processados.

## Status

**Fase 1: aquisição e inspeção dos dados.**

A próxima etapa é consolidar a série histórica, padronizar o schema e gerar a primeira base analítica tratada.

## Licença

O código deste repositório é disponibilizado sob licença MIT. Os dados permanecem sujeitos aos termos e à origem de publicação da ANP.
