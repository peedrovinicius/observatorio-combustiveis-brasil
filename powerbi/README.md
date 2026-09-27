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
dim_data[data_id]              1 -> * fato_precos_semanais[data_id]
dim_produto[produto_id]        1 -> * fato_precos_semanais[produto_id]
dim_localidade[localidade_id]  1 -> * fato_precos_semanais[localidade_id]
```

Direção de filtro única, das dimensões para a fato.

## Modelo por posto

Usar:

- `dim_data_coleta`;
- `dim_produto_posto`;
- `dim_posto`;
- `fato_precos_postos`.

Relacionamentos:

```text
dim_data_coleta[data_coleta_id]       1 -> * fato_precos_postos[data_coleta_id]
dim_produto_posto[produto_posto_id]   1 -> * fato_precos_postos[produto_posto_id]
dim_posto[posto_id]                   1 -> * fato_precos_postos[posto_id]
```

Esse modelo é destinado a análises de dispersão, bandeira, estabelecimento e distribuição dos preços observados.

Não relacione diretamente as duas tabelas fato.

## Saídas Python por posto

O pipeline também gera:

```text
data/processed/analytics_postos/
├── resumo_postos_2026.csv
├── distribuicao_municipios_ultima_coleta.csv
└── bandeiras_ultima_coleta.csv
```

Essas tabelas são úteis para conferência dos resultados do Power BI e análises independentes do modelo DAX.

## Página 1: Visão Geral

Filtros:

- produto;
- unidade de medida;
- período;
- nível geográfico.

Cards:

- preço da última semana;
- variação semanal;
- preço mínimo;
- preço máximo;
- postos pesquisados na última semana.

Visuais:

- linha: evolução semanal;
- barras: preço por região/UF;
- tabela: maiores e menores preços.

## Página 2: Geografia

Filtros:

- produto;
- unidade de medida;
- UF;
- município.

Visuais:

- mapa por UF/município;
- ranking de UFs;
- ranking de municípios;
- amplitude de preço;
- coeficiente de variação.

## Página 3: Tendência

Visuais:

- linha semanal por produto;
- média das observações semanais por mês;
- variação percentual;
- mínimo e máximo do período.

A média mensal gerada pelo projeto é um indicador derivado das observações semanais e não deve ser apresentada como se fosse a série mensal oficial da ANP.

## Página 4: Mercado por Posto

Cards:

- preço médio observado;
- mediana observada;
- postos distintos;
- observações de preço;
- amplitude observada.

Visuais:

- distribuição dos preços;
- comparação por bandeira;
- quantidade de revendas pesquisadas;
- menores e maiores preços observados;
- dispersão por município;
- intervalo interquartil;
- coeficiente de variação.

A data mais recente deve ser avaliada por combinação de produto e unidade de medida. Uma única data máxima global pode excluir séries cuja coleta mais recente ocorreu em outro dia.

## Página 5: Etanol × Gasolina

Usar `data/processed/analytics/etanol_gasolina_ultima_semana.csv` ou reproduzir a medida no modelo.

Visuais:

- relação etanol/gasolina por município;
- ranking;
- dispersão preço do etanol × preço da gasolina;
- filtros por UF.

O projeto não define automaticamente uma regra fixa de vantagem econômica. O dashboard apresenta a razão observada e deixa qualquer limiar explícito e documentado.

## Medidas

As medidas estão em [`medidas.dax`](medidas.dax).

As medidas de preço exigem uma única série no contexto do visual. No modelo agregado, isso significa um único produto e uma única unidade de medida. No modelo por posto, a série é identificada por `produto_posto_id`, que já representa produto + unidade. Se o contexto misturar unidades, as medidas retornam vazio em vez de produzir uma média entre grandezas incompatíveis.

Para cards de cobertura agregada, use `Postos Pesquisados Última Semana` quando a intenção for mostrar a cobertura da observação corrente. A medida simples `Postos Pesquisados` continua disponível para tabelas ou contextos em que a soma faça sentido.

## Regra importante

Os preços agregados oficiais e as observações por posto têm grãos e significados diferentes. Mantenha cada tabela fato no seu próprio contexto analítico e não compare medidas como se fossem equivalentes.
