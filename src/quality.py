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


def build_quality_report(frame: pd.DataFrame) -> dict[str, object]:
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))

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

    prices = pd.to_numeric(frame["preco_medio_revenda"], errors="coerce")
    report["invalid_price_rows"] = int(prices.isna().sum())
    report["non_positive_price_rows"] = int((prices <= 0).fillna(False).sum())

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
        int(frame.duplicated(subset=duplicate_keys, keep=False).sum())
        if duplicate_keys
        else 0
    )

    range_inconsistencies = 0
    if {"preco_minimo_revenda", "preco_maximo_revenda"}.issubset(frame.columns):
        minimum = pd.to_numeric(frame["preco_minimo_revenda"], errors="coerce")
        maximum = pd.to_numeric(frame["preco_maximo_revenda"], errors="coerce")
        range_inconsistencies = int((minimum > maximum).fillna(False).sum())
    report["min_greater_than_max_rows"] = range_inconsistencies

    report["status"] = (
        "passed"
        if all(
            report[key] == 0
            for key in (
                "invalid_price_rows",
                "non_positive_price_rows",
                "duplicate_rows_by_business_key",
                "min_greater_than_max_rows",
            )
        )
        else "review"
    )
    return report


def main() -> None:
    source = PROCESSED_DIR / OUTPUT_NAME
    if not source.exists():
        raise SystemExit(
            f"Tabela não encontrada: {source}. Execute python -m src.consolidate."
        )

    frame = pd.read_csv(source, low_memory=False)
    report = build_quality_report(frame)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output = REPORTS_DIR / "quality_2026.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
