# Testes

O projeto usa `pytest` para testes unitários e de integração.

## Execução

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

No Windows, `scripts/run_local.ps1` executa a suíte antes do pipeline.

## Cobertura

Os testes estão organizados em torno dos contratos que sustentam o pipeline:

- descoberta, download e integridade das fontes oficiais;
- normalização de schema, datas, números e unidades;
- proveniência e SHA-256 das camadas raw e processada;
- deduplicação, sobreposições e identidade de estabelecimentos;
- barreiras de qualidade para agregados e dados por posto;
- modelos estrela, chaves e integridade referencial;
- KPIs e regras de comparação entre produtos e unidades;
- contratos de carga e consultas PostgreSQL;
- geração de gráficos, site e publicação transacional do snapshot;
- rollback de saídas quando uma etapa de publicação falha;
- higiene dos notebooks e regras de estilo do repositório.

A lista de casos executados está nos arquivos `tests/test_*.py` e `tests/integration/`, que são a referência para o comportamento coberto.

## Integração offline

`tests/integration/test_offline_pipeline.py` cria fixtures temporárias e percorre os dois fluxos principais sem depender da rede:

```text
Excel agregado -> transformação -> consolidação -> qualidade -> modelo -> analytics
CSV por posto  -> ingestão -> auditoria -> qualidade -> modelo -> analytics
```

As fixtures não são publicadas nem usadas nos resultados do projeto.

## Qualidade do código e cobertura

A CI executa `ruff check .` antes dos testes. A cobertura usa branch coverage sobre `src/` e exige no mínimo 75%.

## PostgreSQL no CI

`tests/integration/test_postgres_live.py` roda contra PostgreSQL 16, aplica schemas e constraints, executa `COPY` e valida registros nas tabelas fato e na view agregada.

## Smoke das fontes da ANP

`.github/workflows/anp-smoke.yml` roda semanalmente e também pode ser acionado manualmente. Ele verifica as páginas de origem, os escopos esperados, o acesso aos recursos e as assinaturas dos formatos publicados.

O smoke fica separado da CI normal para que indisponibilidade externa da ANP não bloqueie alterações no código.
