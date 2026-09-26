from pathlib import Path

from src.config import PROJECT_ROOT

STATION_QUERIES = (
    PROJECT_ROOT
    / "sql"
    / "station_queries.sql"
)


def _sql() -> str:
    return STATION_QUERIES.read_text(
        encoding="utf-8",
    )


def test_station_sql_uses_latest_date_per_product() -> None:
    sql = _sql()

    assert (
        sql.count(
            "WITH ultima_coleta_produto AS"
        )
        == 3
    )
    assert (
        sql.count(
            "GROUP BY\n        f.produto_posto_id"
        )
        == 3
    )
    assert (
        "SELECT MAX(data_coleta)\n"
        "    FROM dim_data_coleta"
        not in sql
    )


def test_station_sql_brand_sample_matches_python_rule() -> None:
    sql = _sql()

    assert "COUNT(*) >= 5" in sql
    assert (
        "DISTINCT p.posto_id"
        in sql
    )
    assert ") >= 3" in sql


def test_station_sql_distribution_exposes_expected_metrics() -> None:
    sql = _sql()

    expected = (
        "mediana",
        "q1",
        "q3",
        "intervalo_interquartil",
        "desvio_padrao",
        "coef_variacao_pct",
        "postos_distintos",
    )

    for metric in expected:
        assert metric in sql
