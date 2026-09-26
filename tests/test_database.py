from pathlib import Path

import pytest

from src.load_postgres import LOAD_PLAN, required_files, validate_input_files


def test_load_plan_has_two_fact_tables() -> None:
    tables = [table for table, _ in LOAD_PLAN]

    assert "fato_precos_semanais" in tables
    assert "fato_precos_postos" in tables


def test_required_files_matches_load_plan() -> None:
    assert required_files() == [
        path for _, path in LOAD_PLAN
    ]


def test_validate_input_files_fails_when_models_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    fake_plan = [
        ("dim_data", tmp_path / "dim_data.csv"),
        ("fato_precos_semanais", tmp_path / "fact.csv"),
    ]
    monkeypatch.setattr(loader, "LOAD_PLAN", fake_plan)

    with pytest.raises(FileNotFoundError):
        validate_input_files()
