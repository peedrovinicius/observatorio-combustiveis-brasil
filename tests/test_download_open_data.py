from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from src.download_open_data import (
    _clear_dataset_artifacts,
    _extract_csvs,
)
from src.file_formats import (
    UnsupportedDownloadError,
)


def _zip_with_file(
    name: str,
    content: bytes,
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
    ) as archive:
        archive.writestr(
            name,
            content,
        )
    return buffer.getvalue()


def test_dataset_cleanup_removes_only_owned_artifacts(
    tmp_path: Path,
) -> None:
    stem = (
        "etanol_gasolina_agosto_2026"
    )
    csv_path = (
        tmp_path
        / f"{stem}.csv"
    )
    zip_path = (
        tmp_path
        / f"{stem}.zip"
    )
    extract_dir = (
        tmp_path
        / stem
    )
    unrelated = (
        tmp_path
        / "diesel_gnv_agosto_2026.csv"
    )

    csv_path.write_text(
        "antigo",
        encoding="utf-8",
    )
    zip_path.write_bytes(
        b"antigo"
    )
    extract_dir.mkdir()
    (
        extract_dir
        / "stale.csv"
    ).write_text(
        "antigo",
        encoding="utf-8",
    )
    unrelated.write_text(
        "preservar",
        encoding="utf-8",
    )

    _clear_dataset_artifacts(
        tmp_path,
        stem,
    )

    assert not csv_path.exists()
    assert not zip_path.exists()
    assert not extract_dir.exists()
    assert unrelated.exists()


def test_zip_extraction_validates_inner_csv_content(
    tmp_path: Path,
) -> None:
    destination = (
        tmp_path
        / "extract"
    )
    destination.mkdir()
    content = _zip_with_file(
        "dados.csv",
        (
            b"<!doctype html>"
            b"<html><body>erro</body></html>"
        ),
    )

    with pytest.raises(
        UnsupportedDownloadError,
        match="HTML",
    ):
        _extract_csvs(
            content,
            destination,
        )

    assert not (
        destination
        / "dados.csv"
    ).exists()
