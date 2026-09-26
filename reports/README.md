# Relatórios de qualidade

Esta pasta recebe relatórios gerados automaticamente pelo pipeline.

## Série agregada

```text
reports/quality_2026.json
```

Valida:

- colunas obrigatórias;
- preços inválidos ou não positivos;
- duplicidades;
- consistência entre preço mínimo e máximo.

## Dados por posto

```text
reports/quality_postos_2026.json
```

Valida:

- datas e cobertura de 2026;
- UF, município e produto;
- preços inválidos e não positivos;
- duplicidades pela chave de negócio;
- quantidade de UFs, municípios, produtos e postos;
- cobertura de CNPJ e bandeira.

Os relatórios são saídas reproduzíveis e não são versionados. As regras de validação permanecem em `src/quality.py` e `src/station_quality.py`.
