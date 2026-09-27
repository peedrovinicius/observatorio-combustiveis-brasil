from pathlib import Path

import pandas as pd
import pytest

from src.transform import (
    _prepare_workbook_outputs,
    detect_header_row,
    normalize_column,
    read_excel_sheet,
)


def _sample_workbook(path: Path) -> None:
    rows = [
        ["AGÊNCIA NACIONAL DO PETRÓLEO, GÁS NATURAL E BIOCOMBUSTÍVEIS", None, None, None],
        ["LEVANTAMENTO DE PREÇOS DE COMBUSTÍVEIS", None, None, None],
        [None, None, None, None],
        ["DATA INICIAL", "MUNICÍPIO", "PRODUTO", "PREÇO MÉDIO REVENDA"],
        ["20/09/2026", "FORTALEZA", "GASOLINA COMUM", "6,12"],
        ["20/09/2026", "FORTALEZA", "ETANOL HIDRATADO", "4,89"],
    ]

    pd.DataFrame(rows).to_excel(path, index=False, header=False, sheet_name="Municípios")


def test_normalize_column_removes_accents_and_maps_alias() -> None:
    assert normalize_column("PREÇO MÉDIO REVENDA") == "preco_medio_revenda"
    assert normalize_column("CNPJ da Revenda") == "cnpj_revenda"
    assert normalize_column("Município") == "municipio"


def test_detect_header_row_with_report_preamble(tmp_path: Path) -> None:
    path = tmp_path / "sample.xlsx"
    _sample_workbook(path)

    assert detect_header_row(path, "Municípios") == 3


def test_read_excel_sheet_normalizes_schema_and_types(tmp_path: Path) -> None:
    path = tmp_path / "sample.xlsx"
    _sample_workbook(path)

    frame = read_excel_sheet(path, "Municípios")

    assert list(frame["municipio"]) == ["FORTALEZA", "FORTALEZA"]
    assert list(frame["produto"]) == ["GASOLINA COMUM", "ETANOL HIDRATADO"]
    assert list(frame["preco_medio_revenda"]) == [6.12, 4.89]
    assert "fonte_arquivo" in frame.columns
    assert "fonte_planilha" in frame.columns



def test_read_excel_sheet_rejects_duplicate_normalized_columns(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "duplicate-columns.xlsx"
    )
    rows = [
        [
            "DATA INICIAL",
            "UF",
            "ESTADO SIGLA",
            "PRODUTO",
            "PREÇO MÉDIO REVENDA",
        ],
        [
            "20/09/2026",
            "CE",
            "CE",
            "GASOLINA",
            "6,10",
        ],
    ]
    pd.DataFrame(
        rows
    ).to_excel(
        path,
        index=False,
        header=False,
        sheet_name="Dados",
    )

    with pytest.raises(
        ValueError,
        match="Colunas duplicadas após normalização",
    ):
        read_excel_sheet(
            path,
            "Dados",
        )


def test_read_excel_sheet_preserves_fractional_station_count_for_quality(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "fractional-count.xlsx"
    )
    rows = [
        [
            "DATA INICIAL",
            "PRODUTO",
            "PREÇO MÉDIO REVENDA",
            "NÚMERO DE POSTOS PESQUISADOS",
        ],
        [
            "20/09/2026",
            "GASOLINA",
            "6,10",
            "1,5",
        ],
    ]
    pd.DataFrame(
        rows
    ).to_excel(
        path,
        index=False,
        header=False,
        sheet_name="Dados",
    )

    frame = read_excel_sheet(
        path,
        "Dados",
    )

    assert (
        frame.loc[
            0,
            "postos_pesquisados",
        ]
        == 1.5
    )



def test_prepare_workbook_propagates_duplicate_column_error(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "historico_semanal_brasil__duplicado.xlsx"
    )
    rows = [
        [
            "DATA INICIAL",
            "UF",
            "ESTADO SIGLA",
            "PRODUTO",
            "PREÇO MÉDIO REVENDA",
        ],
        [
            "20/09/2026",
            "CE",
            "CE",
            "GASOLINA",
            "6,10",
        ],
    ]
    pd.DataFrame(
        rows
    ).to_excel(
        path,
        index=False,
        header=False,
        sheet_name="Dados",
    )

    with pytest.raises(
        ValueError,
        match="Colunas duplicadas após normalização",
    ):
        _prepare_workbook_outputs(
            path
        )
