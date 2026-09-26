# Relatórios de qualidade

Esta pasta recebe relatórios gerados automaticamente pelo pipeline.

## Série agregada

```text
reports/quality_2026.json
```

Valida:

- colunas obrigatórias;
- datas e período;
- cobertura de 2026;
- preços inválidos ou não positivos;
- duplicidades;
- consistência entre preço mínimo e máximo.

Erros de integridade deixam o relatório com status `failed` e interrompem o pipeline.

## Auditoria de ingestão por posto

```text
reports/station_ingestion_audit_2026.json
```

Registra o que aconteceu antes da base final ser construída:

- linhas recebidas por arquivo;
- datas inválidas;
- linhas fora de 2026;
- preços inválidos;
- preços não positivos;
- linhas elegíveis;
- sobreposições entre publicações;
- grupos em que uma publicação mais recente trouxe preço diferente;
- quantidade de linhas removidas pela deduplicação;
- total final preservado.

Essa auditoria existe para impedir limpeza silenciosa. As exclusões continuam reproduzíveis e mensuráveis mesmo quando não entram no modelo analítico.

## Qualidade da base final por posto

```text
reports/quality_postos_2026.json
```

Valida:

- datas e cobertura de 2026;
- UF, município, produto e unidade;
- preços inválidos e não positivos;
- duplicidades pela chave natural;
- quantidade de UFs, municípios, produtos e postos;
- cobertura de CNPJ e bandeira.

Problemas de integridade na base final deixam o status `failed` e interrompem o pipeline.

Os relatórios são saídas reproduzíveis e não são versionados. As regras permanecem em `src/quality.py`, `src/station_data.py` e `src/station_quality.py`.
