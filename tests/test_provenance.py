import hashlib
import json
from pathlib import Path

import pytest

from src.provenance import (
    verify_history_provenance,
    verify_open_data_provenance,
)


def _sha256(
    content: bytes,
) -> str:
    return hashlib.sha256(
        content
    ).hexdigest()


def _write_history_manifest(
    root: Path,
) -> None:
    records = []
    for scope in (
        "brasil",
        "regioes",
        "estados",
        "municipios_2026",
    ):
        content = (
            f"xlsx-{scope}"
        ).encode(
            "utf-8"
        )
        filename = (
            f"historico_semanal_{scope}__dados.xlsx"
        )
        (
            root
            / filename
        ).write_bytes(
            content
        )
        records.append(
            {
                "scope": scope,
                "filename": filename,
                "detected_format": "xlsx",
                "bytes": len(
                    content
                ),
                "sha256": _sha256(
                    content
                ),
            }
        )

    (
        root
        / "history_manifest.json"
    ).write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "files": records,
            }
        ),
        encoding="utf-8",
    )


def test_history_provenance_accepts_exact_snapshot(
    tmp_path: Path,
) -> None:
    _write_history_manifest(
        tmp_path
    )

    manifest = (
        verify_history_provenance(
            tmp_path
        )
    )

    assert (
        manifest[
            "manifest_version"
        ]
        == 1
    )


def test_history_provenance_rejects_modified_file(
    tmp_path: Path,
) -> None:
    _write_history_manifest(
        tmp_path
    )
    (
        tmp_path
        / "historico_semanal_brasil__dados.xlsx"
    ).write_bytes(
        b"alterado"
    )

    with pytest.raises(
        ValueError,
        match="divergente do manifesto",
    ):
        verify_history_provenance(
            tmp_path
        )


def test_history_provenance_rejects_unmanifested_file(
    tmp_path: Path,
) -> None:
    _write_history_manifest(
        tmp_path
    )
    (
        tmp_path
        / "historico_semanal_brasil__extra.xlsx"
    ).write_bytes(
        b"extra"
    )

    with pytest.raises(
        ValueError,
        match="não correspondem exatamente",
    ):
        verify_history_provenance(
            tmp_path
        )


def _write_open_manifest(
    root: Path,
) -> None:
    direct = (
        b"produto;preco\nGASOLINA;6,00\n"
    )
    direct_name = (
        "automotivos_2026_s1.csv"
    )
    (
        root
        / direct_name
    ).write_bytes(
        direct
    )

    extract_dir = (
        root
        / "etanol_gasolina_setembro_2026"
    )
    extract_dir.mkdir()
    extracted = (
        b"produto;preco\nETANOL;4,50\n"
    )
    extracted_path = (
        extract_dir
        / "dados.csv"
    )
    extracted_path.write_bytes(
        extracted
    )

    raw_zip = (
        b"PK\x03\x04raw-simulado"
    )
    raw_zip_name = (
        "etanol_gasolina_setembro_2026.zip"
    )
    (
        root
        / raw_zip_name
    ).write_bytes(
        raw_zip
    )

    (
        root
        / "manifest.json"
    ).write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "files": [
                    {
                        "dataset": (
                            "automotivos_2026_s1"
                        ),
                        "filename": direct_name,
                        "detected_format": "csv",
                        "bytes": len(
                            direct
                        ),
                        "sha256": _sha256(
                            direct
                        ),
                        "extracted_csvs": [],
                        "extracted_files": [],
                    },
                    {
                        "dataset": (
                            "etanol_gasolina_setembro_2026"
                        ),
                        "filename": raw_zip_name,
                        "detected_format": "zip",
                        "bytes": len(
                            raw_zip
                        ),
                        "sha256": _sha256(
                            raw_zip
                        ),
                        "extracted_csvs": [
                            (
                                "etanol_gasolina_setembro_2026/"
                                "dados.csv"
                            )
                        ],
                        "extracted_files": [
                            {
                                "path": (
                                    "etanol_gasolina_setembro_2026/"
                                    "dados.csv"
                                ),
                                "bytes": len(
                                    extracted
                                ),
                                "sha256": _sha256(
                                    extracted
                                ),
                            }
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_open_data_provenance_accepts_raw_and_extracted_files(
    tmp_path: Path,
) -> None:
    _write_open_manifest(
        tmp_path
    )

    manifest = (
        verify_open_data_provenance(
            tmp_path
        )
    )

    assert len(
        manifest[
            "files"
        ]
    ) == 2


def test_open_data_provenance_rejects_modified_extracted_csv(
    tmp_path: Path,
) -> None:
    _write_open_manifest(
        tmp_path
    )
    (
        tmp_path
        / "etanol_gasolina_setembro_2026"
        / "dados.csv"
    ).write_text(
        "alterado",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="divergente do manifesto",
    ):
        verify_open_data_provenance(
            tmp_path
        )


def test_open_data_provenance_rejects_unmanifested_csv(
    tmp_path: Path,
) -> None:
    _write_open_manifest(
        tmp_path
    )
    (
        tmp_path
        / "extra.csv"
    ).write_text(
        "produto;preco\nX;1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="não correspondem exatamente",
    ):
        verify_open_data_provenance(
            tmp_path
        )


def test_provenance_rejects_legacy_manifest_without_version(
    tmp_path: Path,
) -> None:
    (
        tmp_path
        / "history_manifest.json"
    ).write_text(
        '{"files":[]}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Versão de manifesto",
    ):
        verify_history_provenance(
            tmp_path
        )
