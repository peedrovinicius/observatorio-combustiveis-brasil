from __future__ import annotations

import re
import shutil
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR, RAW_DIR
from .provenance import (
    verified_history_files,
)

HEADER_HINTS = {
    "DATA INICIAL",
    "DATA FINAL",
    "ESTADO",
    "MUNICÍPIO",
    "MUNICIPIO",
    "PRODUTO",
    "UNIDADE DE MEDIDA",
    "PREÇO MÉDIO REVENDA",
    "PRECO MEDIO REVENDA",
    "VALOR DE VENDA",
    "BANDEIRA",
    "CNPJ DA REVENDA",
}

HISTORY_FILE_PATTERN = re.compile(
    r"^historico_semanal_(.+?)__",
    flags=re.IGNORECASE,
)

COLUMN_ALIASES = {
    "data_inicial": "data_inicial",
    "data_final": "data_final",
    "regiao": "regiao",
    "regiao_sigla": "regiao",
    "estado": "estado",
    "estado_sigla": "uf",
    "uf": "uf",
    "municipio": "municipio",
    "produto": "produto",
    "numero_de_postos_pesquisados": "postos_pesquisados",
    "unidade_de_medida": "unidade_medida",
    "preco_medio_revenda": "preco_medio_revenda",
    "preco_minimo_revenda": "preco_minimo_revenda",
    "preco_maximo_revenda": "preco_maximo_revenda",
    "desvio_padrao_revenda": "desvio_padrao_revenda",
    "coef_de_variacao_revenda": "coef_variacao_revenda",
    "coeficiente_de_variacao_revenda": "coef_variacao_revenda",
    "razao_social": "razao_social",
    "revenda": "razao_social",
    "cnpj_da_revenda": "cnpj_revenda",
    "nome_da_rua": "logradouro",
    "numero_rua": "numero",
    "complemento": "complemento",
    "bairro": "bairro",
    "cep": "cep",
    "data_da_coleta": "data_coleta",
    "valor_de_venda": "preco_revenda",
    "valor_de_compra": "preco_compra",
    "bandeira": "bandeira",
}


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


def normalize_column(value: object) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return COLUMN_ALIASES.get(text, text)


def parse_decimal_series(series: pd.Series) -> pd.Series:
    def parse(value: object) -> float | None:
        if pd.isna(value):
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace("R$", "").replace(" ", "")
        if not text:
            return None
        if "," in text:
            text = text.replace(".", "").replace(",", ".")

        try:
            return float(text)
        except ValueError:
            return None

    return series.map(parse)


def detect_header_row(path: Path, sheet_name: str, max_rows: int = 30) -> int:
    preview = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=max_rows)

    best_row = -1
    best_score = 0

    for row_index, row in preview.iterrows():
        values = {normalize_text(value).upper() for value in row if pd.notna(value)}
        score = len(values & HEADER_HINTS)

        if score > best_score:
            best_row = int(row_index)
            best_score = score

    if best_row < 0 or best_score < 2:
        raise ValueError(
            f"Não foi possível detectar o cabeçalho da planilha '{sheet_name}' "
            f"em {path.name}. Melhor pontuação: {best_score}."
        )

    return best_row


def read_excel_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    header_row = detect_header_row(path, sheet_name)
    frame = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    frame = frame.dropna(how="all").copy()

    frame.columns = [normalize_column(column) for column in frame.columns]

    unnamed = [
        column for column in frame.columns
        if not column or column.startswith("unnamed")
    ]
    if unnamed:
        frame = frame.drop(columns=unnamed, errors="ignore")

    frame = frame.loc[:, ~frame.columns.duplicated()].copy()

    for column in ("data_inicial", "data_final", "data_coleta"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(
                frame[column], errors="coerce", dayfirst=True
            ).dt.date

    for column in (
        "preco_medio_revenda",
        "preco_minimo_revenda",
        "preco_maximo_revenda",
        "desvio_padrao_revenda",
        "coef_variacao_revenda",
        "preco_revenda",
        "preco_compra",
    ):
        if column in frame.columns:
            frame[column] = parse_decimal_series(frame[column])

    if "postos_pesquisados" in frame.columns:
        frame["postos_pesquisados"] = pd.to_numeric(
            frame["postos_pesquisados"], errors="coerce"
        ).astype("Int64")

    frame["fonte_arquivo"] = path.name
    frame["fonte_planilha"] = sheet_name

    return frame


def history_scope_from_path(
    path: Path,
) -> str | None:
    match = HISTORY_FILE_PATTERN.match(
        path.stem
    )
    if match is None:
        return None
    return match.group(1).casefold()


def clear_processed_history_scope(
    directory: Path,
    scope: str,
) -> None:
    prefix = (
        f"historico_semanal_{scope}__"
    )
    for path in directory.glob(
        prefix + "*.csv"
    ):
        if path.is_file():
            path.unlink()


def _prepare_workbook_outputs(
    path: Path,
) -> tuple[
    str | None,
    list[
        tuple[
            str,
            pd.DataFrame,
        ]
    ],
]:
    workbook = pd.ExcelFile(path)
    prepared: list[
        tuple[
            str,
            pd.DataFrame,
        ]
    ] = []
    used_names: set[str] = set()

    stem = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        path.stem,
    ).strip("_").lower()

    for sheet_name in workbook.sheet_names:
        try:
            frame = read_excel_sheet(
                path,
                sheet_name,
            )
        except ValueError:
            continue

        if frame.empty:
            continue

        safe_sheet = re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            normalize_text(
                sheet_name
            ),
        ).strip("_").lower()
        filename = (
            f"{stem}__{safe_sheet}.csv"
        )
        normalized = (
            filename.casefold()
        )
        if normalized in used_names:
            raise ValueError(
                "A planilha gera nomes de CSV "
                f"duplicados: {filename}"
            )
        used_names.add(
            normalized
        )
        prepared.append(
            (
                filename,
                frame,
            )
        )

    if not prepared:
        raise RuntimeError(
            "Nenhuma tabela reconhecida "
            f"foi encontrada em {path.name}."
        )

    return (
        history_scope_from_path(
            path
        ),
        prepared,
    )


def _processed_scope_files(
    directory: Path,
    scope: str,
) -> list[Path]:
    prefix = (
        f"historico_semanal_{scope}__"
    )
    return sorted(
        path
        for path in directory.glob(
            prefix + "*.csv"
        )
        if path.is_file()
    )


def _replace_processed_batch(
    directory: Path,
    prepared_batches: list[
        tuple[
            str | None,
            list[
                tuple[
                    str,
                    pd.DataFrame,
                ]
            ],
        ]
    ],
) -> list[Path]:
    if not prepared_batches:
        raise ValueError(
            "Lote processado vazio."
        )

    history_scopes = [
        scope
        for scope, _
        in prepared_batches
        if scope is not None
    ]
    if len(history_scopes) != len(
        set(history_scopes)
    ):
        raise ValueError(
            "Lote processado contém "
            "escopos históricos duplicados."
        )

    filenames = [
        filename
        for _, outputs
        in prepared_batches
        for filename, _
        in outputs
    ]
    normalized_names = [
        filename.casefold()
        for filename
        in filenames
    ]
    if len(normalized_names) != len(
        set(normalized_names)
    ):
        raise ValueError(
            "Lote processado contém "
            "nomes de CSV duplicados."
        )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix=".processed_stage_",
        dir=directory,
    ) as temporary:
        stage_root = Path(
            temporary
        )
        staged: list[
            Path
        ] = []

        for _, outputs in (
            prepared_batches
        ):
            for filename, frame in outputs:
                target = (
                    stage_root
                    / filename
                )
                frame.to_csv(
                    target,
                    index=False,
                    encoding="utf-8",
                )
                staged.append(
                    target
                )

        backup_root = (
            stage_root
            / "backup"
        )
        backup_root.mkdir()

        existing_files: list[
            Path
        ] = []
        for scope in history_scopes:
            existing_files.extend(
                _processed_scope_files(
                    directory,
                    scope,
                )
            )

        backed_up: list[
            tuple[
                Path,
                Path,
            ]
        ] = []
        installed: list[
            Path
        ] = []

        try:
            for existing in existing_files:
                backup = (
                    backup_root
                    / existing.name
                )
                shutil.move(
                    str(existing),
                    str(backup),
                )
                backed_up.append(
                    (
                        existing,
                        backup,
                    )
                )

            outputs: list[
                Path
            ] = []
            for staged_file in staged:
                destination = (
                    directory
                    / staged_file.name
                )
                if (
                    destination.exists()
                    and destination
                    not in existing_files
                ):
                    raise FileExistsError(
                        "Saída processada já existe "
                        "fora do escopo substituído: "
                        f"{destination.name}"
                    )

                shutil.move(
                    str(staged_file),
                    str(destination),
                )
                installed.append(
                    destination
                )
                outputs.append(
                    destination
                )

            return outputs
        except Exception:
            for path in reversed(
                installed
            ):
                if path.exists():
                    path.unlink()

            for original, backup in reversed(
                backed_up
            ):
                if backup.exists():
                    shutil.move(
                        str(backup),
                        str(original),
                    )
            raise


def transform_workbook(
    path: Path,
) -> list[Path]:
    scope, prepared = (
        _prepare_workbook_outputs(
            path
        )
    )
    return _replace_processed_batch(
        PROCESSED_DIR,
        [
            (
                scope,
                prepared,
            )
        ],
    )


def transform_workbooks(
    paths: list[Path],
) -> list[Path]:
    prepared_batches = [
        _prepare_workbook_outputs(
            path
        )
        for path in paths
    ]
    return _replace_processed_batch(
        PROCESSED_DIR,
        prepared_batches,
    )

def main() -> None:
    excel_files = (
        verified_history_files(
            RAW_DIR
        )
    )

    outputs = transform_workbooks(
        excel_files
    )
    for output in outputs:
        print(
            "Gerado: "
            f"{output.relative_to(PROCESSED_DIR.parent.parent)}"
        )

    print(
        f"\nTabelas processadas: {len(outputs)}"
    )


if __name__ == "__main__":
    main()
