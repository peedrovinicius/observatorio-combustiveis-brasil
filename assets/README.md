# Assets

## architecture.svg

Diagrama estático da arquitetura do projeto, exibido no README principal.

## generated/

Criado por:

```bash
python -m src.reporting
```

A pasta recebe gráficos gerados exclusivamente a partir das saídas processadas do pipeline:

- `tendencia_brasil_2026.png`
- `ranking_ufs_gasolina.png`
- `etanol_gasolina_municipios.png`

O relatório textual correspondente é salvo em `reports/insights_2026.md`.

Nenhum gráfico contém valores fixados manualmente no código.
