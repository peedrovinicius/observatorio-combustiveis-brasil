from pathlib import Path

import pandas as pd

from src.transform import detect_header_row, normalize_column, read_excel_sheet


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
