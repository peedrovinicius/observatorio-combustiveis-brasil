from pathlib import Path

import pytest

from src.load_postgres import (
    LOAD_PLAN,
    _finalize_model_constraints,
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



def test_dim_posto_contract_requires_station_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_posto.csv"
    path.write_text(
        "posto_id,uf,municipio\n"
        "1,CE,FORTALEZA\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [
            (
                "dim_posto",
                path,
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="posto_chave",
    ):
        validate_csv_contracts()



class _RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(
        self,
        statement: str,
    ) -> None:
        self.statements.append(
            statement
        )


def test_finalize_model_constraints_protects_fact_grains() -> None:
    connection = (
        _RecordingConnection()
    )

    _finalize_model_constraints(
        connection
    )

    sql = "\n".join(
        connection.statements
    )

    assert (
        "ux_fato_precos_semanais_grain"
        in sql
    )
    assert (
        "COALESCE(unidade_medida, '')"
        in sql
    )
    assert (
        "ux_fato_precos_postos_grain"
        in sql
    )
    assert (
        "data_coleta_id, produto_posto_id, posto_id"
        in sql
    )


def test_station_schema_declares_unique_fact_grain() -> None:
    from src.config import (
        PROJECT_ROOT,
    )

    schema = (
        PROJECT_ROOT
        / "sql"
        / "station_schema.sql"
    ).read_text(
        encoding="utf-8",
    )

    assert (
        "UNIQUE (\n"
        "        data_coleta_id,\n"
        "        produto_posto_id,\n"
        "        posto_id\n"
        "    )"
        in schema
    )



def test_finalize_model_constraints_protects_dimension_keys() -> None:
    connection = (
        _RecordingConnection()
    )

    _finalize_model_constraints(
        connection
    )

    sql = "\n".join(
        connection.statements
    )

    assert (
        "ALTER TABLE dim_produto_posto "
        "ALTER COLUMN unidade_medida "
        "SET NOT NULL"
        in sql
    )
    assert (
        "ux_dim_localidade_natural"
        in sql
    )
    assert (
        "COALESCE(regiao, '')"
        in sql
    )
    assert (
        "COALESCE(uf, '')"
        in sql
    )
    assert (
        "COALESCE(estado, '')"
        in sql
    )
    assert (
        "COALESCE(municipio, '')"
        in sql
    )
    assert (
        "ux_dim_produto_posto_natural"
        in sql
    )
    assert (
        "produto, COALESCE(unidade_medida, '')"
        in sql
    )


def test_station_product_dimension_requires_unit() -> None:
    from src.config import (
        PROJECT_ROOT,
    )

    schema = (
        PROJECT_ROOT
        / "sql"
        / "station_schema.sql"
    ).read_text(
        encoding="utf-8",
    )

    assert (
        "unidade_medida VARCHAR(40) NOT NULL"
        in schema
    )
