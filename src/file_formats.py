from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from urllib.parse import urlparse


class UnsupportedDownloadError(ValueError):
    pass


def _looks_like_html(content: bytes) -> bool:
    sample = content[:4096].lstrip().lower()
    return (
        sample.startswith(b"<!doctype html")
        or sample.startswith(b"<html")
        or b"<html" in sample[:512]
    )


def _zip_kind(content: bytes) -> str | None:
    if not content.startswith(b"PK"):
        return None

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return None

    if (
        "[Content_Types].xml" in names
        and any(
            name.startswith("xl/")
            for name in names
        )
    ):
        return "xlsx"

    return "zip"


def _looks_like_csv(content: bytes) -> bool:
    if not content or _looks_like_html(content):
        return False

    sample_bytes = content[:16384]
    for encoding in (
        "utf-8-sig",
        "utf-8",
        "latin-1",
    ):
        try:
            text = sample_bytes.decode(
                encoding
            )
        except UnicodeDecodeError:
            continue

        lines = [
            line
            for line in text.splitlines()
            if line.strip()
        ]
        if not lines:
            continue

        first = lines[0]
        if ";" not in first and "," not in first:
            continue

        try:
            dialect = csv.Sniffer().sniff(
                "\n".join(lines[:5]),
                delimiters=";,",
            )
            row = next(
                csv.reader(
                    [first],
                    dialect=dialect,
                )
            )
        except (csv.Error, StopIteration):
            continue

        if len(row) >= 2:
            return True

    return False


def detect_download_kind(
    content: bytes,
    final_url: str = "",
    content_type: str = "",
) -> str:
    if not content:
        raise UnsupportedDownloadError(
            "O arquivo recebido está vazio."
        )

    if _looks_like_html(content):
        raise UnsupportedDownloadError(
            "A resposta recebida é HTML, não um arquivo de dados."
        )

    zip_kind = _zip_kind(content)
    if zip_kind:
        return zip_kind

    if _looks_like_csv(content):
        return "csv"

    path = urlparse(final_url).path.lower()
    media_type = content_type.casefold()

    if path.endswith(".csv") or "csv" in media_type:
        raise UnsupportedDownloadError(
            "A resposta anuncia CSV, mas o conteúdo não parece ser CSV válido."
        )
    if (
        path.endswith((".xlsx", ".xls"))
        or "spreadsheet" in media_type
        or "excel" in media_type
    ):
        raise UnsupportedDownloadError(
            "A resposta anuncia planilha, mas o conteúdo não parece ser XLSX válido."
        )
    if path.endswith(".zip") or "zip" in media_type:
        raise UnsupportedDownloadError(
            "A resposta anuncia ZIP, mas o conteúdo não é um ZIP válido."
        )

    raise UnsupportedDownloadError(
        "Formato de arquivo não reconhecido."
    )


def extension_for_kind(kind: str) -> str:
    extensions = {
        "csv": ".csv",
        "zip": ".zip",
        "xlsx": ".xlsx",
    }
    try:
        return extensions[kind]
    except KeyError as exc:
        raise ValueError(
            f"Tipo de arquivo não suportado: {kind}"
        ) from exc


def safe_basename(
    url: str,
    fallback: str,
) -> str:
    name = Path(
        urlparse(url).path
    ).name
    return name or fallback
