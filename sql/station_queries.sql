-- PostgreSQL
-- Consultas de referência para a camada por estabelecimento.
-- A última coleta é calculada por produto e unidade de medida.

-- Base auxiliar com a última data disponível de cada produto.
WITH ultima_coleta_produto AS (
    SELECT
        f.produto_posto_id,
        MAX(d.data_coleta) AS data_coleta
    FROM fato_precos_postos f
    JOIN dim_data_coleta d
        ON d.data_coleta_id = f.data_coleta_id
    GROUP BY
        f.produto_posto_id
)
SELECT
    d.data_coleta,
    p.uf,
    p.municipio,
    pr.produto,
    pr.unidade_medida,
    COUNT(*) AS observacoes,
    COUNT(DISTINCT p.posto_id) AS postos_distintos,
    AVG(f.preco_revenda) AS preco_medio,
    PERCENTILE_CONT(0.5)
        WITHIN GROUP (
            ORDER BY f.preco_revenda
        ) AS mediana,
    MIN(f.preco_revenda) AS preco_minimo,
    MAX(f.preco_revenda) AS preco_maximo,
    PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY f.preco_revenda
        ) AS q1,
    PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY f.preco_revenda
        ) AS q3,
    (
        PERCENTILE_CONT(0.75)
            WITHIN GROUP (
                ORDER BY f.preco_revenda
            )
        - PERCENTILE_CONT(0.25)
            WITHIN GROUP (
                ORDER BY f.preco_revenda
            )
    ) AS intervalo_interquartil,
    STDDEV_SAMP(
        f.preco_revenda
    ) AS desvio_padrao,
    (
        100
        * STDDEV_SAMP(
            f.preco_revenda
        )
        / NULLIF(
            AVG(
                f.preco_revenda
            ),
            0
        )
    ) AS coef_variacao_pct
FROM fato_precos_postos f
JOIN dim_data_coleta d
    ON d.data_coleta_id = f.data_coleta_id
JOIN dim_produto_posto pr
    ON pr.produto_posto_id = f.produto_posto_id
JOIN dim_posto p
    ON p.posto_id = f.posto_id
JOIN ultima_coleta_produto u
    ON u.produto_posto_id = f.produto_posto_id
    AND u.data_coleta = d.data_coleta
GROUP BY
    d.data_coleta,
    p.uf,
    p.municipio,
    pr.produto,
    pr.unidade_medida
ORDER BY
    pr.produto,
    pr.unidade_medida,
    preco_medio DESC;


-- Comparação entre bandeiras na última coleta de cada produto.
WITH ultima_coleta_produto AS (
    SELECT
        f.produto_posto_id,
        MAX(d.data_coleta) AS data_coleta
    FROM fato_precos_postos f
    JOIN dim_data_coleta d
        ON d.data_coleta_id = f.data_coleta_id
    GROUP BY
        f.produto_posto_id
)
SELECT
    d.data_coleta,
    COALESCE(
        NULLIF(
            BTRIM(
                p.bandeira
            ),
            ''
        ),
        'NÃO INFORMADA'
    ) AS bandeira,
    pr.produto,
    pr.unidade_medida,
    COUNT(*) AS observacoes,
    COUNT(
        DISTINCT p.posto_id
    ) AS postos_distintos,
    AVG(
        f.preco_revenda
    ) AS preco_medio,
    PERCENTILE_CONT(0.5)
        WITHIN GROUP (
            ORDER BY f.preco_revenda
        ) AS mediana,
    MIN(
        f.preco_revenda
    ) AS preco_minimo,
    MAX(
        f.preco_revenda
    ) AS preco_maximo,
    STDDEV_SAMP(
        f.preco_revenda
    ) AS desvio_padrao
FROM fato_precos_postos f
JOIN dim_data_coleta d
    ON d.data_coleta_id = f.data_coleta_id
JOIN dim_produto_posto pr
    ON pr.produto_posto_id = f.produto_posto_id
JOIN dim_posto p
    ON p.posto_id = f.posto_id
JOIN ultima_coleta_produto u
    ON u.produto_posto_id = f.produto_posto_id
    AND u.data_coleta = d.data_coleta
GROUP BY
    d.data_coleta,
    COALESCE(
        NULLIF(
            BTRIM(
                p.bandeira
            ),
            ''
        ),
        'NÃO INFORMADA'
    ),
    pr.produto,
    pr.unidade_medida
HAVING
    COUNT(*) >= 5
    AND COUNT(
        DISTINCT p.posto_id
    ) >= 3
ORDER BY
    pr.produto,
    pr.unidade_medida,
    preco_medio;


-- Postos com menor preço na última coleta de cada produto.
WITH ultima_coleta_produto AS (
    SELECT
        f.produto_posto_id,
        MAX(d.data_coleta) AS data_coleta
    FROM fato_precos_postos f
    JOIN dim_data_coleta d
        ON d.data_coleta_id = f.data_coleta_id
    GROUP BY
        f.produto_posto_id
)
SELECT
    d.data_coleta,
    p.uf,
    p.municipio,
    p.revenda,
    p.bandeira,
    pr.produto,
    pr.unidade_medida,
    f.preco_revenda
FROM fato_precos_postos f
JOIN dim_data_coleta d
    ON d.data_coleta_id = f.data_coleta_id
JOIN dim_produto_posto pr
    ON pr.produto_posto_id = f.produto_posto_id
JOIN dim_posto p
    ON p.posto_id = f.posto_id
JOIN ultima_coleta_produto u
    ON u.produto_posto_id = f.produto_posto_id
    AND u.data_coleta = d.data_coleta
ORDER BY
    pr.produto,
    pr.unidade_medida,
    f.preco_revenda,
    p.uf,
    p.municipio,
    p.revenda;
