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



def test_station_quality_accepts_alphanumeric_cnpj() -> None:
    frame = _valid_frame()
    frame["cnpj_revenda"] = [
        "00.000.000/E08G-12",
        "00.000.000/E08G-12",
    ]

    report = build_station_quality_report(
        frame
    )

    assert report["cnpj_invalido"] == 0
    assert (
        report[
            "postos_distintos_cnpj"
        ]
        == 1
    )
    assert report["status"] == "passed"


def test_station_quality_blocks_invalid_cnpj_even_with_complete_fallback() -> None:
    frame = _valid_frame().iloc[[0]].copy()
    frame["cnpj_revenda"] = [
        "CNPJ INVALIDO"
    ]
    frame["logradouro"] = [
        "RUA A"
    ]
    frame["numero"] = [
        "10"
    ]

    report = build_station_quality_report(
        frame
    )

    assert report["cnpj_invalido"] == 1
    assert (
        report[
            "fallback_identidade_incompleta"
        ]
        == 0
    )
    assert report["status"] == "failed"


def test_station_quality_blocks_incomplete_fallback_without_cnpj() -> None:
    frame = _valid_frame().iloc[[0]].copy()
    frame["cnpj_revenda"] = [
        pd.NA
    ]
    frame["logradouro"] = [
        pd.NA
    ]
    frame["numero"] = [
        pd.NA
    ]

    report = build_station_quality_report(
        frame
    )

    assert (
        report[
            "fallback_identidade_incompleta"
        ]
        == 1
    )
    assert (
        report[
            "fallback_sem_logradouro"
        ]
        == 1
    )
    assert (
        report[
            "fallback_sem_numero"
        ]
        == 1
    )
    assert report["status"] == "failed"


def test_station_quality_accepts_complete_fallback_without_cnpj() -> None:
    frame = _valid_frame().iloc[[0]].copy()
    frame["cnpj_revenda"] = [
        pd.NA
    ]
    frame["logradouro"] = [
        "RUA A"
    ]
    frame["numero"] = [
        "10"
    ]

    report = build_station_quality_report(
        frame
    )

    assert report["cnpj_ausente"] == 1
    assert report["cnpj_invalido"] == 0
    assert (
        report[
            "fallback_identidade_incompleta"
        ]
        == 0
    )
    assert report["status"] == "passed"
