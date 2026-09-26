import pandas as pd
import pytest

from src.build_station_model import (
    build_validated_station_model,
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
                "00.000.000/0001-00",
                "00.000.000/0002-00",
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
