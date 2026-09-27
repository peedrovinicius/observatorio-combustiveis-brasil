import re
from pathlib import Path

import pytest

from src.load_postgres import (
    LOAD_PLAN,
    TABLE_COLUMNS,
    _finalize_model_constraints,
    _read_csv_header,
    _split_sql_statements,
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
        "ALTER TABLE dim_posto "
        "ALTER COLUMN uf "
        "SET NOT NULL"
        in sql
    )
    assert (
        "ALTER TABLE dim_posto "
        "ALTER COLUMN municipio "
        "SET NOT NULL"
        in sql
    )
    assert (
        "ALTER TABLE fato_precos_postos "
        "ALTER COLUMN fonte_arquivo "
        "SET NOT NULL"
        in sql
    )
    assert (
        "ux_dim_posto_chave"
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



def test_sql_splitter_preserves_semicolons_inside_literals() -> None:
    script = (
        "SELECT 'a;b' AS texto;\n"
        'SELECT "col;una" FROM tabela;'
    )

    statements = (
        _split_sql_statements(
            script
        )
    )

    assert statements == [
        "SELECT 'a;b' AS texto",
        'SELECT "col;una" FROM tabela',
    ]


def test_sql_splitter_ignores_semicolons_in_comments() -> None:
    script = (
        "-- comentário ; interno\n"
        "SELECT 1;\n"
        "/* bloco ; comentário */\n"
        "SELECT 2;"
    )

    statements = (
        _split_sql_statements(
            script
        )
    )

    assert len(statements) == 2
    assert "SELECT 1" in statements[0]
    assert "SELECT 2" in statements[1]


def test_sql_splitter_preserves_postgres_dollar_block() -> None:
    script = (
        "DO $$\n"
        "BEGIN\n"
        "    PERFORM 1;\n"
        "    PERFORM 2;\n"
        "END\n"
        "$$;\n"
        "SELECT 3;"
    )

    statements = (
        _split_sql_statements(
            script
        )
    )

    assert len(statements) == 2
    assert "PERFORM 1;" in statements[0]
    assert "PERFORM 2;" in statements[0]
    assert statements[1] == "SELECT 3"


def test_sql_splitter_supports_tagged_dollar_quote() -> None:
    script = (
        "SELECT $texto$a;b$texto$;\n"
        "SELECT 2;"
    )

    assert (
        _split_sql_statements(
            script
        )
        == [
            "SELECT $texto$a;b$texto$",
            "SELECT 2",
        ]
    )


def test_sql_splitter_supports_nested_block_comments() -> None:
    script = (
        "/* externo ; "
        "/* interno ; */ "
        "fim */\n"
        "SELECT 1;"
    )

    statements = (
        _split_sql_statements(
            script
        )
    )

    assert len(statements) == 1
    assert "SELECT 1" in statements[0]


def test_sql_splitter_supports_escape_strings() -> None:
    script = (
        "SELECT E'abc\\\'def;ghi';\n"
        "SELECT 2;"
    )

    statements = (
        _split_sql_statements(
            script
        )
    )

    assert len(statements) == 2
    assert (
        "abc\\'def;ghi"
        in statements[0]
    )
    assert statements[1] == "SELECT 2"


def test_sql_splitter_drops_comment_only_tail() -> None:
    script = (
        "SELECT 1;\n"
        "-- comentário final ;"
    )

    assert (
        _split_sql_statements(
            script
        )
        == ["SELECT 1"]
    )



@pytest.mark.parametrize(
    "script",
    [
        "SELECT 'texto;",
        'SELECT "coluna;',
        "/* comentário sem fim",
        "DO $$ BEGIN PERFORM 1;",
    ],
)
def test_sql_splitter_rejects_unclosed_delimiters(
    script: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="delimitador não encerrado",
    ):
        _split_sql_statements(
            script
        )


def test_station_schema_defers_station_key_unique_index_until_after_cleanup() -> None:
    from src.config import PROJECT_ROOT

    schema = (
        PROJECT_ROOT
        / "sql"
        / "station_schema.sql"
    ).read_text(
        encoding="utf-8",
    )

    assert "ux_dim_posto_chave" not in schema


def test_station_sql_schema_columns_match_loader_contract() -> None:
    from src.config import PROJECT_ROOT

    schema = (
        PROJECT_ROOT
        / "sql"
        / "station_schema.sql"
    ).read_text(
        encoding="utf-8",
    )
    station_tables = (
        "dim_data_coleta",
        "dim_produto_posto",
        "dim_posto",
        "fato_precos_postos",
    )
    column_pattern = re.compile(
        r"^\s*([a-z_][a-z0-9_]*)\s+"
        r"(?:BIGINT|DATE|SMALLINT|VARCHAR|CHAR|NUMERIC|"
        r"INTEGER|TEXT|BOOLEAN)\b",
        re.MULTILINE,
    )

    for table in station_tables:
        block = re.search(
            rf"CREATE TABLE IF NOT EXISTS {table}\s*"
            r"\((.*?)\n\);",
            schema,
            re.DOTALL,
        )
        assert block is not None
        declared = set(
            column_pattern.findall(
                block.group(1)
            )
        )
        assert declared == TABLE_COLUMNS[table]


def test_station_schema_requires_station_geography_and_provenance() -> None:
    from src.config import PROJECT_ROOT

    schema = (
        PROJECT_ROOT
        / "sql"
        / "station_schema.sql"
    ).read_text(
        encoding="utf-8",
    )

    assert "uf CHAR(2) NOT NULL" in schema
    assert "municipio VARCHAR(160) NOT NULL" in schema
    assert "fonte_arquivo VARCHAR(255) NOT NULL" in schema


def test_station_csv_contract_rejects_invalid_station_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_posto.csv"
    path.write_text(
        "posto_id,posto_chave,uf,municipio\n"
        "1,hash-invalido,CE,FORTALEZA\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_posto", path)],
    )

    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        validate_csv_contracts()


def test_station_csv_contract_rejects_text_overflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_posto.csv"
    municipio = "A" * 161
    path.write_text(
        "posto_id,posto_chave,uf,municipio\n"
        f"1,{'a' * 64},CE,{municipio}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_posto", path)],
    )

    with pytest.raises(
        ValueError,
        match="160 caracteres",
    ):
        validate_csv_contracts()


def test_station_csv_contract_rejects_inconsistent_date_dimension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_data_coleta.csv"
    path.write_text(
        "data_coleta_id,data_coleta,ano,mes,semana_iso\n"
        "1,2026-09-20,2026,8,38\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_data_coleta", path)],
    )

    with pytest.raises(
        ValueError,
        match="incompatível com data_coleta",
    ):
        validate_csv_contracts()


def test_station_csv_contract_rejects_rounding_and_blank_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "fato_precos_postos.csv"
    path.write_text(
        "preco_posto_id,data_coleta_id,produto_posto_id,"
        "posto_id,preco_revenda,fonte_arquivo\n"
        "1,1,1,1,6.12345,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("fato_precos_postos", path)],
    )

    with pytest.raises(
        ValueError,
    ) as exc_info:
        validate_csv_contracts()

    message = str(exc_info.value)
    assert "fonte_arquivo" in message
    assert "arredondamento" in message


def _write_valid_station_contract_bundle(
    tmp_path: Path,
) -> list[tuple[str, Path]]:
    data = tmp_path / "dim_data_coleta.csv"
    product = tmp_path / "dim_produto_posto.csv"
    station = tmp_path / "dim_posto.csv"
    fact = tmp_path / "fato_precos_postos.csv"

    data.write_text(
        "data_coleta_id,data_coleta,ano,mes,semana_iso\n"
        "1,2026-09-20,2026,9,38\n",
        encoding="utf-8",
    )
    product.write_text(
        "produto_posto_id,produto,unidade_medida\n"
        "1,GASOLINA,R$ / litro\n",
        encoding="utf-8",
    )
    station.write_text(
        "posto_id,posto_chave,uf,municipio\n"
        f"1,{'a' * 64},CE,FORTALEZA\n",
        encoding="utf-8",
    )
    fact.write_text(
        "preco_posto_id,data_coleta_id,produto_posto_id,"
        "posto_id,preco_revenda,fonte_arquivo\n"
        "1,1,1,1,6.1234,postos.csv\n",
        encoding="utf-8",
    )

    return [
        ("dim_data_coleta", data),
        ("dim_produto_posto", product),
        ("dim_posto", station),
        ("fato_precos_postos", fact),
    ]


def test_station_relations_reject_missing_foreign_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    plan = _write_valid_station_contract_bundle(
        tmp_path
    )
    fact = dict(plan)[
        "fato_precos_postos"
    ]
    fact.write_text(
        "preco_posto_id,data_coleta_id,produto_posto_id,"
        "posto_id,preco_revenda,fonte_arquivo\n"
        "1,1,99,1,6.1234,postos.csv\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        plan,
    )

    with pytest.raises(
        ValueError,
        match="referência inexistente",
    ):
        validate_input_files()


def test_station_relations_reject_duplicate_fact_grain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    plan = _write_valid_station_contract_bundle(
        tmp_path
    )
    fact = dict(plan)[
        "fato_precos_postos"
    ]
    fact.write_text(
        "preco_posto_id,data_coleta_id,produto_posto_id,"
        "posto_id,preco_revenda,fonte_arquivo\n"
        "1,1,1,1,6.1234,postos.csv\n"
        "2,1,1,1,6.1200,postos.csv\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        plan,
    )

    with pytest.raises(
        ValueError,
        match="grão duplicado",
    ):
        validate_input_files()


def test_station_csv_contract_rejects_external_text_whitespace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_posto.csv"
    path.write_text(
        "posto_id,posto_chave,uf,municipio\n"
        f"1,{'a' * 64},CE, FORTALEZA\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_posto", path)],
    )

    with pytest.raises(
        ValueError,
        match="espaços externos",
    ):
        validate_csv_contracts()


def test_aggregate_csv_contract_rejects_text_overflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_produto.csv"
    path.write_text(
        "produto_id,produto\n"
        f"1,{'A' * 151}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_produto", path)],
    )

    with pytest.raises(
        ValueError,
        match="150 caracteres",
    ):
        validate_csv_contracts()


def test_aggregate_csv_contract_rejects_inconsistent_date_dimension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_data.csv"
    path.write_text(
        "data_id,data_inicial,data_final,ano,mes,"
        "semana_iso,trimestre\n"
        "1,2026-01-04,2026-01-10,2026,2,1,1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_data", path)],
    )

    with pytest.raises(
        ValueError,
        match="incompatível com data_inicial",
    ):
        validate_csv_contracts()


def test_aggregate_csv_contract_rejects_decimal_rounding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "fato_precos_semanais.csv"
    path.write_text(
        "preco_fato_id,data_id,produto_id,localidade_id,"
        "preco_medio_revenda\n"
        "1,1,1,1,6.12345\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("fato_precos_semanais", path)],
    )

    with pytest.raises(
        ValueError,
        match="arredondamento",
    ):
        validate_csv_contracts()


def _write_valid_aggregate_contract_bundle(
    tmp_path: Path,
) -> list[tuple[str, Path]]:
    data = tmp_path / "dim_data.csv"
    product = tmp_path / "dim_produto.csv"
    locality = tmp_path / "dim_localidade.csv"
    fact = tmp_path / "fato_precos_semanais.csv"

    data.write_text(
        "data_id,data_inicial,data_final,ano,mes,"
        "semana_iso,trimestre\n"
        "1,2026-01-04,2026-01-10,2026,1,1,1\n",
        encoding="utf-8",
    )
    product.write_text(
        "produto_id,produto\n"
        "1,GASOLINA\n",
        encoding="utf-8",
    )
    locality.write_text(
        "localidade_id,nivel_geografico,regiao,uf,estado,municipio\n"
        "1,municipio,NORDESTE,CE,CEARA,FORTALEZA\n",
        encoding="utf-8",
    )
    fact.write_text(
        "preco_fato_id,data_id,produto_id,localidade_id,"
        "unidade_medida,preco_medio_revenda\n"
        "1,1,1,1,R$/L,6.1234\n",
        encoding="utf-8",
    )

    return [
        ("dim_data", data),
        ("dim_produto", product),
        ("dim_localidade", locality),
        ("fato_precos_semanais", fact),
    ]


def test_aggregate_relations_reject_missing_foreign_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    plan = _write_valid_aggregate_contract_bundle(
        tmp_path
    )
    fact = dict(plan)[
        "fato_precos_semanais"
    ]
    fact.write_text(
        "preco_fato_id,data_id,produto_id,localidade_id,"
        "unidade_medida,preco_medio_revenda\n"
        "1,1,99,1,R$/L,6.1234\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        plan,
    )

    with pytest.raises(
        ValueError,
        match="referência inexistente",
    ):
        validate_input_files()


def test_aggregate_relations_reject_duplicate_fact_grain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    plan = _write_valid_aggregate_contract_bundle(
        tmp_path
    )
    fact = dict(plan)[
        "fato_precos_semanais"
    ]
    fact.write_text(
        "preco_fato_id,data_id,produto_id,localidade_id,"
        "unidade_medida,preco_medio_revenda\n"
        "1,1,1,1,R$/L,6.1234\n"
        "2,1,1,1,R$/L,6.1200\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        plan,
    )

    with pytest.raises(
        ValueError,
        match="grão duplicado",
    ):
        validate_input_files()


def test_aggregate_csv_contract_rejects_date_outside_2026(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_data.csv"
    path.write_text(
        "data_id,data_inicial,data_final,ano,mes,"
        "semana_iso,trimestre\n"
        "1,2025-12-28,2026-01-03,2025,12,52,4\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_data", path)],
    )

    with pytest.raises(
        ValueError,
        match="deve pertencer a 2026",
    ):
        validate_csv_contracts()


def test_station_csv_contract_rejects_date_outside_2026(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import src.load_postgres as loader

    path = tmp_path / "dim_data_coleta.csv"
    path.write_text(
        "data_coleta_id,data_coleta,ano,mes,semana_iso\n"
        "1,2025-12-31,2025,12,1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        [("dim_data_coleta", path)],
    )

    with pytest.raises(
        ValueError,
        match="deve pertencer a 2026",
    ):
        validate_csv_contracts()


def test_aggregate_sql_schema_columns_match_loader_contract() -> None:
    from src.config import PROJECT_ROOT

    schema = (
        PROJECT_ROOT
        / "sql"
        / "schema.sql"
    ).read_text(
        encoding="utf-8",
    )
    aggregate_tables = (
        "dim_data",
        "dim_produto",
        "dim_localidade",
        "fato_precos_semanais",
    )
    column_pattern = re.compile(
        r"^\s*([a-z_][a-z0-9_]*)\s+"
        r"(?:BIGINT|DATE|SMALLINT|VARCHAR|CHAR|NUMERIC|"
        r"INTEGER|TEXT|BOOLEAN)\b",
        re.MULTILINE,
    )

    for table in aggregate_tables:
        block = re.search(
            rf"CREATE TABLE IF NOT EXISTS {table}\s*"
            r"\((.*?)\n\);",
            schema,
            re.DOTALL,
        )
        assert block is not None
        declared = set(
            column_pattern.findall(
                block.group(1)
            )
        )
        assert declared == TABLE_COLUMNS[table]
