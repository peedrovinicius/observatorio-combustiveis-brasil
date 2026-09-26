# Camada SQL

Os scripts desta pasta usam sintaxe PostgreSQL.

## Estrutura

- `schema.sql`: schema da série agregada;
- `station_schema.sql`: schema da camada por posto;
- `views.sql`: camada semântica agregada;
- `queries.sql`: consultas analíticas da série agregada;
- `station_queries.sql`: consultas analíticas da camada por posto.

A carga automatizada dos dois modelos é executada por:

```bash
python -m src.load_postgres
```

## Arquivos produzidos pelo pipeline

```text
data/processed/model/
├── dim_data.csv
├── dim_produto.csv
├── dim_localidade.csv
└── fato_precos_semanais.csv
```

O modelo agregado preserva os indicadores publicados pela ANP. A fato representa observações semanais por produto e localidade.

Na camada por posto, as consultas de última coleta determinam a data separadamente para cada `produto_posto_id`, que representa produto e unidade de medida. A comparação por bandeira segue a mesma regra de apresentação usada no Python: pelo menos 5 observações e 3 postos distintos.
