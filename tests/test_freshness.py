import os
from pathlib import Path

import pytest

from src.freshness import (
    validate_artifact_freshness,
)


def _write(
    path: Path,
    content: bytes = b"x",
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(
        content
    )
    return path


def test_freshness_accepts_artifacts_not_older_than_inputs(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "source.csv"
    )
    artifact = _write(
        tmp_path / "artifact.csv"
    )
    os.utime(
        source,
        (100, 100),
    )
    os.utime(
        artifact,
        (200, 200),
    )

    validate_artifact_freshness(
        [source],
        [artifact],
        "Teste",
    )


def test_freshness_rejects_stale_artifact(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "source.csv"
    )
    artifact = _write(
        tmp_path / "artifact.csv"
    )
    os.utime(
        source,
        (200, 200),
    )
    os.utime(
        artifact,
        (100, 100),
    )

    with pytest.raises(
        ValueError,
        match="Teste desatualizado",
    ):
        validate_artifact_freshness(
            [source],
            [artifact],
            "Teste",
            "Reexecute a etapa.",
        )


def test_freshness_rejects_missing_path(
    tmp_path: Path,
) -> None:
    artifact = _write(
        tmp_path / "artifact.csv"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Arquivos ausentes",
    ):
        validate_artifact_freshness(
            [
                tmp_path
                / "missing.csv"
            ],
            [artifact],
            "Teste",
        )


def test_freshness_rejects_empty_file(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "source.csv"
    )
    artifact = _write(
        tmp_path / "artifact.csv",
        b"",
    )

    with pytest.raises(
        ValueError,
        match="Arquivos vazios",
    ):
        validate_artifact_freshness(
            [source],
            [artifact],
            "Teste",
        )


def test_freshness_rejects_empty_contract(
    tmp_path: Path,
) -> None:
    artifact = _write(
        tmp_path / "artifact.csv"
    )

    with pytest.raises(
        ValueError,
        match="lista de entradas vazia",
    ):
        validate_artifact_freshness(
            [],
            [artifact],
            "Teste",
        )
