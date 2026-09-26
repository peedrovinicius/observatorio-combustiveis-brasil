from src.config import PROJECT_ROOT

VIEWS_SQL = (
    PROJECT_ROOT
    / "sql"
    / "views.sql"
)
QUERIES_SQL = (
    PROJECT_ROOT
    / "sql"
    / "queries.sql"
)


def test_latest_aggregate_view_is_per_product() -> None:
    sql = VIEWS_SQL.read_text(
        encoding="utf-8",
    )

    assert (
        "WITH ultima_data_produto AS"
        in sql
    )
    assert (
        "GROUP BY\n        produto,\n        unidade_medida"
        in sql
    )
    assert (
        "SELECT MAX(data_inicial)\n"
        "    FROM vw_precos_semanais"
        not in sql
    )


def test_ratio_sql_uses_latest_comparable_week() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert (
        "ROW_NUMBER() OVER"
        in sql
    )
    assert (
        "PARTITION BY uf, municipio"
        in sql
    )
    assert (
        "produto NOT ILIKE '%ADITIV%'"
        in sql
    )
    assert (
        "WHERE ordem = 1"
        in sql
    )


def test_latest_ranking_queries_expose_product_and_date() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert (
        "-- 2. Preço médio por UF na última semana disponível de cada produto."
        in sql
    )
    assert (
        "-- 3. Municípios com maiores preços na última semana de cada produto."
        in sql
    )
