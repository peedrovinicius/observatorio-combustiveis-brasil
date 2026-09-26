-- PostgreSQL
-- Consultas analíticas de referência.

-- 1. Evolução semanal oficial no nível Brasil.
SELECT
    data_inicial,
    data_final,
    produto,
    preco_medio_revenda
FROM vw_precos_semanais
WHERE nivel_geografico = 'brasil'
ORDER BY produto, data_inicial;


-- 2. Preço médio por UF na semana mais recente para gasolina.
SELECT
    uf,
    preco_medio_revenda,
    postos_pesquisados
FROM vw_ultimo_periodo
WHERE nivel_geografico = 'estado'
  AND produto ILIKE 'GASOLINA%'
ORDER BY preco_medio_revenda DESC;


-- 3. Municípios com maiores preços na semana mais recente.
SELECT
    uf,
    municipio,
    preco_medio_revenda,
    postos_pesquisados
FROM vw_ultimo_periodo
WHERE nivel_geografico = 'municipio'
  AND produto ILIKE 'GASOLINA%'
ORDER BY preco_medio_revenda DESC
LIMIT 20;


-- 4. Média mensal das observações semanais no nível Brasil.
-- Este indicador é derivado pelo projeto e não substitui a série mensal oficial da ANP.
WITH mensal AS (
    SELECT
        ano,
        mes,
        produto,
        AVG(preco_medio_revenda) AS media_semanal_no_mes
    FROM vw_precos_semanais
    WHERE nivel_geografico = 'brasil'
    GROUP BY ano, mes, produto
)
SELECT
    ano,
    mes,
    produto,
    media_semanal_no_mes,
    ROUND(
        100.0
        * (
            media_semanal_no_mes
            - LAG(media_semanal_no_mes)
                OVER (PARTITION BY produto ORDER BY ano, mes)
        )
        / NULLIF(
            LAG(media_semanal_no_mes)
                OVER (PARTITION BY produto ORDER BY ano, mes),
            0
        ),
        2
    ) AS variacao_percentual_mes
FROM mensal
ORDER BY produto, ano, mes;


-- 5. Localidades com maior dispersão relativa de preços.
SELECT
    data_inicial,
    uf,
    municipio,
    produto,
    coef_variacao_revenda,
    preco_medio_revenda
FROM vw_precos_semanais
WHERE nivel_geografico = 'municipio'
  AND coef_variacao_revenda IS NOT NULL
ORDER BY coef_variacao_revenda DESC
LIMIT 30;


-- 6. Relação etanol/gasolina por município na semana mais recente.
WITH precos AS (
    SELECT
        uf,
        municipio,
        MAX(preco_medio_revenda)
            FILTER (WHERE produto ILIKE 'ETANOL%') AS etanol,
        MAX(preco_medio_revenda)
            FILTER (WHERE produto ILIKE 'GASOLINA%') AS gasolina
    FROM vw_ultimo_periodo
    WHERE nivel_geografico = 'municipio'
    GROUP BY uf, municipio
)
SELECT
    uf,
    municipio,
    etanol,
    gasolina,
    ROUND(100.0 * etanol / NULLIF(gasolina, 0), 2)
        AS relacao_etanol_gasolina_percentual
FROM precos
WHERE etanol IS NOT NULL
  AND gasolina IS NOT NULL
ORDER BY relacao_etanol_gasolina_percentual;
