import hashlib
import json
from pathlib import Path

import pytest

from src.config import (
    ANP_HISTORICAL_PAGE,
    ANP_OPEN_DATA_PAGE,
)
from src.provenance import (
    verified_history_files,
    verify_history_provenance,
    verify_history_transform_provenance,
    verify_open_data_provenance,
    verify_station_transform_provenance,
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
                "source_page": ANP_HISTORICAL_PAGE,
                "discovered_url": (
                    "https://www.gov.br/anp/"
                    f"{scope}.xlsx"
                ),
                "final_url": (
                    "https://www.gov.br/anp/"
                    f"{scope}.xlsx"
                ),
                "collected_at_utc": (
                    "2026-09-27T20:00:00+00:00"
                ),
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
                "source": "ANP",
                "source_page": ANP_HISTORICAL_PAGE,
                "collected_at_utc": "2026-09-27T20:00:00+00:00",
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

    diesel = (
        b"produto;preco\nDIESEL S10;6,20\n"
    )
    diesel_name = (
        "diesel_gnv_setembro_2026.csv"
    )
    (
        root
        / diesel_name
    ).write_bytes(
        diesel
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
                "source": "ANP",
                "source_page": ANP_OPEN_DATA_PAGE,
                "collected_at_utc": "2026-09-27T20:00:00+00:00",
                "files": [
                    {
                        "dataset": (
                            "automotivos_2026_s1"
                        ),
                        "url": (
                            "https://www.gov.br/anp/"
                            "automotivos.csv"
                        ),
                        "final_url": (
                            "https://www.gov.br/anp/"
                            "automotivos.csv"
                        ),
                        "collected_at_utc": (
                            "2026-09-27T20:00:00+00:00"
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
                            "diesel_gnv_setembro_2026"
                        ),
                        "url": (
                            "https://www.gov.br/anp/"
                            "diesel.csv"
                        ),
                        "final_url": (
                            "https://www.gov.br/anp/"
                            "diesel.csv"
                        ),
                        "collected_at_utc": (
                            "2026-09-27T20:00:00+00:00"
                        ),
                        "filename": diesel_name,
                        "detected_format": "csv",
                        "bytes": len(
                            diesel
                        ),
                        "sha256": _sha256(
                            diesel
                        ),
                        "extracted_csvs": [],
                        "extracted_files": [],
                    },
                    {
                        "dataset": (
                            "etanol_gasolina_setembro_2026"
                        ),
                        "url": (
                            "https://www.gov.br/anp/"
                            "etanol.zip"
                        ),
                        "final_url": (
                            "https://www.gov.br/anp/"
                            "etanol.zip"
                        ),
                        "collected_at_utc": (
                            "2026-09-27T20:00:00+00:00"
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
    ) == 3


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



def test_open_data_provenance_rejects_raw_name_dataset_mismatch(
    tmp_path: Path,
) -> None:
    _write_open_manifest(
        tmp_path
    )
    manifest_path = (
        tmp_path
        / "manifest.json"
    )
    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )
    manifest["files"][0][
        "dataset"
    ] = "outro_dataset"
    manifest_path.write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="dataset lógico",
    ):
        verify_open_data_provenance(
            tmp_path
        )


def test_open_data_provenance_rejects_extra_raw_archive(
    tmp_path: Path,
) -> None:
    _write_open_manifest(
        tmp_path
    )
    (
        tmp_path
        / "arquivo_extra.zip"
    ).write_bytes(
        b"extra"
    )

    with pytest.raises(
        ValueError,
        match="Arquivos raw locais",
    ):
        verify_open_data_provenance(
            tmp_path
        )


def test_open_data_provenance_accepts_windows_legacy_separator(
    tmp_path: Path,
) -> None:
    _write_open_manifest(
        tmp_path
    )
    manifest_path = (
        tmp_path
        / "manifest.json"
    )
    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )
    manifest["files"][2][
        "extracted_csvs"
    ] = [
        (
            "etanol_gasolina_setembro_2026"
            "\\dados.csv"
        )
    ]
    manifest_path.write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    verify_open_data_provenance(
        tmp_path
    )



def test_provenance_rejects_non_utc_timestamp(
    tmp_path: Path,
) -> None:
    _write_history_manifest(
        tmp_path
    )
    manifest_path = (
        tmp_path
        / "history_manifest.json"
    )
    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )
    manifest[
        "collected_at_utc"
    ] = "2026-09-27T17:00:00-03:00"
    manifest_path.write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="deve estar em UTC",
    ):
        verify_history_provenance(
            tmp_path
        )



def test_verified_history_files_returns_only_manifested_snapshot(
    tmp_path: Path,
) -> None:
    _write_history_manifest(
        tmp_path
    )
    unrelated = (
        tmp_path
        / "arquivo_extra.xlsx"
    )
    unrelated.write_bytes(
        b"nao-usar"
    )

    files = (
        verified_history_files(
            tmp_path
        )
    )

    assert len(files) == 4
    assert unrelated not in files
    assert all(
        path.name.startswith(
            "historico_semanal_"
        )
        for path in files
    )



def test_history_provenance_rejects_record_timestamp_mismatch(
    tmp_path: Path,
) -> None:
    _write_history_manifest(
        tmp_path
    )
    manifest_path = (
        tmp_path
        / "history_manifest.json"
    )
    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )
    manifest["files"][0][
        "collected_at_utc"
    ] = "2026-09-27T20:01:00+00:00"
    manifest_path.write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Timestamp do arquivo histórico",
    ):
        verify_history_provenance(
            tmp_path
        )



def test_open_data_provenance_rejects_missing_family(
    tmp_path: Path,
) -> None:
    _write_open_manifest(
        tmp_path
    )
    manifest_path = (
        tmp_path
        / "manifest.json"
    )
    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )
    manifest["files"] = [
        item
        for item in manifest[
            "files"
        ]
        if not str(
            item["dataset"]
        ).startswith(
            "diesel_gnv_"
        )
    ]
    (
        tmp_path
        / "diesel_gnv_setembro_2026.csv"
    ).unlink()
    manifest_path.write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Famílias ausentes",
    ):
        verify_open_data_provenance(
            tmp_path
        )



def _write_history_transform_manifest(
    raw_root: Path,
    processed_root: Path,
) -> None:
    raw_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    processed_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    _write_history_manifest(
        raw_root
    )

    records = []
    for scope in (
        "brasil",
        "regioes",
        "estados",
        "municipios_2026",
    ):
        content = (
            "data_inicial,produto,preco_medio_revenda\n"
            "2026-01-04,GASOLINA,6.0\n"
        ).encode(
            "utf-8"
        )
        filename = (
            f"historico_semanal_{scope}"
            "__dados__dados.csv"
        )
        (
            processed_root
            / filename
        ).write_bytes(
            content
        )
        records.append(
            {
                "scope": scope,
                "filename": filename,
                "source_file": (
                    f"historico_semanal_{scope}"
                    "__dados.xlsx"
                ),
                "source_sheet": "Dados",
                "rows": 1,
                "columns": 3,
                "bytes": len(
                    content
                ),
                "sha256": _sha256(
                    content
                ),
            }
        )

    source_manifest = (
        raw_root
        / "history_manifest.json"
    )
    (
        processed_root
        / "history_transform_manifest.json"
    ).write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "source_manifest": (
                    "history_manifest.json"
                ),
                "source_manifest_sha256": _sha256(
                    source_manifest.read_bytes()
                ),
                "files": records,
            }
        ),
        encoding="utf-8",
    )


def test_history_transform_provenance_accepts_exact_snapshot(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    _write_history_transform_manifest(
        raw,
        processed,
    )

    files = (
        verify_history_transform_provenance(
            processed,
            raw,
        )
    )

    assert len(files) == 4


def test_history_transform_provenance_rejects_modified_csv(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    _write_history_transform_manifest(
        raw,
        processed,
    )
    (
        processed
        / "historico_semanal_brasil__dados__dados.csv"
    ).write_text(
        "alterado",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="divergente do manifesto",
    ):
        verify_history_transform_provenance(
            processed,
            raw,
        )


def test_history_transform_provenance_rejects_changed_raw_manifest(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    _write_history_transform_manifest(
        raw,
        processed,
    )
    raw_manifest = (
        raw
        / "history_manifest.json"
    )
    raw_manifest.write_text(
        raw_manifest.read_text(
            encoding="utf-8",
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Manifesto raw atual diverge",
    ):
        verify_history_transform_provenance(
            processed,
            raw,
        )


def test_history_transform_provenance_rejects_extra_history_csv(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    _write_history_transform_manifest(
        raw,
        processed,
    )
    (
        processed
        / "historico_semanal_brasil__extra.csv"
    ).write_text(
        "x",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="não correspondem exatamente",
    ):
        verify_history_transform_provenance(
            processed,
            raw,
        )



def _write_station_transform_manifest(
    raw_root: Path,
    processed_root: Path,
    reports_root: Path,
) -> None:
    raw_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    processed_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    reports_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    _write_open_manifest(
        raw_root
    )

    station = (
        b"data_coleta,uf,municipio,produto,"
        b"preco_revenda,unidade_medida,fonte_arquivo\n"
        b"2026-09-20,CE,FORTALEZA,GASOLINA,"
        b"6.10,R$ / litro,dados.csv\n"
    )
    station_path = (
        processed_root
        / "precos_postos_2026.csv"
    )
    station_path.write_bytes(
        station
    )

    audit = {
        "status": "passed",
        "linhas_finais": 1,
    }
    audit_path = (
        reports_root
        / "station_ingestion_audit_2026.json"
    )
    audit_path.write_text(
        json.dumps(
            audit
        ),
        encoding="utf-8",
    )

    raw_manifest = (
        raw_root
        / "manifest.json"
    )
    manifest = {
        "manifest_version": 1,
        "source_manifest": "manifest.json",
        "source_manifest_sha256": _sha256(
            raw_manifest.read_bytes()
        ),
        "files": [
            {
                "role": "station_data",
                "filename": station_path.name,
                "rows": 1,
                "columns": 7,
                "bytes": station_path.stat().st_size,
                "sha256": _sha256(
                    station_path.read_bytes()
                ),
            },
            {
                "role": "ingestion_audit",
                "filename": audit_path.name,
                "bytes": audit_path.stat().st_size,
                "sha256": _sha256(
                    audit_path.read_bytes()
                ),
            },
        ],
    }
    (
        processed_root
        / "station_transform_manifest.json"
    ).write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )


def test_station_transform_provenance_accepts_exact_bundle(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    _write_station_transform_manifest(
        raw,
        processed,
        reports,
    )

    result = (
        verify_station_transform_provenance(
            processed,
            raw,
            reports,
        )
    )

    assert (
        result["station_data"].name
        == "precos_postos_2026.csv"
    )


def test_station_transform_provenance_rejects_modified_csv(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    _write_station_transform_manifest(
        raw,
        processed,
        reports,
    )
    (
        processed
        / "precos_postos_2026.csv"
    ).write_text(
        "alterado",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="divergente do manifesto",
    ):
        verify_station_transform_provenance(
            processed,
            raw,
            reports,
        )


def test_station_transform_provenance_rejects_modified_audit(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    _write_station_transform_manifest(
        raw,
        processed,
        reports,
    )
    (
        reports
        / "station_ingestion_audit_2026.json"
    ).write_text(
        '{"linhas_finais":999}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="divergente do manifesto",
    ):
        verify_station_transform_provenance(
            processed,
            raw,
            reports,
        )


def test_station_transform_provenance_rejects_changed_raw_manifest(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    _write_station_transform_manifest(
        raw,
        processed,
        reports,
    )
    raw_manifest = (
        raw
        / "manifest.json"
    )
    raw_manifest.write_text(
        raw_manifest.read_text(
            encoding="utf-8"
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Manifesto raw por posto atual diverge",
    ):
        verify_station_transform_provenance(
            processed,
            raw,
            reports,
        )
