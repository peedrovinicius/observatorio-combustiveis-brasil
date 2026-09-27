import pandas as pd
import pytest

from src.build_model import (
    build_star_schema,
    build_validated_star_schema,
)
from src.load_postgres import (
    REQUIRED_TABLE_COLUMNS,
    TABLE_COLUMNS,
)


def test_star_schema_builds_dimensions_and_fact() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
                "2026-01-04",
                "2026-01-11",
            ],
            "data_final": [
                "2026-01-10",
                "2026-01-10",
                "2026-01-17",
            ],
            "nivel_geografico": [
                "municipio",
                "municipio",
                "municipio",
            ],
            "regiao": ["NORDESTE", "NORDESTE", "NORDESTE"],
            "uf": ["CE", "CE", "CE"],
            "estado": ["CEARA", "CEARA", "CEARA"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "produto": [
                "GASOLINA",
                "ETANOL",
                "GASOLINA",
            ],
            "preco_medio_revenda": [6.0, 4.5, 6.1],
            "unidade_medida": ["R$/L", "R$/L", "R$/L"],
            "fonte_arquivo": [
                "historico.xlsx",
                "historico.xlsx",
                "historico.xlsx",
            ],
            "fonte_planilha": [
                "Dados",
                "Dados",
                "Dados",
            ],
        }
    )

    tables = build_star_schema(frame)

    assert len(tables["dim_data"]) == 2
    assert len(tables["dim_produto"]) == 2
    assert len(tables["dim_localidade"]) == 1
    assert len(tables["fato_precos_semanais"]) == 3

    fact = tables["fato_precos_semanais"]
    assert fact["data_id"].notna().all()
    assert fact["produto_id"].notna().all()
    assert fact["localidade_id"].notna().all()



def test_validated_star_schema_blocks_invalid_aggregate_data() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                "brasil",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                0,
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match=(
            "falhou na validação "
            "de qualidade"
        ),
    ):
        build_validated_star_schema(
            frame
        )


def test_validated_star_schema_accepts_clean_aggregate_data() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                "brasil",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
            "fonte_arquivo": [
                "historico.xlsx",
            ],
            "fonte_planilha": [
                "Dados",
            ],
        }
    )

    tables = (
        build_validated_star_schema(
            frame
        )
    )

    assert (
        len(
            tables[
                "fato_precos_semanais"
            ]
        )
        == 1
    )



def test_validated_star_schema_blocks_municipality_without_state_context() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                "municipio",
            ],
            "municipio": [
                "FORTALEZA",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
            "fonte_arquivo": [
                "historico.xlsx",
            ],
            "fonte_planilha": [
                "Dados",
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match=(
            "falhou na validação "
            "de qualidade"
        ),
    ):
        build_validated_star_schema(
            frame
        )


def test_aggregate_model_headers_match_postgres_contract() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                "brasil",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
            "fonte_arquivo": [
                "historico.xlsx",
            ],
            "fonte_planilha": [
                "Dados",
            ],
        }
    )

    tables = build_validated_star_schema(
        frame
    )

    for table, modeled in tables.items():
        columns = set(modeled.columns)
        assert columns <= TABLE_COLUMNS[table]
        assert (
            REQUIRED_TABLE_COLUMNS[table]
            <= columns
        )


def test_model_normalizes_geographic_level_and_uf_case() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                " Município ",
            ],
            "uf": [
                "ce",
            ],
            "municipio": [
                "FORTALEZA",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
            "fonte_arquivo": [
                "historico.xlsx",
            ],
            "fonte_planilha": [
                "Dados",
            ],
        }
    )

    tables = build_validated_star_schema(
        frame
    )
    locality = tables[
        "dim_localidade"
    ].iloc[0]

    assert (
        locality["nivel_geografico"]
        == "municipio"
    )
    assert locality["uf"] == "CE"


def test_validated_star_schema_blocks_impossible_aggregate_statistics() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                "brasil",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
            "fonte_arquivo": [
                "historico.xlsx",
            ],
            "fonte_planilha": [
                "Dados",
            ],
            "preco_minimo_revenda": [
                6.1,
            ],
            "preco_maximo_revenda": [
                6.5,
            ],
            "desvio_padrao_revenda": [
                -0.1,
            ],
            "postos_pesquisados": [
                3.5,
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="falhou na validação",
    ):
        build_validated_star_schema(
            frame
        )


def test_validated_star_schema_checks_single_published_price_bound() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                "brasil",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
            "fonte_arquivo": [
                "historico.xlsx",
            ],
            "fonte_planilha": [
                "Dados",
            ],
            "preco_minimo_revenda": [
                6.1,
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="falhou na validação",
    ):
        build_validated_star_schema(
            frame
        )


def test_validated_star_schema_requires_aggregate_provenance() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "nivel_geografico": [
                "brasil",
            ],
            "produto": [
                "GASOLINA",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="fonte_arquivo",
    ):
        build_validated_star_schema(
            frame
        )
