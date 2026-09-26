# Camada SQL

Os scripts desta pasta usam sintaxe PostgreSQL.

## Ordem

1. `schema.sql`: cria dimensões, fato, restrições e índices.
2. carregar os CSVs de `data/processed/model/` para as tabelas correspondentes.
3. `views.sql`: cria a camada semântica.
4. `queries.sql`: consultas analíticas de referência.

## Arquivos produzidos pelo pipeline

```text
data/processed/model/
├── dim_data.csv
├── dim_produto.csv
├── dim_localidade.csv
└── fato_precos_semanais.csv
```

O modelo é desenhado para preservar os agregados oficiais publicados pela ANP. A fato representa observações semanais por produto e localidade.

A carga automatizada no PostgreSQL será adicionada em uma etapa posterior, após a validação do primeiro processamento completo dos arquivos oficiais.
