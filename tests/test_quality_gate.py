from pathlib import Path

import pytest

from src.quality_gate import (
    load_passed_quality_report,
)


def test_quality_gate_accepts_passed_report(
    tmp_path: Path,
) -> None:
    path = tmp_path / "quality.json"
    path.write_text(
        '{"status":"passed","rows":10}',
        encoding="utf-8",
    )

    report = load_passed_quality_report(
        path,
        "teste",
    )

    assert report["status"] == "passed"
    assert report["rows"] == 10


def test_quality_gate_rejects_missing_report(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Relatório de qualidade ausente",
    ):
        load_passed_quality_report(
            tmp_path / "missing.json",
            "teste",
        )


def test_quality_gate_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "quality.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Relatório de qualidade inválido",
    ):
        load_passed_quality_report(
            path,
            "teste",
        )


@pytest.mark.parametrize(
    "status",
    [
        "failed",
        "review",
        "",
    ],
)
def test_quality_gate_rejects_non_passed_status(
    tmp_path: Path,
    status: str,
) -> None:
    path = tmp_path / "quality.json"
    path.write_text(
        '{"status":"' + status + '"}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="não aprovado",
    ):
        load_passed_quality_report(
            path,
            "teste",
        )


def test_quality_gate_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "quality.json"
    path.write_text(
        '["passed"]',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="deve ser um objeto JSON",
    ):
        load_passed_quality_report(
            path,
            "teste",
        )
