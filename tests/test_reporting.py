from pathlib import Path

import pandas as pd

from src.reporting import (
    _location_label,
    _select_common_gasoline,
    build_insights_markdown,
    plot_station_brand_median,
    plot_station_municipality_dispersion,
)


def test_select_common_gasoline_excludes_additive() -> None:
    products = pd.Series(
        [
            "GASOLINA ADITIVADA",
            "GASOLINA COMUM",
            "ETANOL HIDRATADO",
        ]
    )

    assert (
        _select_common_gasoline(
            products
        )
        == "GASOLINA COMUM"
    )


def test_location_label_handles_missing_uf() -> None:
    row = pd.Series(
        {
            "uf": pd.NA,
            "estado": "CEARA",
        }
    )

    assert (
        _location_label(row)
        == "CEARA"
    )


def test_insights_use_data_values() -> None:
    kpis = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM"
            ],
            "preco_atual": [6.25],
            "variacao_semanal_pct": [
                1.5
            ],
            "variacao_desde_inicio_ano_pct": [
                2.0
            ],
            "menor_preco_2026": [
                5.90
            ],
            "maior_preco_2026": [
                6.40
            ],
        }
    )
    ranking = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "uf": ["CE", "SP"],
            "preco_medio_revenda": [
                6.30,
                6.10,
            ],
        }
    )

    text = build_insights_markdown(
        kpis,
        ranking,
        {
            "status": "passed"
        },
        {
            "status": "passed",
            "postos_distintos_cnpj": 100,
            "municipios": 20,
        },
    )

    assert "R$ 6,25" in text
    assert "+1,50%" in text
    assert "CE: R$ 6,30" in text
    assert (
        "Postos distintos por CNPJ: **100**"
        in text
    )


def test_station_dispersion_chart_is_created(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "uf": [
                "CE",
                "CE",
            ],
            "municipio": [
                "FORTALEZA",
                "CAUCAIA",
            ],
            "postos_distintos": [
                5,
                4,
            ],
            "intervalo_interquartil": [
                0.20,
                0.10,
            ],
        }
    )
    output = (
        tmp_path
        / "dispersao.png"
    )

    plot_station_municipality_dispersion(
        frame,
        output,
    )

    assert output.exists()
    assert (
        output.stat().st_size
        > 0
    )


def test_station_brand_chart_handles_insufficient_sample(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM"
            ],
            "bandeira": ["A"],
            "postos_distintos": [1],
            "observacoes": [1],
            "mediana_observada": [
                6.20
            ],
            "amostra_suficiente": [
                False
            ],
        }
    )
    output = (
        tmp_path
        / "bandeiras.png"
    )

    plot_station_brand_median(
        frame,
        output,
    )

    assert output.exists()
    assert (
        output.stat().st_size
        > 0
    )
