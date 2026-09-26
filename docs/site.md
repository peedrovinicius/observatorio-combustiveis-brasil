# Relatório web

O snapshot local também gera `docs/index.html`, um relatório estático construído a partir dos dados processados da ANP.

A página inclui:

- KPIs nacionais por produto;
- tendência de preços;
- ranking por UF;
- cobertura e qualidade;
- gráficos de UF e etanol/gasolina;
- placeholders informativos quando um recorte não possui dados suficientes para determinada visualização;
- dispersão municipal dos preços observados por posto;
- comparação de mediana por bandeira com proteção contra amostra pequena;
- links para metodologia e resultados completos.

## Geração

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -Snapshot
```

O site é totalmente estático e não depende de backend.

Os valores exibidos são lidos das saídas analíticas do pipeline. Não existem métricas fictícias ou preenchidas manualmente no HTML.

As visualizações por estabelecimento usam somente a camada por posto e não são apresentadas como equivalentes aos agregados oficiais da ANP.

A pasta `docs/` fica pronta para ser usada como origem de uma publicação estática do repositório, após revisão dos resultados gerados.

Os links de documentação exibidos no HTML apontam para URLs absolutas do GitHub. Dessa forma, continuam válidos quando `docs/index.html` é servido pelo GitHub Pages e não dependem de caminhos relativos fora da pasta publicada.


## Ausência de dados

A ausência de dados em um recorte não faz o relatório visual falhar e não autoriza a substituição por outro produto.

Quando tendência mensal, gasolina comum, relação etanol/gasolina ou uma análise por posto não possui amostra utilizável, o pipeline gera uma imagem informativa indicando a indisponibilidade daquele recorte.

Isso mantém o conjunto de cinco arquivos visuais estável para snapshot e site sem fabricar métricas ou trocar silenciosamente o produto analisado.
