import pandas as pd

from src.station_quality import (
    build_station_quality_report,
)


def _valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_coleta": [
                "2026-09-20",
                "2026-09-20",
            ],
            "uf": ["CE", "CE"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
            ],
            "produto": [
                "GASOLINA",
                "ETANOL",
            ],
            "preco_revenda": [
                6.10,
                4.50,
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
            ],
            "cnpj_revenda": [
                "00.000.000/0001-00",
                "00.000.000/0001-00",
            ],
            "bandeira": [
                "BRANCA",
                "BRANCA",
            ],
            "revenda": [
                "POSTO A",
                "POSTO A",
            ],
        }
    )


def test_station_quality_passes_clean_data() -> None:
    report = build_station_quality_report(
        _valid_frame()
    )

    assert report["status"] == "passed"
    assert report["ufs"] == 1
    assert report["municipios"] == 1
    assert (
        report[
            "postos_distintos_cnpj"
        ]
        == 1
    )


def test_station_quality_blocks_duplicate_business_key() -> None:
    frame = (
        _valid_frame()
        .iloc[[0, 0]]
        .copy()
    )

    report = build_station_quality_report(
        frame
    )

    assert (
        report[
            "duplicidades_chave_negocio"
        ]
        == 2
    )
    assert report["status"] == "failed"


def test_station_quality_does_not_merge_missing_cnpj_stations() -> None:
    frame = pd.DataFrame(
        {
            "data_coleta": [
                "2026-09-20",
                "2026-09-20",
            ],
            "uf": ["CE", "CE"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
            ],
            "revenda": [
                "POSTO A",
                "POSTO B",
            ],
            "produto": [
                "GASOLINA",
                "GASOLINA",
            ],
            "preco_revenda": [
                6.10,
                6.10,
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
            ],
            "cnpj_revenda": [
                pd.NA,
                pd.NA,
            ],
        }
    )

    report = build_station_quality_report(
        frame
    )

    assert (
        report[
            "duplicidades_chave_negocio"
        ]
        == 0
    )


def test_station_quality_blocks_date_outside_2026() -> None:
    frame = _valid_frame()
    frame.loc[
        0,
        "data_coleta",
    ] = "2025-12-31"

    report = build_station_quality_report(
        frame
    )

    assert report["datas_fora_2026"] == 1
    assert report["status"] == "failed"


def test_station_quality_fails_without_required_column() -> None:
    frame = _valid_frame().drop(
        columns=[
            "preco_revenda"
        ]
    )

    report = build_station_quality_report(
        frame
    )

    assert report["status"] == "failed"
    assert "preco_revenda" in report[
        "missing_required_columns"
    ]
