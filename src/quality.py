from __future__ import annotations

import json

import pandas as pd

from .config import PROCESSED_DIR, REPORTS_DIR
from .consolidate import OUTPUT_NAME

REQUIRED_COLUMNS = {
    "data_inicial",
    "produto",
    "preco_medio_revenda",
    "nivel_geografico",
}

VALID_LEVELS = {
    "brasil",
    "regiao",
    "estado",
    "municipio",
}


def _blank_count(series: pd.Series) -> int:
    values = (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
    )
    return int(values.isna().sum())


def _nonblank_mask(
    frame: pd.DataFrame,
    column: str,
) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(
            False,
            index=frame.index,
            dtype="boolean",
        )

    return (
        frame[column]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
        .notna()
    )


def build_quality_report(
    frame: pd.DataFrame,
) -> dict[str, object]:
    missing_columns = sorted(
        REQUIRED_COLUMNS - set(frame.columns)
    )

    report: dict[str, object] = {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "missing_required_columns": missing_columns,
        "nulls": {
            column: int(value)
            for column, value in frame.isna().sum().items()
        },
    }

    if missing_columns:
        report["status"] = "failed"
        return report

    start_dates = pd.to_datetime(
        frame["data_inicial"],
        errors="coerce",
    )
    report["invalid_start_date_rows"] = int(
        start_dates.isna().sum()
    )
    report["outside_2026_rows"] = int(
        (
            start_dates.notna()
            & ~start_dates.dt.year.eq(2026)
        ).sum()
    )

    if "data_final" in frame.columns:
        end_dates = pd.to_datetime(
            frame["data_final"],
            errors="coerce",
        )
        report["invalid_end_date_rows"] = int(
            end_dates.isna().sum()
        )
        report["end_before_start_rows"] = int(
            (
                start_dates.notna()
                & end_dates.notna()
                & end_dates.lt(start_dates)
            ).sum()
        )
    else:
        report["invalid_end_date_rows"] = 0
        report["end_before_start_rows"] = 0

    report["blank_product_rows"] = _blank_count(
        frame["produto"]
    )

    levels = (
        frame["nivel_geografico"]
        .astype("string")
        .str.strip()
        .str.lower()
    )
    report["invalid_geographic_level_rows"] = int(
        (
            levels.isna()
            | levels.eq("")
            | ~levels.isin(VALID_LEVELS)
        ).sum()
    )

    has_region = _nonblank_mask(
        frame,
        "regiao",
    )
    has_uf = _nonblank_mask(
        frame,
        "uf",
    )
    has_state = _nonblank_mask(
        frame,
        "estado",
    )
    has_municipality = _nonblank_mask(
        frame,
        "municipio",
    )
    has_state_identity = (
        has_uf
        | has_state
    )

    report["missing_region_identifier_rows"] = int(
        (
            levels.eq("regiao")
            & ~has_region
        ).sum()
    )
    report["missing_state_identifier_rows"] = int(
        (
            levels.eq("estado")
            & ~has_state_identity
        ).sum()
    )
    report[
        "missing_municipality_identifier_rows"
    ] = int(
        (
            levels.eq("municipio")
            & ~has_municipality
        ).sum()
    )
    report[
        "missing_municipality_state_identifier_rows"
    ] = int(
        (
            levels.eq("municipio")
            & ~has_state_identity
        ).sum()
    )

    prices = pd.to_numeric(
        frame["preco_medio_revenda"],
        errors="coerce",
    )
    report["invalid_price_rows"] = int(
        prices.isna().sum()
    )
    report["non_positive_price_rows"] = int(
        (prices <= 0).fillna(False).sum()
    )

    duplicate_keys = [
        column
        for column in (
            "data_inicial",
            "data_final",
            "nivel_geografico",
            "regiao",
            "uf",
            "estado",
            "municipio",
            "produto",
            "unidade_medida",
        )
        if column in frame.columns
    ]
    report["duplicate_rows_by_business_key"] = (
        int(
            frame.duplicated(
                subset=duplicate_keys,
                keep=False,
            ).sum()
        )
        if duplicate_keys
        else 0
    )

    range_inconsistencies = 0
    if {
        "preco_minimo_revenda",
        "preco_maximo_revenda",
    }.issubset(frame.columns):
        minimum = pd.to_numeric(
            frame["preco_minimo_revenda"],
            errors="coerce",
        )
        maximum = pd.to_numeric(
            frame["preco_maximo_revenda"],
            errors="coerce",
        )
        range_inconsistencies = int(
            (minimum > maximum)
            .fillna(False)
            .sum()
        )
    report["min_greater_than_max_rows"] = (
        range_inconsistencies
    )

    blocking_keys = (
        "invalid_start_date_rows",
        "outside_2026_rows",
        "invalid_end_date_rows",
        "end_before_start_rows",
        "blank_product_rows",
        "invalid_geographic_level_rows",
        "missing_region_identifier_rows",
        "missing_state_identifier_rows",
        "missing_municipality_identifier_rows",
        "missing_municipality_state_identifier_rows",
        "invalid_price_rows",
        "non_positive_price_rows",
        "duplicate_rows_by_business_key",
        "min_greater_than_max_rows",
    )

    report["status"] = (
        "passed"
        if all(
            report[key] == 0
            for key in blocking_keys
        )
        else "failed"
    )
    return report


def main() -> None:
    source = PROCESSED_DIR / OUTPUT_NAME
    if not source.exists():
        raise SystemExit(
            f"Tabela não encontrada: {source}. "
            "Execute python -m src.consolidate."
        )

    frame = pd.read_csv(
        source,
        low_memory=False,
    )
    report = build_quality_report(frame)

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    output = REPORTS_DIR / "quality_2026.json"
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
