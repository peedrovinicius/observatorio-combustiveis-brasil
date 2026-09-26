from __future__ import annotations

import json

import pandas as pd

from .config import REPORTS_DIR
from .station_data import (
    BUSINESS_KEY,
    STATION_OUTPUT,
    station_identity,
)

REQUIRED_COLUMNS = {
    "data_coleta",
    "uf",
    "municipio",
    "produto",
    "preco_revenda",
    "unidade_medida",
}


def build_station_quality_report(
    frame: pd.DataFrame,
) -> dict[str, object]:
    missing_columns = sorted(
        REQUIRED_COLUMNS - set(frame.columns)
    )

    report: dict[str, object] = {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "missing_required_columns": missing_columns,
    }

    if missing_columns:
        report["status"] = "failed"
        return report

    working = frame.copy()
    working["data_coleta"] = pd.to_datetime(
        working["data_coleta"],
        errors="coerce",
    )
    prices = pd.to_numeric(
        working["preco_revenda"],
        errors="coerce",
    )

    report["periodo_inicial"] = (
        working["data_coleta"].min().date().isoformat()
        if working["data_coleta"].notna().any()
        else None
    )
    report["periodo_final"] = (
        working["data_coleta"].max().date().isoformat()
        if working["data_coleta"].notna().any()
        else None
    )
    report["ufs"] = int(working["uf"].dropna().nunique())
    report["municipios"] = int(
        working["municipio"].dropna().nunique()
    )
    report["produtos"] = int(
        working["produto"].dropna().nunique()
    )

    if "cnpj_revenda" in working.columns:
        cnpj = (
            working["cnpj_revenda"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        report["postos_distintos_cnpj"] = int(
            cnpj.dropna().nunique()
        )
        report["cnpj_ausente"] = int(
            cnpj.isna().sum()
        )

    if "bandeira" in working.columns:
        bandeira = (
            working["bandeira"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        report["bandeira_ausente"] = int(
            bandeira.isna().sum()
        )

    report["datas_invalidas"] = int(
        working["data_coleta"].isna().sum()
    )
    report["datas_fora_2026"] = int(
        (
            working["data_coleta"].notna()
            & ~working["data_coleta"].dt.year.eq(2026)
        ).sum()
    )
    report["precos_invalidos"] = int(
        prices.isna().sum()
    )
    report["precos_nao_positivos"] = int(
        (prices <= 0).fillna(False).sum()
    )

    working["_posto_identidade"] = station_identity(
        working
    )
    keys = [
        column
        for column in BUSINESS_KEY
        if column in working.columns
    ]
    report["duplicidades_chave_negocio"] = (
        int(
            working.duplicated(
                subset=keys,
                keep=False,
            ).sum()
        )
        if keys
        else 0
    )

    required_nulls: dict[str, int] = {}
    for column in sorted(
        REQUIRED_COLUMNS - {"preco_revenda"}
    ):
        values = (
            working[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        required_nulls[column] = int(
            values.isna().sum()
        )

    report["nulos_campos_obrigatorios"] = (
        required_nulls
    )

    blocking_issues = [
        report["datas_invalidas"],
        report["datas_fora_2026"],
        report["precos_invalidos"],
        report["precos_nao_positivos"],
        report["duplicidades_chave_negocio"],
        *required_nulls.values(),
    ]

    report["status"] = (
        "passed"
        if all(value == 0 for value in blocking_issues)
        else "review"
    )

    return report


def main() -> None:
    if not STATION_OUTPUT.exists():
        raise SystemExit(
            "Base por posto não encontrada. "
            "Execute python -m src.station_data."
        )

    frame = pd.read_csv(
        STATION_OUTPUT,
        low_memory=False,
    )
    report = build_station_quality_report(frame)

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    output = REPORTS_DIR / "quality_postos_2026.json"
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
