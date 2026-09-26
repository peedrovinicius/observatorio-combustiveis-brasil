from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR, RAW_DIR

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


def transform_workbook(path: Path) -> list[Path]:
    workbook = pd.ExcelFile(path)
    outputs: list[Path] = []

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for sheet_name in workbook.sheet_names:
        try:
            frame = read_excel_sheet(path, sheet_name)
        except ValueError:
            continue

        if frame.empty:
            continue

        safe_sheet = re.sub(r"[^A-Za-z0-9_-]+", "_", sheet_name).strip("_").lower()
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_").lower()
        output = PROCESSED_DIR / f"{stem}__{safe_sheet}.csv"
        frame.to_csv(output, index=False, encoding="utf-8")
        outputs.append(output)

    if not outputs:
        raise RuntimeError(
            f"Nenhuma tabela reconhecida foi encontrada em {path.name}."
        )

    return outputs


def main() -> None:
    excel_files = sorted(
        path
        for path in RAW_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".xlsx", ".xls"}
    )

    if not excel_files:
        raise SystemExit(
            "Nenhuma planilha encontrada em data/raw. "
            "Execute primeiro: python -m src.download_history"
        )

    total = 0
    for path in excel_files:
        outputs = transform_workbook(path)
        for output in outputs:
            total += 1
            print(f"Gerado: {output.relative_to(PROCESSED_DIR.parent.parent)}")

    print(f"\nTabelas processadas: {total}")


if __name__ == "__main__":
    main()
