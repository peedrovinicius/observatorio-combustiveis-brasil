# Relatório web

O comando de snapshot gera `docs/index.html` a partir das saídas analíticas do pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -Snapshot
```

O site é estático e não depende de backend. Exibe KPIs nacionais, tendência, ranking por UF, cobertura, qualidade, dispersão municipal, comparação por bandeira e relação etanol/gasolina.

## Regras de publicação

Os valores do HTML vêm das saídas analíticas; métricas não são preenchidas manualmente. Contagens ausentes aparecem como `n/d`.

A publicação é feita por `python -m src.snapshot`. Site, relatório, imagens e bloco visual do README são montados em staging e substituídos como um único conjunto. Se a geração ou instalação falhar, o estado anterior é restaurado.

Os cinco PNGs públicos são definidos em `src/publication_contract.py`. O snapshot exige que imagens, relatório de insights, analytics e relatórios de qualidade estejam coerentes e atualizados em relação às respectivas entradas.

## Ausência ou ambiguidade de dados

Um recorte sem amostra suficiente produz uma indicação de indisponibilidade em vez de reutilizar outro produto ou fabricar uma métrica.

O ranking por UF usa gasolina comum, uma única unidade de medida e observações temporalmente comparáveis. Se o produto estiver ausente, houver mais de uma unidade ou o rótulo for ambíguo, o ranking não é publicado.

A tendência mensal mantém unidades de medida em séries separadas. Produtos em R$/L, R$/m³ ou outras unidades não compartilham o mesmo eixo de preço.

## Camada por posto

As visualizações por estabelecimento usam somente a camada por posto. A identidade do estabelecimento prioriza CNPJ normalizado e usa o fallback documentado quando o CNPJ está ausente.

A dispersão municipal considera até 12 municípios com pelo menos 3 postos. A comparação por bandeira considera até 10 grupos que atendam à amostra mínima. Os gráficos exibem o recorte temporal utilizado.

O gráfico de etanol e gasolina usa, para cada município, a semana comparável mais recente e mantém a comparação dentro da mesma unidade de medida.

## Contratos de dados

Os gráficos validam o schema mínimo dos CSVs analíticos antes da renderização. Ausência de produto, unidade, data, identidade geográfica ou métricas obrigatórias interrompe a geração com erro.

Os links de documentação no HTML usam URLs absolutas do GitHub para permanecer válidos quando `docs/index.html` é servido como página estática.
