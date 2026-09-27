from __future__ import annotations

import pandas as pd

from .atomic_outputs import replace_csv_batch
from .config import PROCESSED_DIR
from .consolidate import OUTPUT_NAME
from .quality import build_quality_report

MODEL_DIR = PROCESSED_DIR / "model"

LOCATION_COLUMNS = [
    "nivel_geografico",
    "regiao",
    "uf",
    "estado",
    "municipio",
]

AGGREGATE_MODEL_REQUIRED_COLUMNS = {
    "data_inicial",
    "produto",
    "nivel_geografico",
    "preco_medio_revenda",
    "fonte_arquivo",
    "fonte_planilha",
}

FACT_METRICS = [
    "postos_pesquisados",
    "unidade_medida",
    "preco_medio_revenda",
    "preco_minimo_revenda",
    "preco_maximo_revenda",
    "desvio_padrao_revenda",
    "coef_variacao_revenda",
    "fonte_arquivo",
    "fonte_planilha",
]


def _normalized_text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def build_star_schema(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    required = (
        AGGREGATE_MODEL_REQUIRED_COLUMNS
    )
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes: " + ", ".join(sorted(missing))
        )

    for column in (
        "fonte_arquivo",
        "fonte_planilha",
    ):
        provenance = (
            frame[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        if provenance.isna().any():
            raise ValueError(
                f"A coluna {column} deve estar "
                "preenchida em todas as observações "
                "do modelo agregado."
            )

    working = frame.copy()
    working["data_inicial"] = pd.to_datetime(
        working["data_inicial"], errors="coerce"
    )

    if "data_final" in working.columns:
        working["data_final"] = pd.to_datetime(
            working["data_final"], errors="coerce"
        )
    else:
        working["data_final"] = working["data_inicial"]

    dim_data = (
        working[["data_inicial", "data_final"]]
        .drop_duplicates()
        .sort_values(["data_inicial", "data_final"], kind="stable")
        .reset_index(drop=True)
    )
    dim_data.insert(0, "data_id", range(1, len(dim_data) + 1))
    dim_data["ano"] = dim_data["data_inicial"].dt.year.astype("Int64")
    dim_data["mes"] = dim_data["data_inicial"].dt.month.astype("Int64")
    dim_data["semana_iso"] = (
        dim_data["data_inicial"].dt.isocalendar().week.astype("Int64")
    )
    dim_data["trimestre"] = (
        dim_data["data_inicial"].dt.quarter.astype("Int64")
    )

    dim_produto = (
        pd.DataFrame({"produto": _normalized_text(working["produto"])})
        .drop_duplicates()
        .sort_values("produto", kind="stable")
        .reset_index(drop=True)
    )
    dim_produto.insert(0, "produto_id", range(1, len(dim_produto) + 1))

    for column in LOCATION_COLUMNS:
        if column not in working.columns:
            working[column] = ""
        working[column] = _normalized_text(working[column])

    working["nivel_geografico"] = (
        working["nivel_geografico"]
        .str.lower()
    )
    working["uf"] = (
        working["uf"]
        .str.upper()
    )

    dim_localidade = (
        working[LOCATION_COLUMNS]
        .drop_duplicates()
        .sort_values(LOCATION_COLUMNS, kind="stable")
        .reset_index(drop=True)
    )
    dim_localidade.insert(
        0, "localidade_id", range(1, len(dim_localidade) + 1)
    )

    fact = working.copy()
    fact = fact.merge(
        dim_data,
        on=["data_inicial", "data_final"],
        how="left",
        validate="many_to_one",
    )

    fact["produto"] = _normalized_text(fact["produto"])
    fact = fact.merge(
        dim_produto,
        on="produto",
        how="left",
        validate="many_to_one",
    )
    fact = fact.merge(
        dim_localidade,
        on=LOCATION_COLUMNS,
        how="left",
        validate="many_to_one",
    )

    fact_columns = [
        "data_id",
        "produto_id",
        "localidade_id",
    ] + [
        column
        for column in FACT_METRICS
        if column in fact.columns
    ]

    fact = fact[fact_columns].copy()
    fact.insert(0, "preco_fato_id", range(1, len(fact) + 1))

    return {
        "dim_data": dim_data,
        "dim_produto": dim_produto,
        "dim_localidade": dim_localidade,
        "fato_precos_semanais": fact,
    }


def build_validated_star_schema(
    frame: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    report = build_quality_report(
        frame
    )
    if report["status"] != "passed":
        raise ValueError(
            "A série agregada falhou na validação "
            "de qualidade e não pode ser modelada."
        )

    return build_star_schema(
        frame
    )


def main() -> None:
    source = PROCESSED_DIR / OUTPUT_NAME
    if not source.exists():
        raise SystemExit(f"Tabela consolidada não encontrada: {source}")

    frame = pd.read_csv(source, low_memory=False)
    try:
        tables = build_validated_star_schema(
            frame
        )
    except ValueError as exc:
        raise SystemExit(
            str(exc)
        ) from exc

    outputs = replace_csv_batch(
        MODEL_DIR,
        tables,
    )

    for output in outputs:
        name = output.stem
        table = tables[name]
        print(
            f"{name}: {len(table):,} linhas -> "
            f"{output.relative_to(PROCESSED_DIR.parent.parent)}"
        )


if __name__ == "__main__":
    main()
