from __future__ import annotations

import json
import unicodedata

import pandas as pd

from .atomic_outputs import (
    replace_text_file,
)
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


def normalize_geographic_level(
    series: pd.Series,
) -> pd.Series:
    values = (
        series.astype("string")
        .str.strip()
    )

    def normalize(
        value: object,
    ) -> object:
        if pd.isna(value):
            return pd.NA
        text = unicodedata.normalize(
            "NFKD",
            str(value),
        )
        return "".join(
            char
            for char in text
            if not unicodedata.combining(
                char
            )
        ).casefold()

    return values.map(
        normalize
    ).astype("string")


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
        "empty_dataset": bool(
            frame.empty
        ),
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

    levels = normalize_geographic_level(
        frame["nivel_geografico"]
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

    optional_numeric_columns = (
        "preco_minimo_revenda",
        "preco_maximo_revenda",
        "desvio_padrao_revenda",
        "coef_variacao_revenda",
    )
    parsed_optional: dict[
        str,
        pd.Series,
    ] = {}
    invalid_optional: dict[
        str,
        int,
    ] = {}
    for column in optional_numeric_columns:
        if column not in frame.columns:
            continue
        raw = (
            frame[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        parsed = pd.to_numeric(
            frame[column],
            errors="coerce",
        )
        parsed_optional[column] = parsed
        invalid_optional[column] = int(
            (
                raw.notna()
                & parsed.isna()
            ).sum()
        )

    report[
        "invalid_optional_numeric_rows"
    ] = invalid_optional

    minimum = parsed_optional.get(
        "preco_minimo_revenda"
    )
    maximum = parsed_optional.get(
        "preco_maximo_revenda"
    )
    stddev = parsed_optional.get(
        "desvio_padrao_revenda"
    )
    coefficient = parsed_optional.get(
        "coef_variacao_revenda"
    )

    report[
        "non_positive_min_price_rows"
    ] = int(
        (minimum <= 0)
        .fillna(False)
        .sum()
    ) if minimum is not None else 0
    report[
        "non_positive_max_price_rows"
    ] = int(
        (maximum <= 0)
        .fillna(False)
        .sum()
    ) if maximum is not None else 0
    report[
        "negative_standard_deviation_rows"
    ] = int(
        (stddev < 0)
        .fillna(False)
        .sum()
    ) if stddev is not None else 0
    report[
        "negative_coefficient_variation_rows"
    ] = int(
        (coefficient < 0)
        .fillna(False)
        .sum()
    ) if coefficient is not None else 0

    report["min_greater_than_max_rows"] = (
        int(
            (minimum > maximum)
            .fillna(False)
            .sum()
        )
        if (
            minimum is not None
            and maximum is not None
        )
        else 0
    )
    mean_below_minimum = pd.Series(
        False,
        index=frame.index,
        dtype="boolean",
    )
    if minimum is not None:
        mean_below_minimum = (
            minimum.notna()
            & prices.notna()
            & prices.lt(minimum)
        )

    mean_above_maximum = pd.Series(
        False,
        index=frame.index,
        dtype="boolean",
    )
    if maximum is not None:
        mean_above_maximum = (
            maximum.notna()
            & prices.notna()
            & prices.gt(maximum)
        )

    report[
        "mean_outside_min_max_rows"
    ] = int(
        (
            mean_below_minimum
            | mean_above_maximum
        ).sum()
    )

    if "postos_pesquisados" in frame.columns:
        raw_station_count = (
            frame["postos_pesquisados"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        station_count = pd.to_numeric(
            frame["postos_pesquisados"],
            errors="coerce",
        )
        report[
            "invalid_station_count_rows"
        ] = int(
            (
                raw_station_count.notna()
                & station_count.isna()
            ).sum()
        )
        report[
            "non_integer_station_count_rows"
        ] = int(
            (
                station_count.notna()
                & station_count.mod(1).ne(0)
            ).sum()
        )
        report[
            "negative_station_count_rows"
        ] = int(
            (
                station_count < 0
            ).fillna(False).sum()
        )
    else:
        report[
            "invalid_station_count_rows"
        ] = 0
        report[
            "non_integer_station_count_rows"
        ] = 0
        report[
            "negative_station_count_rows"
        ] = 0

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
        "non_positive_min_price_rows",
        "non_positive_max_price_rows",
        "negative_standard_deviation_rows",
        "negative_coefficient_variation_rows",
        "min_greater_than_max_rows",
        "mean_outside_min_max_rows",
        "invalid_station_count_rows",
        "non_integer_station_count_rows",
        "negative_station_count_rows",
    )

    report["status"] = (
        "passed"
        if (
            not report[
                "empty_dataset"
            ]
            and all(
                report[key] == 0
                for key in blocking_keys
            )
            and all(
                value == 0
                for value in (
                    report[
                        "invalid_optional_numeric_rows"
                    ]
                    .values()
                )
            )
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
    replace_text_file(
        output,
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
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
