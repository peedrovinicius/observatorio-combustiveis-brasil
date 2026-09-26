# Relatório web

O snapshot local também gera `docs/index.html`, um relatório estático construído a partir dos dados processados da ANP.

A página inclui:

- KPIs nacionais por produto;
- tendência de preços;
- ranking por UF;
- cobertura e qualidade;
- gráficos de UF e etanol/gasolina;
- links para metodologia e resultados completos.

## Geração

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -Snapshot
```

O site é totalmente estático e não depende de backend.

Os valores exibidos são lidos das saídas analíticas do pipeline. Não existem métricas fictícias ou preenchidas manualmente no HTML.

A pasta `docs/` fica pronta para ser usada como origem de uma publicação estática do repositório, após revisão dos resultados gerados.
