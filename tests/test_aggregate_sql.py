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


def test_latest_aggregate_view_is_per_product_unit_level() -> None:
    sql = VIEWS_SQL.read_text(
        encoding="utf-8",
    )

    assert (
        "WITH ultima_data_serie AS"
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

    assert "WITH municipios_ranqueados AS" in sql
    assert (
        "PARTITION BY\n                produto,\n                unidade_medida"
        in sql
    )
    assert "WHERE ranking_mais_caro <= 20" in sql
    assert "LIMIT 20" not in sql


def test_ratio_sql_rejects_ambiguous_fuel_classes() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "AS etanol_observacoes" in sql
    assert "AS gasolina_observacoes" in sql
    assert "etanol_observacoes = 1" in sql
    assert "gasolina_observacoes = 1" in sql


def test_ratio_sql_requires_hydrated_ethanol_and_common_gasoline() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "produto ILIKE '%HIDRAT%'" in sql
    assert "produto ILIKE '%COMUM%'" in sql
    assert "produto NOT ILIKE '%ADITIV%'" in sql


def test_ratio_sql_accepts_plain_fuel_aliases() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "BTRIM(produto) ILIKE 'ETANOL'" in sql
    assert "BTRIM(produto) ILIKE 'GASOLINA'" in sql


def test_ranking_queries_do_not_pre_filter_product() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )
    ranking_section = sql.split(
        "-- 2. Preço médio por UF",
        1,
    )[1].split(
        "-- 4. Média mensal",
        1,
    )[0]

    assert "ILIKE 'GASOLINA%'" not in ranking_section


def test_ranking_sql_exposes_python_contract_columns() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "AS ranking_mais_caro" in sql
    assert "AS ranking_mais_barato" in sql
    assert "preco_minimo_revenda" in sql
    assert "preco_maximo_revenda" in sql


def test_monthly_sql_uses_python_export_names() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "AS media_das_semanas" in sql
    assert "AS menor_semana" in sql
    assert "AS maior_semana" in sql
    assert "AS semanas_observadas" in sql
    assert "AS variacao_mensal_pct" in sql
    assert "media_semanal_no_mes" not in sql
    assert "variacao_percentual_mes" not in sql


def test_ratio_sql_uses_python_export_names() -> None:
    sql = QUERIES_SQL.read_text(
        encoding="utf-8",
    )

    assert "etanol AS preco_etanol" in sql
    assert "gasolina AS preco_gasolina_comum" in sql
    assert "AS relacao_etanol_gasolina_pct" in sql
