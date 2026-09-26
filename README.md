<div align="center">

# Observatório de Combustíveis Brasil

**Pipeline de Data Analytics para preços de combustíveis com dados públicos oficiais da ANP**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-Modelagem%20Dimensional-336791)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811?logo=powerbi&logoColor=black)
![Data](https://img.shields.io/badge/Dados-ANP.gov.br-0B6E4F)

</div>

## Visão geral

O projeto analisa a evolução e a distribuição dos preços de combustíveis no Brasil a partir de dados públicos da Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP).

A proposta é construir um fluxo analítico reproduzível de ponta a ponta: aquisição, rastreabilidade, inspeção, tratamento, validação, consolidação, SQL e visualização em Power BI.

## Pergunta analítica

**Como os preços dos combustíveis variam em 2026 ao longo do tempo e entre Brasil, regiões, estados, municípios e produtos?**

## Pipeline

```mermaid
flowchart LR
    A[ANP<br/>Série histórica] --> B[Download<br/>Python]
    B --> C[Raw<br/>Arquivos originais]
    C --> D[Inspeção<br/>Schema]
    D --> E[Transformação<br/>Pandas]
    E --> F[Consolidação<br/>2026]
    F --> G[Qualidade<br/>Data checks]
    G --> H[SQL<br/>Modelo analítico]
    H --> I[Power BI<br/>Dashboard]
```

## O que já está implementado

- descoberta automática dos arquivos semanais oficiais;
- coleta separada para Brasil, regiões, estados e municípios de 2026;
- manifesto de origem com URL, horário, tamanho e SHA-256;
- inspeção dos arquivos brutos;
- detecção automática de cabeçalho nas planilhas;
- normalização de nomes, datas e valores monetários;
- suporte a vírgula decimal brasileira e ponto decimal;
- consolidação exclusiva da série de 2026;
- identificação automática do nível geográfico;
- remoção de duplicidades por chave analítica;
- criação de ano, mês e semana ISO;
- validações de qualidade antes da análise;
- testes automatizados para as regras centrais.

## Estrutura

```text
observatorio-combustiveis-brasil/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── dicionario-dados.md
│   ├── fontes.md
│   └── metodologia.md
├── notebooks/
├── reports/
├── sql/
│   └── schema.sql
├── src/
│   ├── config.py
│   ├── consolidate.py
│   ├── download_anp.py
│   ├── download_history.py
│   ├── inspect_raw.py
│   ├── pipeline.py
│   ├── quality.py
│   └── transform.py
├── tests/
├── .gitignore
├── requirements.txt
└── README.md
```

## Execução completa

Crie o ambiente e instale as dependências:

```bash
python -m venv .venv
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.pipeline
```

O comando executa:

```text
1. download da série histórica
2. inspeção dos arquivos brutos
3. transformação e padronização
4. consolidação da série 2026
5. validação de qualidade
```

Para executar os testes:

```bash
pytest
```

## Saída analítica

O pipeline gera localmente:

```text
data/processed/precos_semanais_2026.csv
reports/quality_2026.json
```

Os datasets não são versionados no Git. Eles são reconstruíveis a partir do código e das fontes oficiais, mantendo o repositório leve.

## Escopo analítico

A tabela consolidada será usada para calcular e visualizar:

- evolução semanal e mensal;
- preço médio, mínimo e máximo;
- amplitude e dispersão;
- comparação entre produtos;
- comparação Brasil × região × estado × município;
- diferença de cada localidade em relação aos agregados oficiais;
- quantidade de postos pesquisados quando disponível;
- rankings e variações percentuais;
- análise etanol × gasolina.

## Metodologia

O projeto não recalcula o indicador nacional como uma média simples das médias municipais. Os agregados oficiais da ANP são preservados porque os níveis estadual, regional e nacional possuem metodologia de agregação própria.

Detalhes estão em [`docs/metodologia.md`](docs/metodologia.md).

## Princípios

- somente dados públicos reais;
- arquivo bruto imutável;
- origem rastreável;
- transformação reproduzível;
- validação antes da visualização;
- nenhuma métrica digitada manualmente;
- nenhuma remoção automática de outliers;
- separação clara entre raw, processed e camada analítica.

## Status

**Pipeline de aquisição, transformação, consolidação e qualidade de 2026 implementado.**

Próxima etapa: criar a camada SQL analítica e os primeiros indicadores derivados para o dashboard.

## Licença

O código deste repositório é disponibilizado sob licença MIT. Os dados permanecem sujeitos aos termos e à origem de publicação da ANP.
