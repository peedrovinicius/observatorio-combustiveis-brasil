import pandas as pd
import pytest

from src.station_analytics import (
    build_latest_brand_summary,
    build_latest_municipality_distribution,
    build_station_coverage,
    build_validated_station_analytics_exports,
)


def _sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_coleta": [
                "2026-09-19",
                "2026-09-20",
                "2026-09-20",
                "2026-09-20",
                "2026-09-20",
                "2026-09-18",
            ],
            "uf": [
                "CE",
                "CE",
                "CE",
                "CE",
                "CE",
                "SP",
            ],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
                "CAUCAIA",
                "SAO PAULO",
            ],
            "revenda": [
                "POSTO A",
                "POSTO A",
                "POSTO B",
                "POSTO C",
                "POSTO D",
                "POSTO E",
            ],
            "cnpj_revenda": [
                "00000000000100",
                "00000000000100",
                "00000000000200",
                "00000000000300",
                "00000000000400",
                "00000000000500",
            ],
            "produto": [
                "GASOLINA",
                "GASOLINA",
                "GASOLINA",
                "GASOLINA",
                "GASOLINA",
                "ETANOL",
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
                "R$ / litro",
                "R$ / litro",
                "R$ / litro",
                "R$ / litro",
            ],
            "preco_revenda": [
                6.00,
                6.10,
                6.20,
                6.30,
                6.40,
                4.50,
            ],
            "bandeira": [
                "A",
                "A",
                "A",
                "A",
                "B",
                "C",
            ],
        }
    )


def test_station_coverage_summarizes_year() -> None:
    result = build_station_coverage(
        _sample()
    )
    gasoline = result.loc[
        result["produto"].eq(
            "GASOLINA"
        )
    ].iloc[0]

    assert gasoline["observacoes"] == 5
    assert (
        gasoline[
            "postos_distintos"
        ]
        == 4
    )
    assert gasoline["municipios"] == 2
    assert gasoline["ufs"] == 1
    assert round(
        gasoline[
            "mediana_observada"
        ],
        2,
    ) == 6.20


def test_latest_distribution_uses_latest_date_per_product() -> None:
    result = (
        build_latest_municipality_distribution(
            _sample()
        )
    )

    gasoline = result.loc[
        result["produto"].eq(
            "GASOLINA"
        )
    ]
    ethanol = result.loc[
        result["produto"].eq(
            "ETANOL"
        )
    ]

    assert gasoline[
        "data_coleta"
    ].nunique() == 1
    assert (
        gasoline[
            "data_coleta"
        ].iloc[0]
        == pd.Timestamp(
            "2026-09-20"
        )
    )
    assert (
        ethanol[
            "data_coleta"
        ].iloc[0]
        == pd.Timestamp(
            "2026-09-18"
        )
    )


def test_municipality_distribution_calculates_median_and_iqr() -> None:
    result = (
        build_latest_municipality_distribution(
            _sample()
        )
    )
    fortaleza = result.loc[
        result["municipio"].eq(
            "FORTALEZA"
        )
    ].iloc[0]

    assert (
        fortaleza[
            "postos_distintos"
        ]
        == 3
    )
    assert round(
        fortaleza[
            "mediana_observada"
        ],
        2,
    ) == 6.20
    assert round(
        fortaleza[
            "intervalo_interquartil"
        ],
        2,
    ) == 0.10


def test_brand_summary_flags_small_samples() -> None:
    result = build_latest_brand_summary(
        _sample(),
        min_observations=3,
        min_stations=3,
    )

    brand_a = result.loc[
        result["bandeira"].eq("A")
    ].iloc[0]
    brand_b = result.loc[
        result["bandeira"].eq("B")
    ].iloc[0]

    assert bool(
        brand_a[
            "amostra_suficiente"
        ]
    )
    assert not bool(
        brand_b[
            "amostra_suficiente"
        ]
    )


def test_empty_station_data_returns_stable_schema() -> None:
    empty = _sample().iloc[
        0:0
    ].copy()

    coverage = build_station_coverage(
        empty
    )
    distribution = (
        build_latest_municipality_distribution(
            empty
        )
    )

    assert coverage.empty
    assert (
        "postos_distintos"
        in coverage.columns
    )
    assert distribution.empty
    assert (
        "coef_variacao_pct"
        in distribution.columns
    )



def test_validated_station_analytics_accepts_clean_data() -> None:
    frame = _sample().loc[
        lambda item: ~(
            item["produto"].eq(
                "GASOLINA"
            )
            & item[
                "data_coleta"
            ].eq(
                "2026-09-19"
            )
        )
    ].copy()

    exports = (
        build_validated_station_analytics_exports(
            frame
        )
    )

    assert (
        not exports[
            "resumo_postos_2026"
        ].empty
    )
    assert (
        not exports[
            "distribuicao_municipios_ultima_coleta"
        ].empty
    )


def test_validated_station_analytics_blocks_invalid_price() -> None:
    frame = _sample()
    frame.loc[
        0,
        "preco_revenda",
    ] = 0

    with pytest.raises(
        ValueError,
        match=(
            "falhou na validação "
            "de qualidade"
        ),
    ):
        build_validated_station_analytics_exports(
            frame
        )


def test_validated_station_analytics_blocks_duplicate_business_key() -> None:
    frame = _sample()
    duplicate = frame.iloc[
        [1]
    ].copy()
    frame = pd.concat(
        [
            frame,
            duplicate,
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ValueError,
        match=(
            "falhou na validação "
            "de qualidade"
        ),
    ):
        build_validated_station_analytics_exports(
            frame
        )
