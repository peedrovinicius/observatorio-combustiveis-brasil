# Testes

O projeto usa `pytest` para validar regras unitárias e um fluxo de integração offline.

## Execução

```bash
python -m pytest
```

O runner local executa a mesma suíte antes do pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

## Cobertura lógica

A suíte verifica, entre outros pontos:

- descoberta das fontes oficiais;
- reconhecimento de CSV, ZIP e XLSX pelo conteúdo;
- normalização de schema;
- datas e decimais;
- consolidação de 2026;
- qualidade agregada;
- identidade e deduplicação de postos;
- precedência entre publicações sobrepostas;
- auditoria de exclusões;
- modelo estrela agregado;
- modelo estrela por posto;
- KPIs agregados;
- análises por estabelecimento;
- contrato dos CSVs com PostgreSQL;
- geração de gráficos;
- publicação de snapshot e README;
- construção do relatório web.

## Integração offline

`tests/integration/test_offline_pipeline.py` cria arquivos temporários sintéticos apenas durante o teste.

O teste percorre:

```text
Excel agregado
  -> transformação
  -> consolidação
  -> qualidade
  -> modelo estrela
  -> analytics

CSV no schema por posto
  -> ingestão
  -> auditoria
  -> qualidade
  -> modelo estrela
  -> analytics por posto

saídas analíticas
  -> cinco gráficos
  -> relatório de insights
```

As fixtures não entram em `data/`, não são publicadas e não são usadas nos resultados do projeto. O objetivo é validar a integração entre componentes sem depender da rede ou da disponibilidade momentânea do portal da ANP.
