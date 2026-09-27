from __future__ import annotations

import io
import zipfile

import pytest

from src.file_formats import (
    UnsupportedDownloadError,
    detect_download_kind,
    extension_for_kind,
)


def _xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
    ) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "<Types></Types>",
        )
        archive.writestr(
            "xl/workbook.xml",
            "<workbook></workbook>",
        )
    return buffer.getvalue()


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
    ) as archive:
        archive.writestr(
            "dados.csv",
            "UF;Produto\nCE;GASOLINA\n",
        )
    return buffer.getvalue()


def test_detects_xlsx_from_bytes_with_generic_content_type() -> None:
    kind = detect_download_kind(
        _xlsx_bytes(),
        "https://exemplo/@@download/file",
        "application/octet-stream",
    )

    assert kind == "xlsx"
    assert extension_for_kind(
        kind
    ) == ".xlsx"


def test_detects_zip_from_magic_bytes() -> None:
    kind = detect_download_kind(
        _zip_bytes(),
        "https://exemplo/download",
        "application/octet-stream",
    )

    assert kind == "zip"


def test_detects_semicolon_csv_without_helpful_headers() -> None:
    content = (
        "UF;Municipio;Produto;Valor\n"
        "CE;Fortaleza;Gasolina;6,10\n"
    ).encode("utf-8")

    kind = detect_download_kind(
        content,
        "https://exemplo/download",
        "application/octet-stream",
    )

    assert kind == "csv"


def test_rejects_html_even_if_url_looks_like_xlsx() -> None:
    with pytest.raises(
        UnsupportedDownloadError,
        match="HTML",
    ):
        detect_download_kind(
            b"<!doctype html><html><body>erro</body></html>",
            "https://exemplo/dados.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def test_rejects_invalid_zip_payload() -> None:
    with pytest.raises(
        UnsupportedDownloadError,
        match="ZIP",
    ):
        detect_download_kind(
            b"conteudo-invalido",
            "https://exemplo/dados.zip",
            "application/zip",
        )



def test_rejects_bom_prefixed_html_with_csv_delimiter() -> None:
    content = (
        b"\xef\xbb\xbf"
        b"<!doctype html><body>erro;temporario</body>"
    )

    with pytest.raises(
        UnsupportedDownloadError,
        match="HTML",
    ):
        detect_download_kind(
            content,
            "https://exemplo/dados.csv",
            "text/csv",
        )
