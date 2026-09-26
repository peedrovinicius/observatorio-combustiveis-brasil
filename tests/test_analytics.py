import pandas as pd

from src.analytics import (
    build_brazil_kpis,
    build_ethanol_gasoline_ratio,
    build_latest_state_ranking,
    build_monthly_brazil,
)


def _sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
                "2026-01-11",
                "2026-02-01",
                "2026-02-08",
                "2026-02-08",
                "2026-02-08",
                "2026-02-08",
                "2026-02-08",
            ],
            "data_final": [
                "2026-01-10",
                "2026-01-17",
                "2026-02-07",
                "2026-02-14",
                "2026-02-14",
                "2026-02-14",
                "2026-02-14",
                "2026-02-14",
            ],
            "nivel_geografico": [
                "brasil",
                "brasil",
                "brasil",
                "brasil",
                "estado",
                "estado",
                "municipio",
                "municipio",
            ],
            "uf": [None, None, None, None, "CE", "SP", "CE", "CE"],
            "estado": [None, None, None, None, "CEARA", "SAO PAULO", "CEARA", "CEARA"],
            "municipio": [None, None, None, None, None, None, "FORTALEZA", "FORTALEZA"],
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
                "GASOLINA COMUM",
                "GASOLINA COMUM",
                "GASOLINA COMUM",
                "GASOLINA COMUM",
                "ETANOL HIDRATADO",
                "GASOLINA COMUM",
            ],
            "preco_medio_revenda": [
                6.00,
                6.12,
                6.18,
                6.24,
                6.30,
                6.10,
                4.50,
                6.25,
            ],
            "postos_pesquisados": [100, 100, 100, 100, 20, 20, 10, 10],
        }
    )


def test_brazil_kpis_calculate_weekly_change() -> None:
    result = build_brazil_kpis(_sample())
    row = result.loc[result["produto"].eq("GASOLINA COMUM")].iloc[0]

    assert row["preco_atual"] == 6.24
    assert row["preco_semana_anterior"] == 6.18
    assert round(row["variacao_semanal_pct"], 2) == 0.97
    assert row["semanas_observadas"] == 4


def test_monthly_brazil_aggregates_weekly_observations() -> None:
    result = build_monthly_brazil(_sample())
    january = result.loc[result["mes"].eq(1)].iloc[0]

    assert round(january["media_das_semanas"], 2) == 6.06
    assert january["semanas_observadas"] == 2


def test_state_ranking_orders_highest_price_first() -> None:
    result = build_latest_state_ranking(_sample())
    ce = result.loc[result["uf"].eq("CE")].iloc[0]
    sp = result.loc[result["uf"].eq("SP")].iloc[0]

    assert ce["ranking_mais_caro"] == 1
    assert sp["ranking_mais_caro"] == 2


def test_ethanol_gasoline_ratio_uses_common_gasoline() -> None:
    result = build_ethanol_gasoline_ratio(_sample())
    row = result.iloc[0]

    assert row["municipio"] == "FORTALEZA"
    assert round(row["relacao_etanol_gasolina_pct"], 2) == 72.00
