# Power BI

## Modelo

Importar os quatro CSVs gerados em `data/processed/model/`:

- `dim_data.csv`;
- `dim_produto.csv`;
- `dim_localidade.csv`;
- `fato_precos_semanais.csv`.

Relacionamentos:

```text
dim_data[data_id]           1 ─── * fato_precos_semanais[data_id]
dim_produto[produto_id]     1 ─── * fato_precos_semanais[produto_id]
dim_localidade[localidade_id] 1 ─ * fato_precos_semanais[localidade_id]
```

Usar direção de filtro única, das dimensões para a fato.

## Página 1 — Visão Geral

Filtros:

- produto;
- período;
- nível geográfico.

Cards:

- preço da última semana;
- variação semanal;
- preço mínimo;
- preço máximo;
- postos pesquisados.

Visuais:

- linha: evolução semanal;
- barras: preço por região/UF;
- tabela: maiores e menores preços.

## Página 2 — Geografia

Filtros:

- produto;
- UF;
- município.

Visuais:

- mapa por UF/município;
- ranking de UFs;
- ranking de municípios;
- amplitude de preço;
- coeficiente de variação.

## Página 3 — Tendência

Visuais:

- linha semanal por produto;
- média das observações semanais por mês;
- variação percentual;
- mínimo e máximo do período.

A média mensal gerada pelo projeto é um indicador derivado das observações semanais e não deve ser apresentada como se fosse a série mensal oficial da ANP.

## Página 4 — Etanol × Gasolina

Usar `data/processed/analytics/etanol_gasolina_ultima_semana.csv`.

Visuais:

- relação etanol/gasolina por município;
- ranking;
- dispersão preço do etanol × preço da gasolina;
- filtros por UF.

O projeto não define automaticamente uma regra fixa de vantagem econômica. O dashboard apresenta a razão observada e deixa qualquer limiar explícito e documentado.

## Medidas

As medidas iniciais estão em [`medidas.dax`](medidas.dax).

### Regra importante

Os preços da ANP são agregados oficiais em diferentes níveis geográficos. Evite colocar registros de Brasil, região, estado e município no mesmo visual sem filtrar `nivel_geografico`, pois isso misturaria grãos analíticos diferentes.
