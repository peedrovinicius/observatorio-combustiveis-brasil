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

Contagens ausentes são exibidas como `n/d`, nunca como representações internas de valores nulos como `NaN` ou `<NA>`.

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

O período da série também é exibido junto ao ranking. Se uma mesma combinação de produto e unidade chegar com múltiplas datas, o ranking não é exibido, pois essas linhas não seriam temporalmente comparáveis.

Se a saída analítica não contiver gasolina comum, o site informa `Gasolina comum indisponível` e não substitui o produto por etanol, gasolina aditivada ou qualquer outro combustível disponível no arquivo.

Se houver mais de uma unidade de medida para gasolina comum, o ranking também não combina os preços. O site informa a ambiguidade em vez de ordenar grandezas incompatíveis.

Da mesma forma, se mais de um rótulo de produto for reconhecido simultaneamente como gasolina comum no mesmo recorte, o site não escolhe um alias pela ordem dos dados. O ranking é tratado como indisponível até que a série esteja inequivocamente identificada.

Essa regra mantém o HTML consistente com os gráficos e com a definição metodológica do ranking.


## Cobertura por estabelecimento

A cobertura de postos usa a identidade completa do projeto: CNPJ normalizado quando disponível e fallback confiável por UF, município, revenda, logradouro e número quando o CNPJ está ausente. O indicador público `Postos distintos` não se limita, portanto, aos estabelecimentos com CNPJ preenchido.

Municípios são contados pela combinação UF + município, evitando fundir localidades homônimas de estados diferentes.


## Contrato visual do README

A mesma lista de cinco imagens é compartilhada entre a geração do snapshot e a publicação do bloco visual do README. A atualização do README exige que o relatório de resultados e todos os PNGs existam e tenham conteúdo, evitando referências para um snapshot incompleto.


## Coerência do estado versionado

O repositório também testa que a publicação versionada é tudo ou nada. Se qualquer parte do snapshot público estiver presente, o conjunto completo deve existir: relatório de resultados, HTML, assets do site, cinco imagens do snapshot e bloco de resultados no README. Quando nenhum snapshot foi revisado e versionado, os marcadores do README permanecem vazios.


## Recorte explícito nos gráficos

Os gráficos por posto exibem a data da coleta da série selecionada. Se o arquivo analítico trouxer múltiplas datas para o mesmo produto e unidade em um gráfico que exige comparação simultânea, a visualização é substituída por uma mensagem de indisponibilidade.

A dispersão municipal mostra até 12 municípios com maior intervalo interquartil entre os que possuem pelo menos 3 postos. A comparação por bandeira mostra até 10 grupos de maior cobertura entre os que atingem a regra de amostra mínima. Esses critérios aparecem no próprio gráfico e nas legendas do site.

O gráfico de etanol e gasolina é diferente: cada município usa sua semana comparável mais recente, podendo haver datas distintas entre municípios. A comparação continua restrita à mesma unidade de medida.


## Unidades na tendência mensal

A tendência mensal separa as séries por unidade de medida dentro do mesmo PNG. Produtos medidos em R$/L, R$/m³ ou outra unidade não compartilham o mesmo eixo de preço. Isso evita comparar visualmente grandezas incompatíveis.


## Contrato dos gráficos por posto

Os gráficos por posto validam explicitamente o contrato mínimo dos CSVs analíticos antes de desenhar a figura. Produto, unidade, data de coleta, identidade geográfica e métricas necessárias não podem desaparecer silenciosamente. Uma regressão de schema interrompe a geração com erro descritivo em vez de produzir um gráfico incompleto ou falhar com uma exceção genérica de coluna.


## Contrato único de imagens públicas

A lista dos cinco PNGs públicos fica centralizada em `src/publication_contract.py`. Reporting, snapshot, site e publicação do README consomem o mesmo contrato, evitando divergência de nomes ou quantidade de arquivos entre as etapas.


## Entrada única de publicação pública

A publicação direta por `python -m src.site` e `python -m src.publish_readme` é bloqueada para evitar estados parciais. O único comando de publicação pública é `python -m src.snapshot`, que monta e substitui site, relatório, imagens e README como um único bundle.


## Frescor do bundle visual

O snapshot também verifica o frescor do bundle visual antes de publicar. Os cinco PNGs e `reports/insights_2026.md` precisam ser tão recentes quanto os CSVs analíticos e relatórios de qualidade usados como entrada. Se analytics ou qualidade forem regenerados depois dos gráficos, `python -m src.snapshot` é bloqueado até que `python -m src.reporting` seja executado novamente.
