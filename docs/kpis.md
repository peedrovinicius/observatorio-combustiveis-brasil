# KPIs e indicadores

## Preço atual

Último preço médio de revenda publicado para a combinação de produto e nível geográfico selecionada.

## Variação semanal

```text
(preço atual / preço da semana anterior - 1) × 100
```

É calculada somente quando há uma observação anterior válida.

## Variação desde o início de 2026

```text
(preço atual / primeira observação de 2026 - 1) × 100
```

Não representa inflação. É apenas a variação do preço médio observado no período.

## Menor e maior preço em 2026

Menor e maior valor de `preco_medio_revenda` observado na série semanal do recorte analisado.

Para análises de dispersão dentro de uma semana devem ser utilizados os campos de preço mínimo e máximo publicados pela ANP, quando disponíveis.

## Média das semanas no mês

Média aritmética das observações semanais oficiais contidas no mês.

É um **indicador derivado pelo projeto** e não substitui a série mensal oficial da ANP.

## Ranking por UF e município

Os rankings utilizam o preço médio publicado na semana mais recente disponível para cada produto.

São produzidas duas posições:

- `ranking_mais_caro`: ordem decrescente;
- `ranking_mais_barato`: ordem crescente.

Empates recebem a mesma posição mínima.

## Relação etanol/gasolina

```text
(preço médio do etanol / preço médio da gasolina comum) × 100
```

A comparação usa gasolina comum, excluindo gasolina aditivada.

O projeto reporta a razão observada. Qualquer limiar usado para interpretar vantagem econômica deve ser explicitado como uma hipótese adicional, não como propriedade do dado bruto.

## Postos pesquisados

Quantidade de estabelecimentos pesquisados informada pela fonte para aquele recorte, quando disponível.

Não deve ser somada indiscriminadamente entre diferentes níveis geográficos ou semanas.
