from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR, RAW_OPEN_DATA_DIR

STATION_OUTPUT = PROCESSED_DIR / "precos_postos_2026.csv"
STATION_MODEL_DIR = PROCESSED_DIR / "model_postos"

COLUMN_ALIASES = {
    "regiao_sigla": "regiao",
    "estado_sigla": "uf",
    "municipio": "municipio",
    "revenda": "revenda",
    "cnpj_da_revenda": "cnpj_revenda",
    "nome_da_rua": "logradouro",
    "numero_rua": "numero",
    "complemento": "complemento",
    "bairro": "bairro",
    "cep": "cep",
    "produto": "produto",
    "data_da_coleta": "data_coleta",
    "valor_de_venda": "preco_revenda",
    "valor_de_compra": "preco_compra",
    "unidade_de_medida": "unidade_medida",
    "bandeira": "bandeira",
}

BUSINESS_KEY = [
    "data_coleta",
    "_posto_identidade",
    "produto",
    "unidade_medida",
    "preco_revenda",
]

FALLBACK_STATION_COLUMNS = [
    "uf",
    "municipio",
    "revenda",
    "logradouro",
    "numero",
]


def _normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(
        char for char in text if not unicodedata.combining(char)
    )
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return COLUMN_ALIASES.get(text, text)


def _parse_decimal(series: pd.Series) -> pd.Series:
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


def station_identity(frame: pd.DataFrame) -> pd.Series:
    index = frame.index

    if "cnpj_revenda" in frame.columns:
        cnpj = (
            frame["cnpj_revenda"]
            .astype("string")
            .str.replace(r"\D", "", regex=True)
            .str.strip()
        )
        cnpj = cnpj.mask(cnpj.eq(""))
    else:
        cnpj = pd.Series(pd.NA, index=index, dtype="string")

    fallback_parts: list[pd.Series] = []
    for column in FALLBACK_STATION_COLUMNS:
        if column in frame.columns:
            values = (
                frame[column]
                .astype("string")
                .fillna("")
                .str.strip()
                .str.upper()
            )
        else:
            values = pd.Series("", index=index, dtype="string")
        fallback_parts.append(values)

    fallback = fallback_parts[0]
    for part in fallback_parts[1:]:
        fallback = fallback.str.cat(part, sep="|")

    identity = pd.Series(
        "cnpj:" + cnpj,
        index=index,
        dtype="string",
    )
    identity = identity.mask(
        cnpj.isna(),
        "fallback:" + fallback,
    )
    return identity


def deduplicate_station_rows(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["_posto_identidade"] = station_identity(working)

    keys = [
        key
        for key in BUSINESS_KEY
        if key in working.columns
    ]
    working = working.drop_duplicates(
        subset=keys,
        keep="last",
    )
    return working.drop(
        columns=["_posto_identidade"],
        errors="ignore",
    )


def _read_csv(path: Path) -> pd.DataFrame:
    attempts = [
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "latin-1"},
        {"sep": ",", "encoding": "utf-8-sig"},
    ]

    for options in attempts:
        try:
            frame = pd.read_csv(
                path,
                low_memory=False,
                **options,
            )
            if frame.shape[1] >= 10:
                return frame
        except UnicodeDecodeError:
            continue

    raise ValueError(
        f"Não foi possível interpretar {path.name} como CSV da ANP."
    )


def transform_station_file(path: Path) -> pd.DataFrame:
    frame = _read_csv(path)
    frame.columns = [
        _normalize_name(column)
        for column in frame.columns
    ]

    required = {
        "uf",
        "municipio",
        "produto",
        "data_coleta",
        "preco_revenda",
        "unidade_medida",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"{path.name}: colunas obrigatórias ausentes: "
            f"{sorted(missing)}"
        )

    frame["data_coleta"] = pd.to_datetime(
        frame["data_coleta"],
        errors="coerce",
        dayfirst=True,
    )
    frame["preco_revenda"] = _parse_decimal(
        frame["preco_revenda"]
    )

    if "preco_compra" in frame.columns:
        frame["preco_compra"] = _parse_decimal(
            frame["preco_compra"]
        )

    for column in (
        "regiao",
        "uf",
        "municipio",
        "revenda",
        "cnpj_revenda",
        "produto",
        "unidade_medida",
        "bandeira",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
    ):
        if column in frame.columns:
            frame[column] = (
                frame[column]
                .astype("string")
                .str.strip()
            )

    frame = frame.loc[
        frame["data_coleta"].dt.year.eq(2026)
    ].copy()
    frame = frame.dropna(
        subset=["data_coleta", "preco_revenda"]
    )
    frame = frame.loc[
        frame["preco_revenda"].gt(0)
    ].copy()
    frame["fonte_arquivo"] = path.name

    return frame


def consolidate_station_data(
    directory: Path = RAW_OPEN_DATA_DIR,
) -> pd.DataFrame:
    files = sorted(directory.rglob("*.csv"))
    if not files:
        raise RuntimeError(
            "Nenhum CSV de preços por posto encontrado."
        )

    frames = [
        transform_station_file(path)
        for path in files
    ]
    combined = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )

    combined = deduplicate_station_rows(combined)

    sort_candidates = [
        "data_coleta",
        "uf",
        "municipio",
        "produto",
        "cnpj_revenda",
        "revenda",
    ]
    sort_columns = [
        column
        for column in sort_candidates
        if column in combined.columns
    ]

    return combined.sort_values(
        sort_columns,
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)


def build_station_star_schema(
    frame: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    working = frame.copy()

    dim_data = pd.DataFrame(
        {
            "data_coleta": sorted(
                working["data_coleta"]
                .dropna()
                .unique()
            )
        }
    )
    dim_data.insert(
        0,
        "data_coleta_id",
        range(1, len(dim_data) + 1),
    )
    date_values = pd.to_datetime(
        dim_data["data_coleta"]
    )
    dim_data["ano"] = date_values.dt.year
    dim_data["mes"] = date_values.dt.month
    dim_data["semana_iso"] = (
        date_values.dt.isocalendar().week.astype("Int64")
    )

    dim_produto = (
        working[["produto", "unidade_medida"]]
        .drop_duplicates()
        .sort_values(
            ["produto", "unidade_medida"],
            kind="stable",
        )
        .reset_index(drop=True)
    )
    dim_produto.insert(
        0,
        "produto_posto_id",
        range(1, len(dim_produto) + 1),
    )

    posto_cols = [
        column
        for column in [
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
        ]
        if column in working.columns
    ]
    sort_cols = [
        column
        for column in ["uf", "municipio", "cnpj_revenda", "revenda"]
        if column in posto_cols
    ]

    dim_posto = (
        working[posto_cols]
        .drop_duplicates()
        .sort_values(sort_cols, kind="stable")
        .reset_index(drop=True)
    )
    dim_posto.insert(
        0,
        "posto_id",
        range(1, len(dim_posto) + 1),
    )

    fact = working.merge(
        dim_data,
        on="data_coleta",
        how="left",
        validate="many_to_one",
    )
    fact = fact.merge(
        dim_produto,
        on=["produto", "unidade_medida"],
        how="left",
        validate="many_to_one",
    )
    fact = fact.merge(
        dim_posto,
        on=posto_cols,
        how="left",
        validate="many_to_one",
    )

    fact_columns = [
        "data_coleta_id",
        "produto_posto_id",
        "posto_id",
        "preco_revenda",
    ]
    if "preco_compra" in fact.columns:
        fact_columns.append("preco_compra")
    fact_columns.append("fonte_arquivo")

    fact = fact[fact_columns].copy()
    fact.insert(
        0,
        "preco_posto_id",
        range(1, len(fact) + 1),
    )

    return {
        "dim_data_coleta": dim_data,
        "dim_produto_posto": dim_produto,
        "dim_posto": dim_posto,
        "fato_precos_postos": fact,
    }


def main() -> None:
    frame = consolidate_station_data()

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    frame.to_csv(
        STATION_OUTPUT,
        index=False,
        encoding="utf-8",
    )

    STATION_MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    for name, table in build_station_star_schema(frame).items():
        table.to_csv(
            STATION_MODEL_DIR / f"{name}.csv",
            index=False,
            encoding="utf-8",
        )
        print(f"{name}: {len(table):,} linhas")

    print(f"Observações por posto: {len(frame):,}")


if __name__ == "__main__":
    main()
