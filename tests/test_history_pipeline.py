from pathlib import Path

import pandas as pd

from src.consolidate import (
    build_analytics_table,
    infer_geographic_level,
)
from src.download_history import (
    _discover_weekly_history_links,
)
from src.quality import build_quality_report
from src.transform import parse_decimal_series


def test_history_discovery_uses_post_2013_section() -> None:
    html = """
    <h2>Série histórica semanal</h2>
    <a href="old-br.xlsx">Brasil</a>
    <a href="#2013">A partir de 2013</a>
    <a href="new-br.xlsx">Brasil</a>
    <a href="regions.xlsx">Regiões</a>
    <a href="states.xlsx">Estados</a>
    <a href="cities-2026.xlsx">Municípios (2026)</a>
    <h2>Série histórica mensal</h2>
    <a href="monthly.xlsx">Brasil</a>
    """

    links = _discover_weekly_history_links(html)

    assert links["brasil"].endswith(
        "new-br.xlsx"
    )
    assert links["municipios_2026"].endswith(
        "cities-2026.xlsx"
    )


def test_decimal_parser_handles_brazilian_and_dot_decimal() -> None:
    parsed = parse_decimal_series(
        pd.Series(
            ["6,12", "6.12", "1.234,56"]
        )
    )
    assert parsed.tolist() == [
        6.12,
        6.12,
        1234.56,
    ]


def test_geographic_level_prefers_most_granular() -> None:
    frame = pd.DataFrame(
        {
            "regiao": [
                None,
                "NORDESTE",
                "NORDESTE",
                "NORDESTE",
            ],
            "uf": [
                None,
                None,
                "CE",
                "CE",
            ],
            "municipio": [
                None,
                None,
                None,
                "FORTALEZA",
            ],
        }
    )

    assert infer_geographic_level(
        frame
    ).tolist() == [
        "brasil",
        "regiao",
        "estado",
        "municipio",
    ]


def test_consolidation_filters_2026_and_removes_duplicates(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
                "2026-01-04",
                "2025-12-28",
            ],
            "data_final": [
                "2026-01-10",
                "2026-01-10",
                "2026-01-03",
            ],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "uf": ["CE", "CE", "CE"],
            "produto": [
                "GASOLINA",
                "GASOLINA",
                "GASOLINA",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/L",
                "R$/L",
            ],
            "preco_medio_revenda": [
                6.0,
                6.0,
                5.9,
            ],
        }
    )
    frame.to_csv(
        tmp_path / "sample.csv",
        index=False,
    )

    result = build_analytics_table(tmp_path)

    assert len(result) == 1
    assert result.loc[0, "ano"] == 2026
    assert (
        result.loc[
            0,
            "nivel_geografico",
        ]
        == "municipio"
    )


def _valid_quality_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "produto": ["GASOLINA"],
            "preco_medio_revenda": [6.0],
            "preco_minimo_revenda": [5.8],
            "preco_maximo_revenda": [6.2],
            "nivel_geografico": [
                "brasil",
            ],
            "unidade_medida": ["R$/L"],
        }
    )


def test_quality_report_passes_valid_row() -> None:
    report = build_quality_report(
        _valid_quality_frame()
    )

    assert report["status"] == "passed"


def test_quality_report_blocks_non_positive_prices() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "preco_medio_revenda"] = 0

    report = build_quality_report(frame)

    assert (
        report["non_positive_price_rows"]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_invalid_dates() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "data_inicial"] = "invalida"

    report = build_quality_report(frame)

    assert (
        report["invalid_start_date_rows"]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_inverted_period() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "data_final"] = (
        "2026-01-03"
    )

    report = build_quality_report(frame)

    assert (
        report["end_before_start_rows"]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_outside_2026() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "data_inicial"] = (
        "2025-12-28"
    )

    report = build_quality_report(frame)

    assert report["outside_2026_rows"] == 1
    assert report["status"] == "failed"
