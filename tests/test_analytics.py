import pandas as pd
import pytest

from src.analytics import (
    build_brazil_kpis,
    build_ethanol_gasoline_ratio,
    build_latest_city_ranking,
    build_latest_state_ranking,
    build_monthly_brazil,
    build_validated_analytics_exports,
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
            "uf": [
                None,
                None,
                None,
                None,
                "CE",
                "SP",
                "CE",
                "CE",
            ],
            "estado": [
                None,
                None,
                None,
                None,
                "CEARA",
                "SAO PAULO",
                "CEARA",
                "CEARA",
            ],
            "municipio": [
                None,
                None,
                None,
                None,
                None,
                None,
                "FORTALEZA",
                "FORTALEZA",
            ],
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
            "unidade_medida": [
                "R$/L",
                "R$/L",
                "R$/L",
                "R$/L",
                "R$/L",
                "R$/L",
                "R$/L",
                "R$/L",
            ],
            "postos_pesquisados": [
                100,
                100,
                100,
                100,
                20,
                20,
                10,
                10,
            ],
        }
    )


def test_brazil_kpis_calculate_weekly_change() -> None:
    result = build_brazil_kpis(_sample())
    row = result.loc[
        result["produto"].eq("GASOLINA COMUM")
    ].iloc[0]

    assert row["preco_atual"] == 6.24
    assert row["preco_semana_anterior"] == 6.18
    assert (
        round(
            row["variacao_semanal_pct"],
            2,
        )
        == 0.97
    )
    assert row["semanas_observadas"] == 4


def test_monthly_brazil_aggregates_weekly_observations() -> None:
    result = build_monthly_brazil(_sample())
    january = result.loc[
        result["mes"].eq(1)
    ].iloc[0]

    assert (
        round(
            january["media_das_semanas"],
            2,
        )
        == 6.06
    )
    assert january["semanas_observadas"] == 2


def test_state_ranking_orders_highest_price_first() -> None:
    result = build_latest_state_ranking(_sample())
    ce = result.loc[
        result["uf"].eq("CE")
    ].iloc[0]
    sp = result.loc[
        result["uf"].eq("SP")
    ].iloc[0]

    assert ce["ranking_mais_caro"] == 1
    assert sp["ranking_mais_caro"] == 2


def test_ethanol_gasoline_ratio_uses_common_gasoline() -> None:
    result = build_ethanol_gasoline_ratio(
        _sample()
    )
    row = result.iloc[0]

    assert row["municipio"] == "FORTALEZA"
    assert (
        round(
            row[
                "relacao_etanol_gasolina_pct"
            ],
            2,
        )
        == 72.00
    )


def test_analytics_returns_stable_empty_schemas() -> None:
    frame = _sample().loc[
        _sample()["nivel_geografico"].eq(
            "municipio"
        )
    ].copy()

    brazil = build_brazil_kpis(frame)
    monthly = build_monthly_brazil(frame)
    states = build_latest_state_ranking(frame)

    assert brazil.empty
    assert "produto" in brazil.columns
    assert monthly.empty
    assert "variacao_mensal_pct" in monthly.columns
    assert states.empty
    assert "ranking_mais_caro" in states.columns



def test_validated_aggregate_analytics_accepts_clean_data() -> None:
    exports = (
        build_validated_analytics_exports(
            _sample()
        )
    )

    assert (
        not exports[
            "kpis_brasil_2026"
        ].empty
    )


def test_validated_aggregate_analytics_blocks_invalid_data() -> None:
    frame = _sample()
    frame.loc[
        0,
        "preco_medio_revenda",
    ] = 0

    with pytest.raises(
        ValueError,
        match=(
            "falhou na validação "
            "de qualidade"
        ),
    ):
        build_validated_analytics_exports(
            frame
        )



def test_rankings_use_latest_date_per_product() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-02-01",
                "2026-02-01",
                "2026-02-08",
                "2026-02-08",
                "2026-02-01",
                "2026-02-01",
                "2026-02-08",
                "2026-02-08",
            ],
            "data_final": [
                "2026-02-07",
                "2026-02-07",
                "2026-02-14",
                "2026-02-14",
                "2026-02-07",
                "2026-02-07",
                "2026-02-14",
                "2026-02-14",
            ],
            "nivel_geografico": [
                "estado",
                "estado",
                "estado",
                "estado",
                "municipio",
                "municipio",
                "municipio",
                "municipio",
            ],
            "uf": [
                "CE",
                "SP",
                "CE",
                "SP",
                "CE",
                "SP",
                "CE",
                "SP",
            ],
            "estado": [
                "CEARA",
                "SAO PAULO",
                "CEARA",
                "SAO PAULO",
                "CEARA",
                "SAO PAULO",
                "CEARA",
                "SAO PAULO",
            ],
            "municipio": [
                None,
                None,
                None,
                None,
                "FORTALEZA",
                "SAO PAULO",
                "FORTALEZA",
                "SAO PAULO",
            ],
            "produto": [
                "ETANOL HIDRATADO",
                "ETANOL HIDRATADO",
                "GASOLINA COMUM",
                "GASOLINA COMUM",
                "ETANOL HIDRATADO",
                "ETANOL HIDRATADO",
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "preco_medio_revenda": [
                4.50,
                4.40,
                6.30,
                6.10,
                4.55,
                4.45,
                6.25,
                6.05,
            ],
        }
    )

    states = build_latest_state_ranking(
        frame
    )
    cities = build_latest_city_ranking(
        frame
    )

    assert set(
        states["produto"]
    ) == {
        "ETANOL HIDRATADO",
        "GASOLINA COMUM",
    }
    assert set(
        cities["produto"]
    ) == {
        "ETANOL HIDRATADO",
        "GASOLINA COMUM",
    }

    ethanol_states = states.loc[
        states["produto"].eq(
            "ETANOL HIDRATADO"
        )
    ]
    gasoline_states = states.loc[
        states["produto"].eq(
            "GASOLINA COMUM"
        )
    ]

    assert (
        ethanol_states[
            "data_inicial"
        ].nunique()
        == 1
    )
    assert (
        ethanol_states[
            "data_inicial"
        ].iloc[0]
        == pd.Timestamp(
            "2026-02-01"
        )
    )
    assert (
        gasoline_states[
            "data_inicial"
        ].iloc[0]
        == pd.Timestamp(
            "2026-02-08"
        )
    )


def test_ratio_uses_latest_common_week_and_excludes_additive_gasoline() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-02-01",
                "2026-02-01",
                "2026-02-08",
                "2026-02-08",
            ],
            "data_final": [
                "2026-02-07",
                "2026-02-07",
                "2026-02-14",
                "2026-02-14",
            ],
            "nivel_geografico": [
                "municipio",
                "municipio",
                "municipio",
                "municipio",
            ],
            "uf": [
                "CE",
                "CE",
                "CE",
                "CE",
            ],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "produto": [
                "ETANOL HIDRATADO",
                "GASOLINA COMUM",
                "ETANOL HIDRATADO",
                "GASOLINA ADITIVADA",
            ],
            "preco_medio_revenda": [
                4.40,
                6.20,
                4.60,
                6.50,
            ],
        }
    )

    result = (
        build_ethanol_gasoline_ratio(
            frame
        )
    )

    assert len(result) == 1
    assert (
        result.iloc[0][
            "data_inicial"
        ]
        == pd.Timestamp(
            "2026-02-01"
        )
    )
    assert (
        round(
            result.iloc[0][
                "relacao_etanol_gasolina_pct"
            ],
            2,
        )
        == 70.97
    )


def test_aggregate_analytics_isolate_product_units() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-02-01",
                "2026-02-08",
                "2026-02-01",
            ],
            "data_final": [
                "2026-02-07",
                "2026-02-14",
                "2026-02-07",
            ],
            "nivel_geografico": [
                "brasil",
                "brasil",
                "brasil",
            ],
            "produto": [
                "PRODUTO TESTE",
                "PRODUTO TESTE",
                "PRODUTO TESTE",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/L",
                "R$/M3",
            ],
            "preco_medio_revenda": [
                6.0,
                6.2,
                4.5,
            ],
        }
    )

    result = build_brazil_kpis(
        frame
    )

    assert len(result) == 2
    latest = {
        row.unidade_medida: (
            row.ultima_semana_inicio,
            row.preco_atual,
        )
        for row in result.itertuples()
    }
    assert latest["R$/L"] == (
        pd.Timestamp("2026-02-08"),
        6.2,
    )
    assert latest["R$/M3"] == (
        pd.Timestamp("2026-02-01"),
        4.5,
    )


def test_ratio_does_not_mix_different_units() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-02-08",
                "2026-02-08",
                "2026-02-08",
                "2026-02-08",
            ],
            "data_final": [
                "2026-02-14",
                "2026-02-14",
                "2026-02-14",
                "2026-02-14",
            ],
            "nivel_geografico": [
                "municipio",
                "municipio",
                "municipio",
                "municipio",
            ],
            "uf": [
                "CE",
                "CE",
                "CE",
                "CE",
            ],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "produto": [
                "ETANOL HIDRATADO",
                "GASOLINA COMUM",
                "ETANOL HIDRATADO",
                "GASOLINA COMUM",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/M3",
                "R$/M3",
                "R$/M3",
            ],
            "preco_medio_revenda": [
                4.5,
                6200.0,
                4500.0,
                6200.0,
            ],
        }
    )

    result = build_ethanol_gasoline_ratio(
        frame
    )

    assert len(result) == 1
    assert (
        result.iloc[0][
            "unidade_medida"
        ]
        == "R$/M3"
    )
    assert round(
        result.iloc[0][
            "relacao_etanol_gasolina_pct"
        ],
        2,
    ) == 72.58


def test_ratio_rejects_ambiguous_fuel_class() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-02-08",
                "2026-02-08",
                "2026-02-08",
            ],
            "data_final": [
                "2026-02-14",
                "2026-02-14",
                "2026-02-14",
            ],
            "nivel_geografico": [
                "municipio",
                "municipio",
                "municipio",
            ],
            "uf": [
                "CE",
                "CE",
                "CE",
            ],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "produto": [
                "ETANOL HIDRATADO",
                "GASOLINA COMUM",
                "GASOLINA PREMIUM",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/L",
                "R$/L",
            ],
            "preco_medio_revenda": [
                4.50,
                6.20,
                7.10,
            ],
        }
    )

    result = build_ethanol_gasoline_ratio(
        frame
    )

    assert result.empty
