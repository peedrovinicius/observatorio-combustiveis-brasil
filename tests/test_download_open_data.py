from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from src.download_open_data import (
    _clear_dataset_artifacts,
    _discover_2026_links,
    _extract_csvs,
    _replace_dataset_artifacts,
    _replace_open_data_batch,
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



def test_invalid_zip_replacement_preserves_previous_dataset(
    tmp_path: Path,
) -> None:
    stem = (
        "etanol_gasolina_setembro_2026"
    )
    old_zip = (
        tmp_path
        / f"{stem}.zip"
    )
    old_extract = (
        tmp_path
        / stem
    )
    old_zip.write_bytes(
        b"versao-anterior"
    )
    old_extract.mkdir()
    old_csv = (
        old_extract
        / "dados.csv"
    )
    old_csv.write_text(
        "produto;preco\n"
        "GASOLINA;6,00\n",
        encoding="utf-8",
    )

    invalid = _zip_with_file(
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
        _replace_dataset_artifacts(
            tmp_path,
            stem,
            invalid,
            "zip",
        )

    assert (
        old_zip.read_bytes()
        == b"versao-anterior"
    )
    assert old_csv.exists()
    assert (
        "GASOLINA;6,00"
        in old_csv.read_text(
            encoding="utf-8",
        )
    )


def test_valid_zip_replacement_installs_only_new_dataset(
    tmp_path: Path,
) -> None:
    stem = (
        "etanol_gasolina_setembro_2026"
    )
    old_csv = (
        tmp_path
        / f"{stem}.csv"
    )
    old_zip = (
        tmp_path
        / f"{stem}.zip"
    )
    old_extract = (
        tmp_path
        / stem
    )
    unrelated = (
        tmp_path
        / "diesel_gnv_setembro_2026.csv"
    )

    old_csv.write_text(
        "antigo",
        encoding="utf-8",
    )
    old_zip.write_bytes(
        b"antigo"
    )
    old_extract.mkdir()
    (
        old_extract
        / "antigo.csv"
    ).write_text(
        "antigo",
        encoding="utf-8",
    )
    unrelated.write_text(
        "preservar",
        encoding="utf-8",
    )

    content = _zip_with_file(
        "dados_novos.csv",
        (
            b"produto;preco\n"
            b"GASOLINA;6,10\n"
        ),
    )

    raw_path, extracted = (
        _replace_dataset_artifacts(
            tmp_path,
            stem,
            content,
            "zip",
        )
    )

    assert raw_path == (
        tmp_path
        / f"{stem}.zip"
    )
    assert (
        raw_path.read_bytes()
        == content
    )
    assert not old_csv.exists()
    assert unrelated.exists()
    assert extracted == [
        tmp_path
        / stem
        / "dados_novos.csv"
    ]
    assert extracted[0].exists()
    assert not (
        tmp_path
        / stem
        / "antigo.csv"
    ).exists()


def test_direct_csv_replacement_removes_previous_zip_artifacts(
    tmp_path: Path,
) -> None:
    stem = (
        "diesel_gnv_setembro_2026"
    )
    old_zip = (
        tmp_path
        / f"{stem}.zip"
    )
    old_extract = (
        tmp_path
        / stem
    )
    old_zip.write_bytes(
        b"antigo"
    )
    old_extract.mkdir()
    (
        old_extract
        / "dados.csv"
    ).write_text(
        "antigo",
        encoding="utf-8",
    )

    content = (
        b"produto;preco\n"
        b"DIESEL S10;6,20\n"
    )

    raw_path, extracted = (
        _replace_dataset_artifacts(
            tmp_path,
            stem,
            content,
            "csv",
        )
    )

    assert raw_path == (
        tmp_path
        / f"{stem}.csv"
    )
    assert (
        raw_path.read_bytes()
        == content
    )
    assert extracted == []
    assert not old_zip.exists()
    assert not old_extract.exists()



def test_zip_rejects_case_insensitive_duplicate_names(
    tmp_path: Path,
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
    ) as archive:
        archive.writestr(
            "Dados.csv",
            (
                "produto;preco\n"
                "GASOLINA;6,00\n"
            ),
        )
        archive.writestr(
            "dados.csv",
            (
                "produto;preco\n"
                "ETANOL;4,50\n"
            ),
        )

    destination = (
        tmp_path
        / "extract"
    )
    destination.mkdir()

    with pytest.raises(
        ValueError,
        match="nome repetido",
    ):
        _extract_csvs(
            buffer.getvalue(),
            destination,
        )


def test_invalid_direct_csv_preserves_previous_dataset(
    tmp_path: Path,
) -> None:
    stem = (
        "diesel_gnv_outubro_2026"
    )
    old_csv = (
        tmp_path
        / f"{stem}.csv"
    )
    old_csv.write_text(
        "produto;preco\n"
        "DIESEL S10;6,20\n",
        encoding="utf-8",
    )

    invalid = (
        b"<!doctype html>"
        b"<html><body>erro</body></html>"
    )

    with pytest.raises(
        UnsupportedDownloadError,
        match="HTML",
    ):
        _replace_dataset_artifacts(
            tmp_path,
            stem,
            invalid,
            "csv",
        )

    assert (
        "DIESEL S10;6,20"
        in old_csv.read_text(
            encoding="utf-8",
        )
    )


def test_install_failure_restores_previous_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stem = (
        "etanol_gasolina_novembro_2026"
    )
    old_zip = (
        tmp_path
        / f"{stem}.zip"
    )
    old_extract = (
        tmp_path
        / stem
    )
    old_zip.write_bytes(
        b"versao-anterior"
    )
    old_extract.mkdir()
    old_csv = (
        old_extract
        / "dados.csv"
    )
    old_csv.write_text(
        "produto;preco\n"
        "GASOLINA;6,00\n",
        encoding="utf-8",
    )

    content = _zip_with_file(
        "dados_novos.csv",
        (
            b"produto;preco\n"
            b"GASOLINA;6,10\n"
        ),
    )

    import src.download_open_data as downloader

    original_move = (
        downloader.shutil.move
    )

    def failing_move(
        source: str,
        destination: str,
    ):
        source_path = Path(
            source
        )
        destination_path = Path(
            destination
        )
        if (
            source_path.name
            == stem
            and source_path.parent.name.startswith(
                ".dataset_stage_"
            )
            and destination_path
            == tmp_path / stem
        ):
            raise OSError(
                "falha simulada"
            )
        return original_move(
            source,
            destination,
        )

    monkeypatch.setattr(
        downloader.shutil,
        "move",
        failing_move,
    )

    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        _replace_dataset_artifacts(
            tmp_path,
            stem,
            content,
            "zip",
        )

    assert (
        old_zip.read_bytes()
        == b"versao-anterior"
    )
    assert old_csv.exists()
    assert (
        "GASOLINA;6,00"
        in old_csv.read_text(
            encoding="utf-8",
        )
    )
    assert not (
        old_extract
        / "dados_novos.csv"
    ).exists()



def test_discovery_rejects_missing_2026_family() -> None:
    html = """
    <h3>Combustíveis automotivos</h3>
    <a href="s1.csv">1º semestre de 2026</a>
    <h3>Óleo Diesel (S-500 e S-10) + GNV</h3>
    <a href="diesel.csv">Setembro 2026</a>
    """

    with pytest.raises(
        RuntimeError,
        match="Famílias ausentes",
    ):
        _discover_2026_links(
            html
        )


def test_discovery_rejects_duplicate_logical_dataset() -> None:
    html = """
    <h3>Combustíveis automotivos</h3>
    <a href="s1.csv">1º semestre de 2026</a>
    <h3>Óleo Diesel (S-500 e S-10) + GNV</h3>
    <a href="diesel-a.csv">Setembro 2026</a>
    <a href="diesel-b.csv">Setembro 2026</a>
    <h3>Etanol hidratado + gasolina C</h3>
    <a href="etanol.csv">Setembro 2026</a>
    """

    with pytest.raises(
        RuntimeError,
        match="dataset lógico",
    ):
        _discover_2026_links(
            html
        )


def _batch_item(
    stem: str,
    value: str,
) -> dict[str, object]:
    content = (
        "produto;preco\n"
        f"{value};6,00\n"
    ).encode(
        "utf-8"
    )
    return {
        "stem": stem,
        "content": content,
        "kind": "csv",
        "record": {
            "dataset": stem,
            "url": (
                "https://example.test/"
                + stem
            ),
            "sha256": "teste",
        },
    }


def test_open_data_batch_replaces_datasets_and_manifest_together(
    tmp_path: Path,
) -> None:
    old_a = tmp_path / "a.csv"
    old_b = tmp_path / "b.csv"
    manifest = tmp_path / "manifest.json"
    old_a.write_text(
        "antigo-a",
        encoding="utf-8",
    )
    old_b.write_text(
        "antigo-b",
        encoding="utf-8",
    )
    manifest.write_text(
        '{"versao":"antiga"}',
        encoding="utf-8",
    )

    records = _replace_open_data_batch(
        tmp_path,
        [
            _batch_item(
                "a",
                "NOVO A",
            ),
            _batch_item(
                "b",
                "NOVO B",
            ),
        ],
        {
            "source": "ANP",
            "collected_at_utc": (
                "2026-09-27T20:00:00+00:00"
            ),
        },
    )

    assert len(records) == 2
    assert "NOVO A" in (
        tmp_path
        / "a.csv"
    ).read_text(
        encoding="utf-8",
    )
    assert "NOVO B" in (
        tmp_path
        / "b.csv"
    ).read_text(
        encoding="utf-8",
    )
    saved_manifest = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )
    assert len(
        saved_manifest[
            "files"
        ]
    ) == 2


def test_open_data_batch_install_failure_restores_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.download_open_data as downloader

    old_a = tmp_path / "a.csv"
    old_b = tmp_path / "b.csv"
    manifest = tmp_path / "manifest.json"
    old_a.write_text(
        "antigo-a",
        encoding="utf-8",
    )
    old_b.write_text(
        "antigo-b",
        encoding="utf-8",
    )
    manifest.write_text(
        '{"versao":"antiga"}',
        encoding="utf-8",
    )

    original_move = (
        downloader.shutil.move
    )

    def failing_move(
        source: str,
        destination: str,
    ):
        source_path = Path(
            source
        )
        destination_path = Path(
            destination
        )
        if (
            source_path.name
            == "b.csv"
            and destination_path
            == tmp_path / "b.csv"
            and "stage"
            in source_path.parts
        ):
            raise OSError(
                "falha simulada"
            )
        return original_move(
            source,
            destination,
        )

    monkeypatch.setattr(
        downloader.shutil,
        "move",
        failing_move,
    )

    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        _replace_open_data_batch(
            tmp_path,
            [
                _batch_item(
                    "a",
                    "NOVO A",
                ),
                _batch_item(
                    "b",
                    "NOVO B",
                ),
            ],
            {
                "source": "ANP",
            },
        )

    assert (
        old_a.read_text(
            encoding="utf-8",
        )
        == "antigo-a"
    )
    assert (
        old_b.read_text(
            encoding="utf-8",
        )
        == "antigo-b"
    )
    assert (
        manifest.read_text(
            encoding="utf-8",
        )
        == '{"versao":"antiga"}'
    )
