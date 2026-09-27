-- PostgreSQL
-- Consultas analíticas de referência.

-- 1. Evolução semanal oficial no nível Brasil.
SELECT
    data_inicial,
    data_final,
    produto,
    unidade_medida,
    preco_medio_revenda
FROM vw_precos_semanais
WHERE nivel_geografico = 'brasil'
ORDER BY produto, unidade_medida, data_inicial;


-- 2. Preço médio por UF na última semana disponível de cada produto e unidade.
SELECT
    data_inicial,
    uf,
    produto,
    unidade_medida,
    preco_medio_revenda,
    postos_pesquisados
FROM vw_ultimo_periodo
WHERE nivel_geografico = 'estado'
  AND produto ILIKE 'GASOLINA%'
ORDER BY
    produto,
    unidade_medida,
    preco_medio_revenda DESC;


-- 3. Municípios com maiores preços na última semana de cada produto e unidade.
WITH municipios_ordenados AS (
    SELECT
        data_inicial,
        uf,
        municipio,
        produto,
        unidade_medida,
        preco_medio_revenda,
        postos_pesquisados,
        ROW_NUMBER() OVER (
            PARTITION BY
                produto,
                unidade_medida
            ORDER BY
                preco_medio_revenda DESC,
                uf,
                municipio
        ) AS ordem
    FROM vw_ultimo_periodo
    WHERE nivel_geografico = 'municipio'
      AND produto ILIKE 'GASOLINA%'
)
SELECT
    data_inicial,
    uf,
    municipio,
    produto,
    unidade_medida,
    preco_medio_revenda,
    postos_pesquisados
FROM municipios_ordenados
WHERE ordem <= 20
ORDER BY
    produto,
    unidade_medida,
    ordem;


-- 4. Média mensal das observações semanais no nível Brasil.
-- Indicador derivado pelo projeto, não substitui a série mensal oficial da ANP.
WITH mensal AS (
    SELECT
        ano,
        mes,
        produto,
        unidade_medida,
        AVG(preco_medio_revenda) AS media_semanal_no_mes
    FROM vw_precos_semanais
    WHERE nivel_geografico = 'brasil'
    GROUP BY
        ano,
        mes,
        produto,
        unidade_medida
)
SELECT
    ano,
    mes,
    produto,
    unidade_medida,
    media_semanal_no_mes,
    ROUND(
        100.0
        * (
            media_semanal_no_mes
            - LAG(media_semanal_no_mes)
                OVER (
                    PARTITION BY produto, unidade_medida
                    ORDER BY ano, mes
                )
        )
        / NULLIF(
            LAG(media_semanal_no_mes)
                OVER (
                    PARTITION BY produto, unidade_medida
                    ORDER BY ano, mes
                ),
            0
        ),
        2
    ) AS variacao_percentual_mes
FROM mensal
ORDER BY
    produto,
    unidade_medida,
    ano,
    mes;


-- 5. Localidades com maior dispersão relativa de preços.
SELECT
    data_inicial,
    uf,
    municipio,
    produto,
    unidade_medida,
    coef_variacao_revenda,
    preco_medio_revenda
FROM vw_precos_semanais
WHERE nivel_geografico = 'municipio'
  AND coef_variacao_revenda IS NOT NULL
ORDER BY
    coef_variacao_revenda DESC
LIMIT 30;


-- 6. Relação etanol/gasolina na última semana comparável por município.
WITH comparaveis AS (
    SELECT
        data_inicial,
        uf,
        municipio,
        unidade_medida,
        MAX(preco_medio_revenda)
            FILTER (
                WHERE produto ILIKE '%ETANOL%'
                  AND produto ILIKE '%HIDRAT%'
            ) AS etanol,
        COUNT(*)
            FILTER (
                WHERE produto ILIKE '%ETANOL%'
                  AND produto ILIKE '%HIDRAT%'
            ) AS etanol_observacoes,
        MAX(preco_medio_revenda)
            FILTER (
                WHERE produto ILIKE '%GASOLINA%'
                  AND produto ILIKE '%COMUM%'
                  AND produto NOT ILIKE '%ADITIV%'
            ) AS gasolina,
        COUNT(*)
            FILTER (
                WHERE produto ILIKE '%GASOLINA%'
                  AND produto ILIKE '%COMUM%'
                  AND produto NOT ILIKE '%ADITIV%'
            ) AS gasolina_observacoes
    FROM vw_precos_semanais
    WHERE nivel_geografico = 'municipio'
    GROUP BY
        data_inicial,
        uf,
        municipio,
        unidade_medida
),
validos AS (
    SELECT
        data_inicial,
        uf,
        municipio,
        unidade_medida,
        etanol,
        etanol_observacoes,
        gasolina,
        gasolina_observacoes
    FROM comparaveis
    WHERE etanol IS NOT NULL
      AND gasolina IS NOT NULL
      AND etanol_observacoes = 1
      AND gasolina_observacoes = 1
),
ultima_comparavel AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY uf, municipio, unidade_medida
            ORDER BY data_inicial DESC
        ) AS ordem
    FROM validos
)
SELECT
    data_inicial,
    uf,
    municipio,
    unidade_medida,
    etanol,
    gasolina,
    ROUND(
        100.0
        * etanol
        / NULLIF(
            gasolina,
            0
        ),
        2
    ) AS relacao_etanol_gasolina_percentual
FROM ultima_comparavel
WHERE ordem = 1
ORDER BY
    data_inicial DESC,
    relacao_etanol_gasolina_percentual;
