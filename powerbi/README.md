# Power BI

## Opção recomendada: PostgreSQL

Depois de executar:

```bash
docker compose up -d postgres
python -m src.pipeline
python -m src.load_postgres
```

conecte o Power BI Desktop ao PostgreSQL local:

```text
Servidor: localhost:5432
Banco: combustiveis
```

As credenciais de desenvolvimento estão em `.env.example` e podem ser alteradas localmente.

## Modelo agregado

Usar:

- `dim_data`;
- `dim_produto`;
- `dim_localidade`;
- `fato_precos_semanais`.

Relacionamentos:

```text
dim_data[data_id]              1 ─── * fato_precos_semanais[data_id]
dim_produto[produto_id]        1 ─── * fato_precos_semanais[produto_id]
dim_localidade[localidade_id]  1 ─── * fato_precos_semanais[localidade_id]
```

Direção de filtro única, das dimensões para a fato.

## Modelo por posto

Usar:

- `dim_data_coleta`;
- `dim_produto_posto`;
- `dim_posto`;
- `fato_precos_postos`.

Esse modelo é destinado a análises de dispersão, bandeira, estabelecimento e distribuição dos preços observados.

Não relacione diretamente as duas tabelas fato.

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

## Página 4 — Mercado por posto

Visuais:

- distribuição dos preços;
- mediana;
- comparação por bandeira;
- quantidade de revendas pesquisadas;
- menores e maiores preços observados;
- dispersão por município.

## Página 5 — Etanol × Gasolina

Usar `data/processed/analytics/etanol_gasolina_ultima_semana.csv` ou reproduzir a medida no modelo.

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
