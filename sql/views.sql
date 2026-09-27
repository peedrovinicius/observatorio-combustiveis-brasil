-- PostgreSQL
-- Camada semântica para consultas analíticas.

CREATE OR REPLACE VIEW vw_precos_semanais AS
SELECT
    f.preco_fato_id,
    d.data_inicial,
    d.data_final,
    d.ano,
    d.mes,
    d.semana_iso,
    d.trimestre,
    p.produto,
    l.nivel_geografico,
    NULLIF(l.regiao, '') AS regiao,
    NULLIF(l.uf, '') AS uf,
    NULLIF(l.estado, '') AS estado,
    NULLIF(l.municipio, '') AS municipio,
    f.postos_pesquisados,
    f.unidade_medida,
    f.preco_medio_revenda,
    f.preco_minimo_revenda,
    f.preco_maximo_revenda,
    f.desvio_padrao_revenda,
    f.coef_variacao_revenda,
    f.fonte_arquivo,
    f.fonte_planilha
FROM fato_precos_semanais f
JOIN dim_data d
    ON d.data_id = f.data_id
JOIN dim_produto p
    ON p.produto_id = f.produto_id
JOIN dim_localidade l
    ON l.localidade_id = f.localidade_id;

CREATE OR REPLACE VIEW vw_ultimo_periodo AS
WITH ultima_data_serie AS (
    SELECT
        produto,
        unidade_medida,
        nivel_geografico,
        MAX(data_inicial) AS data_inicial
    FROM vw_precos_semanais
    GROUP BY
        produto,
        unidade_medida,
        nivel_geografico
)
SELECT v.*
FROM vw_precos_semanais v
JOIN ultima_data_serie u
    ON u.produto = v.produto
    AND u.unidade_medida IS NOT DISTINCT FROM v.unidade_medida
    AND u.nivel_geografico = v.nivel_geografico
    AND u.data_inicial = v.data_inicial;
