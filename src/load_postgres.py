from __future__ import annotations

import csv
import re
from pathlib import Path

import psycopg
from psycopg import sql

from .build_model import MODEL_DIR
from .config import PROJECT_ROOT
from .database import get_database_settings
from .station_data import STATION_MODEL_DIR

SQL_DIR = PROJECT_ROOT / "sql"

LOAD_PLAN = [
    ("dim_data", MODEL_DIR / "dim_data.csv"),
    ("dim_produto", MODEL_DIR / "dim_produto.csv"),
    ("dim_localidade", MODEL_DIR / "dim_localidade.csv"),
    ("fato_precos_semanais", MODEL_DIR / "fato_precos_semanais.csv"),
    ("dim_data_coleta", STATION_MODEL_DIR / "dim_data_coleta.csv"),
    ("dim_produto_posto", STATION_MODEL_DIR / "dim_produto_posto.csv"),
    ("dim_posto", STATION_MODEL_DIR / "dim_posto.csv"),
    ("fato_precos_postos", STATION_MODEL_DIR / "fato_precos_postos.csv"),
]

TABLE_COLUMNS = {
    "dim_data": {
        "data_id",
        "data_inicial",
        "data_final",
        "ano",
        "mes",
        "semana_iso",
        "trimestre",
    },
    "dim_produto": {
        "produto_id",
        "produto",
    },
    "dim_localidade": {
        "localidade_id",
        "nivel_geografico",
        "regiao",
        "uf",
        "estado",
        "municipio",
    },
    "fato_precos_semanais": {
        "preco_fato_id",
        "data_id",
        "produto_id",
        "localidade_id",
        "postos_pesquisados",
        "unidade_medida",
        "preco_medio_revenda",
        "preco_minimo_revenda",
        "preco_maximo_revenda",
        "desvio_padrao_revenda",
        "coef_variacao_revenda",
        "fonte_arquivo",
        "fonte_planilha",
    },
    "dim_data_coleta": {
        "data_coleta_id",
        "data_coleta",
        "ano",
        "mes",
        "semana_iso",
    },
    "dim_produto_posto": {
        "produto_posto_id",
        "produto",
        "unidade_medida",
    },
    "dim_posto": {
        "posto_id",
        "posto_chave",
        "cnpj_revenda",
        "revenda",
        "bandeira",
        "regiao",
        "uf",
        "municipio",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
    },
    "fato_precos_postos": {
        "preco_posto_id",
        "data_coleta_id",
        "produto_posto_id",
        "posto_id",
        "preco_revenda",
        "preco_compra",
        "fonte_arquivo",
    },
}

REQUIRED_TABLE_COLUMNS = {
    "dim_data": TABLE_COLUMNS["dim_data"],
    "dim_produto": TABLE_COLUMNS["dim_produto"],
    "dim_localidade": TABLE_COLUMNS["dim_localidade"],
    "fato_precos_semanais": {
        "preco_fato_id",
        "data_id",
        "produto_id",
        "localidade_id",
        "preco_medio_revenda",
    },
    "dim_data_coleta": TABLE_COLUMNS["dim_data_coleta"],
    "dim_produto_posto": TABLE_COLUMNS["dim_produto_posto"],
    "dim_posto": {
        "posto_id",
        "posto_chave",
        "uf",
        "municipio",
    },
    "fato_precos_postos": {
        "preco_posto_id",
        "data_coleta_id",
        "produto_posto_id",
        "posto_id",
        "preco_revenda",
        "fonte_arquivo",
    },
}


def required_files() -> list[Path]:
    return [path for _, path in LOAD_PLAN]


def _read_csv_header(path: Path) -> list[str]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.reader(handle)
        try:
            return [
                column.strip()
                for column in next(reader)
            ]
        except StopIteration as exc:
            raise ValueError(
                f"CSV vazio: {path}"
            ) from exc


def validate_csv_contracts() -> None:
    errors: list[str] = []

    for table, path in LOAD_PLAN:
        header = _read_csv_header(path)
        header_set = set(header)

        if len(header) != len(header_set):
            errors.append(
                f"{table}: cabeçalho contém colunas duplicadas"
            )
            continue

        allowed = TABLE_COLUMNS[table]
        required = REQUIRED_TABLE_COLUMNS[table]

        unknown = sorted(header_set - allowed)
        missing = sorted(required - header_set)

        if unknown:
            errors.append(
                f"{table}: colunas não suportadas: "
                + ", ".join(unknown)
            )
        if missing:
            errors.append(
                f"{table}: colunas obrigatórias ausentes: "
                + ", ".join(missing)
            )

    if errors:
        raise ValueError(
            "Contrato dos CSVs incompatível com o schema PostgreSQL:\n"
            + "\n".join(f"- {item}" for item in errors)
        )


def validate_input_files() -> None:
    missing = [
        path
        for path in required_files()
        if not path.exists()
    ]
    if missing:
        formatted = "\n".join(
            f"- {path.relative_to(PROJECT_ROOT)}"
            for path in missing
        )
        raise FileNotFoundError(
            "Arquivos do modelo ainda não foram gerados. "
            "Execute python -m src.pipeline antes da carga PostgreSQL.\n"
            f"Ausentes:\n{formatted}"
        )

    validate_csv_contracts()


DOLLAR_QUOTE_PATTERN = re.compile(
    r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$"
)


def _split_sql_statements(
    script: str,
) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    index = 0
    length = len(script)
    state = "normal"
    dollar_tag: str | None = None
    block_depth = 0
    has_code = False
    backslash_escaped_string = False

    while index < length:
        char = script[index]
        next_char = (
            script[index + 1]
            if index + 1 < length
            else ""
        )

        if state == "line_comment":
            current.append(char)
            index += 1
            if char == "\n":
                state = "normal"
            continue

        if state == "block_comment":
            if (
                char == "/"
                and next_char == "*"
            ):
                current.extend(
                    [char, next_char]
                )
                block_depth += 1
                index += 2
                continue
            if (
                char == "*"
                and next_char == "/"
            ):
                current.extend(
                    [char, next_char]
                )
                block_depth -= 1
                index += 2
                if block_depth == 0:
                    state = "normal"
                continue

            current.append(char)
            index += 1
            continue

        if state == "single_quote":
            current.append(char)

            if (
                backslash_escaped_string
                and char == "\\"
                and next_char
            ):
                current.append(
                    next_char
                )
                index += 2
                continue

            if char == "'":
                if next_char == "'":
                    current.append(
                        next_char
                    )
                    index += 2
                    continue
                state = "normal"
                backslash_escaped_string = False

            index += 1
            continue

        if state == "double_quote":
            current.append(char)
            if char == '"':
                if next_char == '"':
                    current.append(
                        next_char
                    )
                    index += 2
                    continue
                state = "normal"

            index += 1
            continue

        if state == "dollar_quote":
            if (
                dollar_tag
                and script.startswith(
                    dollar_tag,
                    index,
                )
            ):
                current.append(
                    dollar_tag
                )
                index += len(
                    dollar_tag
                )
                state = "normal"
                dollar_tag = None
                continue

            current.append(char)
            index += 1
            continue

        if (
            char == "-"
            and next_char == "-"
        ):
            current.extend(
                [char, next_char]
            )
            index += 2
            state = "line_comment"
            continue

        if (
            char == "/"
            and next_char == "*"
        ):
            current.extend(
                [char, next_char]
            )
            index += 2
            state = "block_comment"
            block_depth = 1
            continue

        if char == "'":
            previous = (
                script[index - 1]
                if index > 0
                else ""
            )
            before_previous = (
                script[index - 2]
                if index > 1
                else ""
            )
            backslash_escaped_string = (
                previous in {"E", "e"}
                and (
                    index == 1
                    or not (
                        before_previous.isalnum()
                        or before_previous == "_"
                    )
                )
            )
            current.append(char)
            index += 1
            state = "single_quote"
            has_code = True
            continue

        if char == '"':
            current.append(char)
            index += 1
            state = "double_quote"
            has_code = True
            continue

        if char == "$":
            match = (
                DOLLAR_QUOTE_PATTERN.match(
                    script,
                    index,
                )
            )
            if match is not None:
                dollar_tag = (
                    match.group(0)
                )
                current.append(
                    dollar_tag
                )
                index = match.end()
                state = "dollar_quote"
                has_code = True
                continue

        if char == ";":
            if has_code:
                statement = "".join(
                    current
                ).strip()
                if statement:
                    statements.append(
                        statement
                    )
            current = []
            has_code = False
            index += 1
            continue

        current.append(char)
        if not char.isspace():
            has_code = True
        index += 1

    if state in {
        "single_quote",
        "double_quote",
        "block_comment",
        "dollar_quote",
    }:
        raise ValueError(
            "Arquivo SQL incompleto: "
            f"delimitador não encerrado ({state})."
        )

    if has_code:
        statement = "".join(
            current
        ).strip()
        if statement:
            statements.append(
                statement
            )

    return statements


def _execute_sql_file(
    connection: psycopg.Connection,
    path: Path,
) -> None:
    script = path.read_text(
        encoding="utf-8"
    )

    for statement in (
        _split_sql_statements(
            script
        )
    ):
        connection.execute(
            statement
        )


def _copy_csv(
    connection: psycopg.Connection,
    table: str,
    path: Path,
) -> int:
    columns = _read_csv_header(path)

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        next(handle)
        payload = handle.read()

    command = sql.SQL(
        "COPY {} ({}) FROM STDIN "
        "WITH (FORMAT CSV, HEADER FALSE, NULL '')"
    ).format(
        sql.Identifier(table),
        sql.SQL(", ").join(
            sql.Identifier(column)
            for column in columns
        ),
    )

    with connection.cursor() as cursor:
        with cursor.copy(command) as copy:
            copy.write(payload)

    count_query = sql.SQL(
        "SELECT COUNT(*) FROM {}"
    ).format(sql.Identifier(table))
    return int(
        connection.execute(
            count_query
        ).fetchone()[0]
    )


def _truncate_tables(
    connection: psycopg.Connection,
) -> None:
    tables = [
        table
        for table, _ in LOAD_PLAN
    ]
    statement = sql.SQL(
        "TRUNCATE TABLE {} RESTART IDENTITY CASCADE"
    ).format(
        sql.SQL(", ").join(
            sql.Identifier(table)
            for table in tables
        )
    )
    connection.execute(statement)


def _finalize_model_constraints(
    connection: psycopg.Connection,
) -> None:
    connection.execute(
        "ALTER TABLE dim_posto "
        "ALTER COLUMN posto_chave "
        "SET NOT NULL"
    )
    connection.execute(
        "ALTER TABLE dim_produto_posto "
        "ALTER COLUMN unidade_medida "
        "SET NOT NULL"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "ux_dim_localidade_natural "
        "ON dim_localidade ("
        "nivel_geografico, "
        "COALESCE(regiao, ''), "
        "COALESCE(uf, ''), "
        "COALESCE(estado, ''), "
        "COALESCE(municipio, '')"
        ")"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "ux_dim_produto_posto_natural "
        "ON dim_produto_posto ("
        "produto, COALESCE(unidade_medida, '')"
        ")"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "ux_fato_precos_semanais_grain "
        "ON fato_precos_semanais ("
        "data_id, produto_id, localidade_id, "
        "COALESCE(unidade_medida, '')"
        ")"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "ux_fato_precos_postos_grain "
        "ON fato_precos_postos ("
        "data_coleta_id, produto_posto_id, posto_id"
        ")"
    )


def _validate_database(
    connection: psycopg.Connection,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for table, _ in LOAD_PLAN:
        query = sql.SQL(
            "SELECT COUNT(*) FROM {}"
        ).format(
            sql.Identifier(table)
        )
        counts[table] = int(
            connection.execute(
                query
            ).fetchone()[0]
        )

    if counts["fato_precos_semanais"] <= 0:
        raise RuntimeError(
            "A tabela fato_precos_semanais foi carregada sem registros."
        )
    if counts["fato_precos_postos"] <= 0:
        raise RuntimeError(
            "A tabela fato_precos_postos foi carregada sem registros."
        )

    return counts


def main() -> None:
    validate_input_files()
    settings = get_database_settings()

    with psycopg.connect(
        settings.url
    ) as connection:
        print("Criando estruturas SQL...")
        _execute_sql_file(
            connection,
            SQL_DIR / "schema.sql",
        )
        _execute_sql_file(
            connection,
            SQL_DIR / "station_schema.sql",
        )

        print("Limpando carga anterior...")
        _truncate_tables(connection)
        _finalize_model_constraints(
            connection
        )

        print("Carregando CSVs...")
        for table, path in LOAD_PLAN:
            rows = _copy_csv(
                connection,
                table,
                path,
            )
            print(
                f"{table}: {rows:,} linhas"
            )

        print("Criando views...")
        _execute_sql_file(
            connection,
            SQL_DIR / "views.sql",
        )

        print("Validando banco...")
        counts = _validate_database(
            connection
        )

        connection.commit()

    print("\nCarga PostgreSQL concluída.")
    for table, rows in counts.items():
        print(f"- {table}: {rows:,}")


if __name__ == "__main__":
    main()
