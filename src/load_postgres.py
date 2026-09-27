from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
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

AGGREGATE_TEXT_LIMITS = {
    "dim_produto": {
        "produto": 150,
    },
    "dim_localidade": {
        "nivel_geografico": 20,
        "regiao": 40,
        "uf": 2,
        "estado": 120,
        "municipio": 160,
    },
    "fato_precos_semanais": {
        "unidade_medida": 30,
        "fonte_arquivo": 255,
        "fonte_planilha": 255,
    },
}

AGGREGATE_NONEMPTY_COLUMNS = {
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
    },
    "fato_precos_semanais": {
        "preco_fato_id",
        "data_id",
        "produto_id",
        "localidade_id",
        "preco_medio_revenda",
    },
}

AGGREGATE_ID_COLUMNS = {
    "dim_data": {
        "data_id",
    },
    "dim_produto": {
        "produto_id",
    },
    "dim_localidade": {
        "localidade_id",
    },
    "fato_precos_semanais": {
        "preco_fato_id",
        "data_id",
        "produto_id",
        "localidade_id",
    },
}

STATION_TEXT_LIMITS = {
    "dim_produto_posto": {
        "produto": 150,
        "unidade_medida": 40,
    },
    "dim_posto": {
        "posto_chave": 64,
        "cnpj_revenda": 30,
        "revenda": 255,
        "bandeira": 180,
        "regiao": 10,
        "uf": 2,
        "municipio": 160,
        "logradouro": 255,
        "numero": 40,
        "complemento": 255,
        "bairro": 160,
        "cep": 20,
    },
    "fato_precos_postos": {
        "fonte_arquivo": 255,
    },
}

STATION_NONEMPTY_COLUMNS = {
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

STATION_ID_COLUMNS = {
    "dim_data_coleta": {
        "data_coleta_id",
    },
    "dim_produto_posto": {
        "produto_posto_id",
    },
    "dim_posto": {
        "posto_id",
    },
    "fato_precos_postos": {
        "preco_posto_id",
        "data_coleta_id",
        "produto_posto_id",
        "posto_id",
    },
}

MAX_VALUE_ERRORS = 25


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


def _is_blank(value: str | None) -> bool:
    return (
        value is None
        or not value.strip()
    )


def _decimal_contract_error(
    value: str,
    precision: int,
    scale: int,
) -> str | None:
    try:
        number = Decimal(value)
    except InvalidOperation:
        return "valor decimal inválido"

    if not number.is_finite():
        return "valor decimal não finito"

    _, digits, exponent = (
        number.as_tuple()
    )
    decimal_places = max(
        -exponent,
        0,
    )
    integer_digits = max(
        len(digits) + exponent,
        0,
    )

    if decimal_places > scale:
        return (
            f"excede {scale} casas decimais "
            "e exigiria arredondamento"
        )
    if integer_digits > (
        precision - scale
    ):
        return (
            "excede o limite de "
            f"NUMERIC({precision}, {scale})"
        )

    return None


def _validate_aggregate_csv_values(
    table: str,
    path: Path,
) -> list[str]:
    if table not in (
        AGGREGATE_NONEMPTY_COLUMNS
    ):
        return []

    errors: list[str] = []
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )
        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            def add_error(
                column: str,
                message: str,
            ) -> None:
                if len(errors) < (
                    MAX_VALUE_ERRORS
                ):
                    errors.append(
                        f"{table}: linha "
                        f"{row_number}, "
                        f"{column}: {message}"
                    )

            for column in (
                AGGREGATE_NONEMPTY_COLUMNS[
                    table
                ]
            ):
                if _is_blank(
                    row.get(column)
                ):
                    add_error(
                        column,
                        "valor obrigatório vazio",
                    )

            for column, limit in (
                AGGREGATE_TEXT_LIMITS
                .get(
                    table,
                    {},
                )
                .items()
            ):
                value = row.get(column)
                if _is_blank(value):
                    continue
                if value != value.strip():
                    add_error(
                        column,
                        "não deve conter espaços "
                        "externos",
                    )
                if len(value) > limit:
                    add_error(
                        column,
                        "excede o limite de "
                        f"{limit} caracteres",
                    )

            for column in (
                AGGREGATE_ID_COLUMNS[
                    table
                ]
            ):
                value = row.get(column)
                if _is_blank(value):
                    continue
                if not re.fullmatch(
                    r"[1-9][0-9]*",
                    value.strip(),
                ):
                    add_error(
                        column,
                        "deve ser inteiro positivo",
                    )

            if table == "dim_data":
                parsed_dates: dict[
                    str,
                    date,
                ] = {}
                for column in (
                    "data_inicial",
                    "data_final",
                ):
                    value = row.get(column)
                    if _is_blank(value):
                        continue
                    try:
                        parsed_dates[
                            column
                        ] = date.fromisoformat(
                            value.strip()
                        )
                    except ValueError:
                        add_error(
                            column,
                            "data ISO inválida",
                        )

                start = parsed_dates.get(
                    "data_inicial"
                )
                end = parsed_dates.get(
                    "data_final"
                )
                if (
                    start is not None
                    and end is not None
                    and end < start
                ):
                    add_error(
                        "data_final",
                        "não pode ser anterior "
                        "a data_inicial",
                    )

                components = {}
                for column in (
                    "ano",
                    "mes",
                    "semana_iso",
                    "trimestre",
                ):
                    value = row.get(column)
                    if _is_blank(value):
                        continue
                    try:
                        components[
                            column
                        ] = int(
                            value.strip()
                        )
                    except ValueError:
                        add_error(
                            column,
                            "deve ser inteiro",
                        )

                if (
                    start is not None
                    and start.year != 2026
                ):
                    add_error(
                        "data_inicial",
                        "deve pertencer a 2026",
                    )

                if start is not None:
                    expected = {
                        "ano": start.year,
                        "mes": start.month,
                        "semana_iso": (
                            start
                            .isocalendar()
                            .week
                        ),
                        "trimestre": (
                            (start.month - 1)
                            // 3
                            + 1
                        ),
                    }
                    for (
                        column,
                        expected_value,
                    ) in expected.items():
                        actual = (
                            components.get(
                                column
                            )
                        )
                        if (
                            actual is not None
                            and actual
                            != expected_value
                        ):
                            add_error(
                                column,
                                "incompatível com "
                                "data_inicial",
                            )

            if table == (
                "dim_localidade"
            ):
                level = row.get(
                    "nivel_geografico"
                )
                if (
                    not _is_blank(level)
                    and level
                    not in {
                        "brasil",
                        "regiao",
                        "estado",
                        "municipio",
                    }
                ):
                    add_error(
                        "nivel_geografico",
                        "nível geográfico inválido",
                    )
                uf = row.get("uf")
                if (
                    not _is_blank(uf)
                    and re.fullmatch(
                        r"[A-Z]{2}",
                        uf,
                    )
                    is None
                ):
                    add_error(
                        "uf",
                        "deve conter duas "
                        "letras maiúsculas",
                    )

            if table == (
                "fato_precos_semanais"
            ):
                integer_value = row.get(
                    "postos_pesquisados"
                )
                if not _is_blank(
                    integer_value
                ):
                    if not re.fullmatch(
                        r"[0-9]+",
                        integer_value.strip(),
                    ):
                        add_error(
                            "postos_pesquisados",
                            "deve ser inteiro "
                            "não negativo",
                        )

                decimal_specs = {
                    "preco_medio_revenda": (
                        12,
                        4,
                    ),
                    "preco_minimo_revenda": (
                        12,
                        4,
                    ),
                    "preco_maximo_revenda": (
                        12,
                        4,
                    ),
                    "desvio_padrao_revenda": (
                        12,
                        6,
                    ),
                    "coef_variacao_revenda": (
                        12,
                        6,
                    ),
                }
                parsed: dict[
                    str,
                    Decimal,
                ] = {}
                for (
                    column,
                    (
                        precision,
                        scale,
                    ),
                ) in decimal_specs.items():
                    value = row.get(column)
                    if _is_blank(value):
                        continue
                    error = (
                        _decimal_contract_error(
                            value.strip(),
                            precision,
                            scale,
                        )
                    )
                    if error is not None:
                        add_error(
                            column,
                            error,
                        )
                        continue
                    parsed[column] = Decimal(
                        value.strip()
                    )

                average = parsed.get(
                    "preco_medio_revenda"
                )
                if (
                    average is not None
                    and average <= 0
                ):
                    add_error(
                        "preco_medio_revenda",
                        "deve ser maior que zero",
                    )

                minimum = parsed.get(
                    "preco_minimo_revenda"
                )
                maximum = parsed.get(
                    "preco_maximo_revenda"
                )
                if (
                    minimum is not None
                    and maximum is not None
                    and minimum > maximum
                ):
                    add_error(
                        "preco_minimo_revenda",
                        "não pode exceder "
                        "preco_maximo_revenda",
                    )

            if len(errors) >= (
                MAX_VALUE_ERRORS
            ):
                break

    return errors


def _validate_station_csv_values(
    table: str,
    path: Path,
) -> list[str]:
    if table not in (
        STATION_NONEMPTY_COLUMNS
    ):
        return []

    errors: list[str] = []
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )
        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            def add_error(
                column: str,
                message: str,
            ) -> None:
                if len(errors) < (
                    MAX_VALUE_ERRORS
                ):
                    errors.append(
                        f"{table}: linha "
                        f"{row_number}, "
                        f"{column}: {message}"
                    )

            for column in (
                STATION_NONEMPTY_COLUMNS[
                    table
                ]
            ):
                if _is_blank(
                    row.get(column)
                ):
                    add_error(
                        column,
                        "valor obrigatório vazio",
                    )

            for column, limit in (
                STATION_TEXT_LIMITS
                .get(
                    table,
                    {},
                )
                .items()
            ):
                value = row.get(column)
                if _is_blank(value):
                    continue
                if value != value.strip():
                    add_error(
                        column,
                        "não deve conter espaços "
                        "externos",
                    )
                if len(value) > limit:
                    add_error(
                        column,
                        "excede o limite de "
                        f"{limit} caracteres",
                    )

            for column in (
                STATION_ID_COLUMNS[
                    table
                ]
            ):
                value = row.get(column)
                if _is_blank(value):
                    continue
                if not re.fullmatch(
                    r"[1-9][0-9]*",
                    value.strip(),
                ):
                    add_error(
                        column,
                        "deve ser inteiro positivo",
                    )

            if table == (
                "dim_data_coleta"
            ):
                raw_date = row.get(
                    "data_coleta"
                )
                parsed_date = None
                if not _is_blank(
                    raw_date
                ):
                    try:
                        parsed_date = (
                            date.fromisoformat(
                                raw_date.strip()
                            )
                        )
                    except ValueError:
                        add_error(
                            "data_coleta",
                            "data ISO inválida",
                        )

                components = {}
                for column in (
                    "ano",
                    "mes",
                    "semana_iso",
                ):
                    value = row.get(
                        column
                    )
                    if _is_blank(value):
                        continue
                    try:
                        components[
                            column
                        ] = int(
                            value.strip()
                        )
                    except ValueError:
                        add_error(
                            column,
                            "deve ser inteiro",
                        )

                if (
                    parsed_date is not None
                    and parsed_date.year
                    != 2026
                ):
                    add_error(
                        "data_coleta",
                        "deve pertencer a 2026",
                    )

                if parsed_date is not None:
                    expected = {
                        "ano": (
                            parsed_date.year
                        ),
                        "mes": (
                            parsed_date.month
                        ),
                        "semana_iso": (
                            parsed_date
                            .isocalendar()
                            .week
                        ),
                    }
                    for (
                        column,
                        expected_value,
                    ) in expected.items():
                        actual = (
                            components.get(
                                column
                            )
                        )
                        if (
                            actual is not None
                            and actual
                            != expected_value
                        ):
                            add_error(
                                column,
                                "incompatível com "
                                "data_coleta",
                            )

            if table == "dim_posto":
                station_key = row.get(
                    "posto_chave"
                )
                if (
                    not _is_blank(
                        station_key
                    )
                    and re.fullmatch(
                        r"[0-9a-f]{64}",
                        station_key,
                    )
                    is None
                ):
                    add_error(
                        "posto_chave",
                        "deve ser SHA-256 "
                        "hexadecimal com "
                        "64 caracteres",
                    )

                uf = row.get("uf")
                if (
                    not _is_blank(uf)
                    and re.fullmatch(
                        r"[A-Z]{2}",
                        uf,
                    )
                    is None
                ):
                    add_error(
                        "uf",
                        "deve conter duas "
                        "letras maiúsculas",
                    )

            if table == (
                "fato_precos_postos"
            ):
                for column in (
                    "preco_revenda",
                    "preco_compra",
                ):
                    value = row.get(column)
                    if _is_blank(value):
                        continue
                    error = (
                        _decimal_contract_error(
                            value.strip(),
                            12,
                            4,
                        )
                    )
                    if error is not None:
                        add_error(
                            column,
                            error,
                        )
                        continue

                    if (
                        column
                        == "preco_revenda"
                        and Decimal(
                            value.strip()
                        )
                        <= 0
                    ):
                        add_error(
                            column,
                            "deve ser maior que zero",
                        )

            if len(errors) >= (
                MAX_VALUE_ERRORS
            ):
                break

    return errors


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

        if (
            not unknown
            and not missing
        ):
            errors.extend(
                _validate_aggregate_csv_values(
                    table,
                    path,
                )
            )
            errors.extend(
                _validate_station_csv_values(
                    table,
                    path,
                )
            )

    if errors:
        raise ValueError(
            "Contrato dos CSVs incompatível com o schema PostgreSQL:\n"
            + "\n".join(f"- {item}" for item in errors)
        )


def _read_csv_records(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(
            csv.DictReader(handle)
        )


def _validate_aggregate_relations() -> None:
    paths = {
        table: path
        for table, path in LOAD_PLAN
        if table in {
            "dim_data",
            "dim_produto",
            "dim_localidade",
            "fato_precos_semanais",
        }
    }
    required_tables = {
        "dim_data",
        "dim_produto",
        "dim_localidade",
        "fato_precos_semanais",
    }
    if set(paths) != required_tables:
        return

    errors: list[str] = []
    dimensions = {
        table: _read_csv_records(
            paths[table]
        )
        for table in (
            "dim_data",
            "dim_produto",
            "dim_localidade",
        )
    }

    def unique_index(
        table: str,
        column: str,
    ) -> set[str]:
        values: set[str] = set()
        for row_number, row in enumerate(
            dimensions[table],
            start=2,
        ):
            value = row[column].strip()
            if value in values:
                errors.append(
                    f"{table}: linha "
                    f"{row_number}, "
                    f"{column}: valor duplicado"
                )
            values.add(value)
        return values

    date_ids = unique_index(
        "dim_data",
        "data_id",
    )
    product_ids = unique_index(
        "dim_produto",
        "produto_id",
    )
    locality_ids = unique_index(
        "dim_localidade",
        "localidade_id",
    )

    natural_keys = (
        (
            "dim_data",
            (
                "data_inicial",
                "data_final",
            ),
        ),
        (
            "dim_produto",
            ("produto",),
        ),
        (
            "dim_localidade",
            (
                "nivel_geografico",
                "regiao",
                "uf",
                "estado",
                "municipio",
            ),
        ),
    )
    for table, columns in natural_keys:
        seen: set[
            tuple[str, ...]
        ] = set()
        for row_number, row in enumerate(
            dimensions[table],
            start=2,
        ):
            key = tuple(
                row.get(
                    column,
                    "",
                ).strip()
                for column in columns
            )
            if key in seen:
                errors.append(
                    f"{table}: linha "
                    f"{row_number}: "
                    "chave natural duplicada"
                )
            seen.add(key)

    fact_ids: set[str] = set()
    fact_grain: set[
        tuple[str, str, str, str]
    ] = set()
    with paths[
        "fato_precos_semanais"
    ].open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )
        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            fact_id = row[
                "preco_fato_id"
            ].strip()
            if fact_id in fact_ids:
                errors.append(
                    "fato_precos_semanais: "
                    f"linha {row_number}, "
                    "preco_fato_id: "
                    "valor duplicado"
                )
            fact_ids.add(fact_id)

            references = (
                (
                    "data_id",
                    date_ids,
                ),
                (
                    "produto_id",
                    product_ids,
                ),
                (
                    "localidade_id",
                    locality_ids,
                ),
            )
            for column, valid_ids in (
                references
            ):
                value = row[
                    column
                ].strip()
                if value not in valid_ids:
                    errors.append(
                        "fato_precos_semanais: "
                        f"linha {row_number}, "
                        f"{column}: referência "
                        "inexistente"
                    )

            grain = (
                row[
                    "data_id"
                ].strip(),
                row[
                    "produto_id"
                ].strip(),
                row[
                    "localidade_id"
                ].strip(),
                (
                    row.get(
                        "unidade_medida",
                        "",
                    )
                    or ""
                ).strip(),
            )
            if grain in fact_grain:
                errors.append(
                    "fato_precos_semanais: "
                    f"linha {row_number}: "
                    "grão duplicado"
                )
            fact_grain.add(grain)

            if len(errors) >= (
                MAX_VALUE_ERRORS
            ):
                break

    if errors:
        raise ValueError(
            "Integridade referencial dos "
            "CSVs agregados inválida:\n"
            + "\n".join(
                f"- {item}"
                for item in errors[
                    :MAX_VALUE_ERRORS
                ]
            )
        )


def _validate_station_relations() -> None:
    paths = {
        table: path
        for table, path in LOAD_PLAN
        if table in {
            "dim_data_coleta",
            "dim_produto_posto",
            "dim_posto",
            "fato_precos_postos",
        }
    }
    required_tables = {
        "dim_data_coleta",
        "dim_produto_posto",
        "dim_posto",
        "fato_precos_postos",
    }
    if set(paths) != required_tables:
        return

    errors: list[str] = []
    dimensions = {
        table: _read_csv_records(
            paths[table]
        )
        for table in (
            "dim_data_coleta",
            "dim_produto_posto",
            "dim_posto",
        )
    }

    def unique_index(
        table: str,
        column: str,
    ) -> set[str]:
        values: set[str] = set()
        for row_number, row in enumerate(
            dimensions[table],
            start=2,
        ):
            value = row[column].strip()
            if value in values:
                errors.append(
                    f"{table}: linha "
                    f"{row_number}, "
                    f"{column}: valor duplicado"
                )
            values.add(value)
        return values

    date_ids = unique_index(
        "dim_data_coleta",
        "data_coleta_id",
    )
    product_ids = unique_index(
        "dim_produto_posto",
        "produto_posto_id",
    )
    station_ids = unique_index(
        "dim_posto",
        "posto_id",
    )
    unique_index(
        "dim_posto",
        "posto_chave",
    )

    for (
        table,
        columns,
    ) in (
        (
            "dim_data_coleta",
            ("data_coleta",),
        ),
        (
            "dim_produto_posto",
            (
                "produto",
                "unidade_medida",
            ),
        ),
    ):
        seen: set[
            tuple[str, ...]
        ] = set()
        for row_number, row in enumerate(
            dimensions[table],
            start=2,
        ):
            key = tuple(
                row[column].strip()
                for column in columns
            )
            if key in seen:
                errors.append(
                    f"{table}: linha "
                    f"{row_number}: "
                    "chave natural duplicada"
                )
            seen.add(key)

    fact_ids: set[str] = set()
    fact_grain: set[
        tuple[str, str, str]
    ] = set()
    with paths[
        "fato_precos_postos"
    ].open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )
        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            fact_id = row[
                "preco_posto_id"
            ].strip()
            if fact_id in fact_ids:
                errors.append(
                    "fato_precos_postos: "
                    f"linha {row_number}, "
                    "preco_posto_id: "
                    "valor duplicado"
                )
            fact_ids.add(fact_id)

            references = (
                (
                    "data_coleta_id",
                    date_ids,
                ),
                (
                    "produto_posto_id",
                    product_ids,
                ),
                (
                    "posto_id",
                    station_ids,
                ),
            )
            for column, valid_ids in (
                references
            ):
                value = row[
                    column
                ].strip()
                if value not in valid_ids:
                    errors.append(
                        "fato_precos_postos: "
                        f"linha {row_number}, "
                        f"{column}: referência "
                        "inexistente"
                    )

            grain = (
                row[
                    "data_coleta_id"
                ].strip(),
                row[
                    "produto_posto_id"
                ].strip(),
                row[
                    "posto_id"
                ].strip(),
            )
            if grain in fact_grain:
                errors.append(
                    "fato_precos_postos: "
                    f"linha {row_number}: "
                    "grão duplicado"
                )
            fact_grain.add(grain)

            if len(errors) >= (
                MAX_VALUE_ERRORS
            ):
                break

    if errors:
        raise ValueError(
            "Integridade referencial dos "
            "CSVs por posto inválida:\n"
            + "\n".join(
                f"- {item}"
                for item in errors[
                    :MAX_VALUE_ERRORS
                ]
            )
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
    _validate_aggregate_relations()
    _validate_station_relations()


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
        "ALTER TABLE dim_posto "
        "ALTER COLUMN uf "
        "SET NOT NULL"
    )
    connection.execute(
        "ALTER TABLE dim_posto "
        "ALTER COLUMN municipio "
        "SET NOT NULL"
    )
    connection.execute(
        "ALTER TABLE fato_precos_postos "
        "ALTER COLUMN fonte_arquivo "
        "SET NOT NULL"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "ux_dim_posto_chave "
        "ON dim_posto(posto_chave)"
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
