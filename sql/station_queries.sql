-- PostgreSQL
-- Consultas para a camada por estabelecimento.

-- Distribuição de preço por município na data mais recente.
SELECT
    p.uf,
    p.municipio,
    pr.produto,
    COUNT(*) AS observacoes,
    AVG(f.preco_revenda) AS preco_medio,
    MIN(f.preco_revenda) AS preco_minimo,
    MAX(f.preco_revenda) AS preco_maximo,
    STDDEV_SAMP(f.preco_revenda) AS desvio_padrao
FROM fato_precos_postos f
JOIN dim_data_coleta d
    ON d.data_coleta_id = f.data_coleta_id
JOIN dim_produto_posto pr
    ON pr.produto_posto_id = f.produto_posto_id
JOIN dim_posto p
    ON p.posto_id = f.posto_id
WHERE d.data_coleta = (
    SELECT MAX(data_coleta)
    FROM dim_data_coleta
)
GROUP BY p.uf, p.municipio, pr.produto
ORDER BY pr.produto, preco_medio DESC;


-- Comparação entre bandeiras.
SELECT
    p.bandeira,
    pr.produto,
    COUNT(DISTINCT p.posto_id) AS postos,
    COUNT(*) AS observacoes,
    AVG(f.preco_revenda) AS preco_medio,
    PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY f.preco_revenda) AS mediana
FROM fato_precos_postos f
JOIN dim_produto_posto pr
    ON pr.produto_posto_id = f.produto_posto_id
JOIN dim_posto p
    ON p.posto_id = f.posto_id
GROUP BY p.bandeira, pr.produto
HAVING COUNT(*) >= 5
ORDER BY pr.produto, preco_medio;


-- Postos com menor preço na última data observada.
SELECT
    d.data_coleta,
    p.uf,
    p.municipio,
    p.revenda,
    p.bandeira,
    pr.produto,
    f.preco_revenda
FROM fato_precos_postos f
JOIN dim_data_coleta d
    ON d.data_coleta_id = f.data_coleta_id
JOIN dim_produto_posto pr
    ON pr.produto_posto_id = f.produto_posto_id
JOIN dim_posto p
    ON p.posto_id = f.posto_id
WHERE d.data_coleta = (
    SELECT MAX(data_coleta)
    FROM dim_data_coleta
)
ORDER BY pr.produto, f.preco_revenda;
