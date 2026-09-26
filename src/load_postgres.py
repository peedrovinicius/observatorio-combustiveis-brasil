from __future__ import annotations

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


def required_files() -> list[Path]:
    return [path for _, path in LOAD_PLAN]


def validate_input_files() -> None:
    missing = [path for path in required_files() if not path.exists()]
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


def _execute_sql_file(
    connection: psycopg.Connection,
    path: Path,
) -> None:
    script = path.read_text(encoding="utf-8")

    for statement in script.split(";"):
        statement = statement.strip()
        if not statement:
            continue
        connection.execute(statement)


def _copy_csv(
    connection: psycopg.Connection,
    table: str,
    path: Path,
) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        header = handle.readline().strip()
        if not header:
            raise ValueError(f"CSV sem cabeçalho: {path}")

        columns = [column.strip() for column in header.split(",")]
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

        payload = handle.read()

    with connection.cursor() as cursor:
        with cursor.copy(command) as copy:
            copy.write(payload)

    count_query = sql.SQL("SELECT COUNT(*) FROM {}").format(
        sql.Identifier(table)
    )
    return int(connection.execute(count_query).fetchone()[0])


def _truncate_tables(
    connection: psycopg.Connection,
) -> None:
    tables = [table for table, _ in LOAD_PLAN]
    statement = sql.SQL(
        "TRUNCATE TABLE {} RESTART IDENTITY CASCADE"
    ).format(
        sql.SQL(", ").join(
            sql.Identifier(table)
            for table in tables
        )
    )
    connection.execute(statement)


def _validate_database(
    connection: psycopg.Connection,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for table, _ in LOAD_PLAN:
        query = sql.SQL("SELECT COUNT(*) FROM {}").format(
            sql.Identifier(table)
        )
        counts[table] = int(
            connection.execute(query).fetchone()[0]
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

    with psycopg.connect(settings.url) as connection:
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

        print("Carregando CSVs...")
        for table, path in LOAD_PLAN:
            rows = _copy_csv(connection, table, path)
            print(f"{table}: {rows:,} linhas")

        print("Criando views...")
        _execute_sql_file(
            connection,
            SQL_DIR / "views.sql",
        )

        print("Validando banco...")
        counts = _validate_database(connection)

        connection.commit()

    print("\nCarga PostgreSQL concluída.")
    for table, rows in counts.items():
        print(f"- {table}: {rows:,}")


if __name__ == "__main__":
    main()
