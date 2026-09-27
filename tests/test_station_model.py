import pandas as pd
import pytest

from src.build_station_model import (
    build_validated_station_model,
)
from src.load_postgres import (
    REQUIRED_TABLE_COLUMNS,
    TABLE_COLUMNS,
)


def _valid_station_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_coleta": pd.to_datetime(
                [
                    "2026-09-20",
                    "2026-09-20",
                ]
            ),
            "uf": [
                "CE",
                "CE",
            ],
            "municipio": [
                "FORTALEZA",
                "CAUCAIA",
            ],
            "revenda": [
                "POSTO A",
                "POSTO B",
            ],
            "cnpj_revenda": [
                "00.000.001/0001-36",
                "00.000.002/0001-80",
            ],
            "produto": [
                "GASOLINA",
                "GASOLINA",
            ],
            "preco_revenda": [
                6.10,
                6.20,
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
            ],
            "fonte_arquivo": [
                "x.csv",
                "x.csv",
            ],
        }
    )


def test_validated_station_model_accepts_clean_data() -> None:
    tables = (
        build_validated_station_model(
            _valid_station_frame()
        )
    )

    assert (
        len(
            tables[
                "fato_precos_postos"
            ]
        )
        == 2
    )
    assert (
        tables[
            "dim_posto"
        ]["posto_chave"]
        .is_unique
    )


def test_validated_station_model_blocks_invalid_data() -> None:
    frame = _valid_station_frame()
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
        build_validated_station_model(
            frame
        )


def test_validated_station_model_blocks_duplicate_business_key() -> None:
    frame = _valid_station_frame()
    duplicate = frame.iloc[
        [0]
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
        build_validated_station_model(
            frame
        )


def test_validated_station_model_requires_source_provenance() -> None:
    frame = _valid_station_frame().drop(
        columns=[
            "fonte_arquivo"
        ]
    )

    with pytest.raises(
        ValueError,
        match="fonte_arquivo",
    ):
        build_validated_station_model(
            frame
        )


def test_station_model_headers_match_postgres_contract() -> None:
    tables = build_validated_station_model(
        _valid_station_frame()
    )

    for table, frame in tables.items():
        columns = set(frame.columns)
        assert columns <= TABLE_COLUMNS[table]
        assert (
            REQUIRED_TABLE_COLUMNS[table]
            <= columns
        )
