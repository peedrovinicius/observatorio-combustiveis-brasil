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
    estado,
    produto,
    unidade_medida,
    postos_pesquisados,
    preco_medio_revenda,
    preco_minimo_revenda,
    preco_maximo_revenda,
    RANK() OVER (
        PARTITION BY
            produto,
            unidade_medida
        ORDER BY
            preco_medio_revenda DESC
    ) AS ranking_mais_caro,
    RANK() OVER (
        PARTITION BY
            produto,
            unidade_medida
        ORDER BY
            preco_medio_revenda ASC
    ) AS ranking_mais_barato
FROM vw_ultimo_periodo
WHERE nivel_geografico = 'estado'
ORDER BY
    produto,
    unidade_medida,
    ranking_mais_caro,
    uf;


-- 3. Municípios com maiores preços na última semana de cada produto e unidade.
WITH municipios_ranqueados AS (
    SELECT
        data_inicial,
        uf,
        municipio,
        produto,
        unidade_medida,
        postos_pesquisados,
        preco_medio_revenda,
        preco_minimo_revenda,
        preco_maximo_revenda,
        RANK() OVER (
            PARTITION BY
                produto,
                unidade_medida
            ORDER BY
                preco_medio_revenda DESC
        ) AS ranking_mais_caro,
        RANK() OVER (
            PARTITION BY
                produto,
                unidade_medida
            ORDER BY
                preco_medio_revenda ASC
        ) AS ranking_mais_barato
    FROM vw_ultimo_periodo
    WHERE nivel_geografico = 'municipio'
)
SELECT
    data_inicial,
    uf,
    municipio,
    produto,
    unidade_medida,
    postos_pesquisados,
    preco_medio_revenda,
    preco_minimo_revenda,
    preco_maximo_revenda,
    ranking_mais_caro,
    ranking_mais_barato
FROM municipios_ranqueados
WHERE ranking_mais_caro <= 20
ORDER BY
    produto,
    unidade_medida,
    ranking_mais_caro,
    uf,
    municipio;


-- 4. Média mensal das observações semanais no nível Brasil.
-- Indicador derivado pelo projeto, não substitui a série mensal oficial da ANP.
WITH mensal AS (
    SELECT
        ano,
        mes,
        produto,
        unidade_medida,
        AVG(preco_medio_revenda) AS media_das_semanas,
        MIN(preco_medio_revenda) AS menor_semana,
        MAX(preco_medio_revenda) AS maior_semana,
        COUNT(DISTINCT data_inicial) AS semanas_observadas
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
    media_das_semanas,
    menor_semana,
    maior_semana,
    semanas_observadas,
    ROUND(
        100.0
        * (
            media_das_semanas
            - LAG(media_das_semanas)
                OVER (
                    PARTITION BY produto, unidade_medida
                    ORDER BY ano, mes
                )
        )
        / NULLIF(
            LAG(media_das_semanas)
                OVER (
                    PARTITION BY produto, unidade_medida
                    ORDER BY ano, mes
                ),
            0
        ),
        2
    ) AS variacao_mensal_pct
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
                WHERE (
                    BTRIM(produto) ILIKE 'ETANOL'
                    OR (
                        produto ILIKE '%ETANOL%'
                        AND produto ILIKE '%HIDRAT%'
                    )
                )
            ) AS etanol,
        COUNT(*)
            FILTER (
                WHERE (
                    BTRIM(produto) ILIKE 'ETANOL'
                    OR (
                        produto ILIKE '%ETANOL%'
                        AND produto ILIKE '%HIDRAT%'
                    )
                )
            ) AS etanol_observacoes,
        MAX(preco_medio_revenda)
            FILTER (
                WHERE (
                    BTRIM(produto) ILIKE 'GASOLINA'
                    OR (
                        produto ILIKE '%GASOLINA%'
                        AND produto ILIKE '%COMUM%'
                        AND produto NOT ILIKE '%ADITIV%'
                    )
                )
            ) AS gasolina,
        COUNT(*)
            FILTER (
                WHERE (
                    BTRIM(produto) ILIKE 'GASOLINA'
                    OR (
                        produto ILIKE '%GASOLINA%'
                        AND produto ILIKE '%COMUM%'
                        AND produto NOT ILIKE '%ADITIV%'
                    )
                )
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
    etanol AS preco_etanol,
    gasolina AS preco_gasolina_comum,
    ROUND(
        100.0
        * etanol
        / NULLIF(
            gasolina,
            0
        ),
        2
    ) AS relacao_etanol_gasolina_pct
FROM ultima_comparavel
WHERE ordem = 1
ORDER BY
    data_inicial DESC,
    relacao_etanol_gasolina_pct;
