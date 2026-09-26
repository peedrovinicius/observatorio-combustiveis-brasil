from pathlib import Path

import pytest

from src.load_postgres import (
    LOAD_PLAN,
    _read_csv_header,
    required_files,
    validate_csv_contracts,
    validate_input_files,
)


def test_load_plan_has_two_fact_tables() -> None:
    tables = [
        table
        for table, _ in LOAD_PLAN
    ]

    assert "fato_precos_semanais" in tables
    assert "fato_precos_postos" in tables


def test_required_files_matches_load_plan() -> None:
    assert required_files() == [
        path
        for _, path in LOAD_PLAN
    ]


def test_read_csv_header_supports_quoted_csv(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        '"coluna_a","coluna_b"\n1,2\n',
        encoding="utf-8",
    )

    assert _read_csv_header(path) == [
        "coluna_a",
        "coluna_b",
    ]


def test_validate_input_files_fails_when_models_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    fake_plan = [
        (
            "dim_data",
            tmp_path / "dim_data.csv",
        ),
        (
            "fato_precos_semanais",
            tmp_path / "fact.csv",
        ),
    ]
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        fake_plan,
    )

    with pytest.raises(
        FileNotFoundError
    ):
        validate_input_files()


def test_csv_contract_rejects_unknown_columns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_produto.csv"
    path.write_text(
        "produto_id,produto,coluna_extra\n1,GASOLINA,x\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_produto", path)],
    )

    with pytest.raises(
        ValueError,
        match="colunas não suportadas",
    ):
        validate_csv_contracts()


def test_csv_contract_rejects_missing_required_columns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_produto.csv"
    path.write_text(
        "produto_id\n1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_produto", path)],
    )

    with pytest.raises(
        ValueError,
        match="colunas obrigatórias ausentes",
    ):
        validate_csv_contracts()
