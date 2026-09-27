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
        "PARTITION BY uf, municipio, unidade_medida"
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
        "-- 2. Preço médio por UF na última semana disponível de cada produto e unidade."
        in sql
    )
    assert (
        "-- 3. Municípios com maiores preços na última semana de cada produto e unidade."
        in sql
    )


def test_monthly_query_partitions_by_product_unit() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert (
        "GROUP BY\n        ano,\n        mes,\n        produto,\n        unidade_medida"
        in sql
    )
    assert (
        sql.count(
            "PARTITION BY produto, unidade_medida"
        )
        >= 2
    )


def test_ratio_sql_requires_same_unit() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert (
        "GROUP BY\n        data_inicial,\n        uf,\n        municipio,\n        unidade_medida"
        in sql
    )
    assert (
        "PARTITION BY uf, municipio, unidade_medida"
        in sql
    )


def test_latest_aggregate_view_is_scoped_by_geographic_level() -> None:
    sql = VIEWS_SQL.read_text(
        encoding="utf-8",
    )

    assert (
        "GROUP BY\n        produto,\n        unidade_medida,\n        nivel_geografico"
        in sql
    )
    assert (
        "u.nivel_geografico = v.nivel_geografico"
        in sql
    )


def test_city_top_20_is_partitioned_by_product_unit() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "WITH municipios_ordenados AS" in sql
    assert (
        "PARTITION BY\n                produto,\n                unidade_medida"
        in sql
    )
    assert "WHERE ordem <= 20" in sql
    assert "LIMIT 20" not in sql


def test_ratio_sql_rejects_ambiguous_fuel_classes() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "AS etanol_observacoes" in sql
    assert "AS gasolina_observacoes" in sql
    assert "etanol_observacoes = 1" in sql
    assert "gasolina_observacoes = 1" in sql
