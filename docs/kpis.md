# KPIs e indicadores

## Camada agregada oficial

Os exports analíticos agregados só são gerados quando a série consolidada passa pela validação de qualidade. A execução direta de `python -m src.analytics` repete essa validação antes de escrever arquivos em `data/processed/analytics/`.

### Preço atual

Último preço médio de revenda publicado para a combinação de produto e nível geográfico selecionada.

### Variação semanal

```text
(preço atual / preço da semana anterior - 1) × 100
```

É calculada somente quando há uma observação anterior válida.

### Variação desde o início de 2026

```text
(preço atual / primeira observação de 2026 - 1) × 100
```

Não representa inflação. É apenas a variação do preço médio observado no período.

### Menor e maior preço em 2026

Menor e maior valor de `preco_medio_revenda` observado na série semanal do recorte analisado.

Para análises de dispersão dentro de uma semana devem ser utilizados os campos de preço mínimo e máximo publicados pela ANP, quando disponíveis.

### Média das semanas no mês

Média aritmética das observações semanais oficiais contidas no mês.

É um **indicador derivado pelo projeto** e não substitui a série mensal oficial da ANP.

### Ranking por UF e município

Os rankings utilizam o preço médio publicado na semana mais recente disponível para cada produto. A data não é escolhida globalmente entre todos os combustíveis.

Assim, um produto continua aparecendo no ranking mesmo quando outro possui uma publicação mais recente.

São produzidas duas posições:

- `ranking_mais_caro`: ordem decrescente;
- `ranking_mais_barato`: ordem crescente.

Empates recebem a mesma posição mínima.

### Relação etanol/gasolina

```text
(preço médio do etanol / preço médio da gasolina comum) × 100
```

A comparação usa gasolina comum, excluindo gasolina aditivada.

Para cada município, o cálculo usa a semana mais recente em que etanol e gasolina comum possuem observação simultaneamente. Isso evita dividir preços provenientes de semanas diferentes.

O projeto reporta a razão observada. Qualquer limiar usado para interpretar vantagem econômica deve ser explicitado como hipótese adicional.

### Postos pesquisados

Quantidade de estabelecimentos pesquisados informada pela fonte para aquele recorte, quando disponível.

Não deve ser somada indiscriminadamente entre diferentes níveis geográficos ou semanas.

## Camada por posto

Os indicadores desta seção são calculados diretamente sobre observações de preço por estabelecimento. Eles não substituem os agregados oficiais publicados pela ANP.

### Preço médio observado

Média aritmética das observações individuais de preço no recorte selecionado.

### Mediana observada

Valor central da distribuição dos preços observados. É especialmente útil para reduzir a influência visual de valores extremos.

### Quartis e intervalo interquartil

```text
IQR = Q3 - Q1
```

O intervalo interquartil resume a dispersão dos 50% centrais da distribuição.

### Desvio padrão

Calculado sobre as observações individuais de preço no recorte.

### Coeficiente de variação

```text
(desvio padrão / preço médio observado) × 100
```

Permite comparar dispersão relativa entre municípios ou produtos.

### Postos distintos

Quantidade de estabelecimentos distintos no recorte, usando CNPJ quando disponível e identidade de fallback quando necessário.

### Cobertura

O resumo anual por produto registra:

- período inicial e final;
- observações;
- postos distintos;
- municípios;
- UFs;
- média;
- mediana;
- mínimo;
- máximo.

### Comparação por bandeira

A comparação por bandeira informa quantidade de observações e de postos. O campo `amostra_suficiente` sinaliza grupos com pelo menos 5 observações e 3 postos distintos.

A sinalização é uma regra de apresentação do projeto, não uma definição estatística universal.

### Última coleta

Na camada por posto, a data mais recente é determinada separadamente para cada combinação de produto e unidade de medida. Isso evita excluir um produto apenas porque outro possui observação em data posterior.

Essa regra é aplicada de forma consistente nos exports Python, nas medidas DAX e nas consultas de referência em `sql/station_queries.sql`.


## Barreira de qualidade para analytics por posto

A geração dos exports de `analytics_postos/` exige que a base consolidada por estabelecimento seja aprovada pela mesma validação usada antes da modelagem.

A execução direta de `python -m src.station_analytics` recalcula essa validação e encerra sem gerar métricas quando a base contém inconsistências bloqueantes.
