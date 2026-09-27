# Relatório web

O snapshot local também gera `docs/index.html`, um relatório estático construído a partir dos dados processados da ANP.

A página inclui:

- KPIs nacionais por produto e unidade de medida;
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


## Publicação do relatório visual

Os cinco gráficos em `assets/generated/` e `reports/insights_2026.md` são gerados primeiro em staging.

A publicação só começa depois que os cinco PNGs esperados e o Markdown de insights existem. O diretório visual anterior e o insight anterior são mantidos em backup temporário durante a troca.

Se a instalação de qualquer parte falhar, o novo conteúdo parcial é removido e o snapshot visual anterior é restaurado. Os relatórios de qualidade presentes em `reports/` não participam da troca e não são removidos.


## Consistência do snapshot versionável

A geração com `src.snapshot` não publica `docs/index.html`, `docs/assets/`, `docs/resultados-2026.md`, `assets/snapshot/` e `README.md` de forma independente.

Todo o conjunto é montado primeiro em staging. A página HTML usa as imagens do snapshot em staging e o README também é atualizado em staging.

Somente depois da geração completa o conjunto substitui a versão anterior. Em caso de falha durante a troca, o site, as imagens, o relatório e o README anteriores são restaurados juntos.


## Seleção de combustível no ranking

O ranking por UF do site usa somente gasolina comum e exige uma única unidade de medida no recorte.

Se a saída analítica não contiver gasolina comum, o site informa `Gasolina comum indisponível` e não substitui o produto por etanol, gasolina aditivada ou qualquer outro combustível disponível no arquivo.

Se houver mais de uma unidade de medida para gasolina comum, o ranking também não combina os preços. O site informa a ambiguidade em vez de ordenar grandezas incompatíveis.

Essa regra mantém o HTML consistente com os gráficos e com a definição metodológica do ranking.
