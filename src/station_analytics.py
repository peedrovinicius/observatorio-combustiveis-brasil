from __future__ import annotations

import pandas as pd

from .atomic_outputs import replace_csv_batch
from .config import PROCESSED_DIR
from .station_data import (
    STATION_OUTPUT,
    station_identity,
)
from .station_quality import (
    build_station_quality_report,
)

STATION_ANALYTICS_DIR = (
    PROCESSED_DIR / "analytics_postos"
)

COVERAGE_COLUMNS = [
    "produto",
    "unidade_medida",
    "periodo_inicial",
    "periodo_final",
    "observacoes",
    "postos_distintos",
    "municipios",
    "ufs",
    "preco_medio_observado",
    "mediana_observada",
    "preco_minimo_observado",
    "preco_maximo_observado",
]

MUNICIPAL_DISTRIBUTION_COLUMNS = [
    "data_coleta",
    "produto",
    "unidade_medida",
    "uf",
    "municipio",
    "observacoes",
    "postos_distintos",
    "preco_medio_observado",
    "mediana_observada",
    "preco_minimo_observado",
    "preco_maximo_observado",
    "q1",
    "q3",
    "intervalo_interquartil",
    "desvio_padrao",
    "coef_variacao_pct",
]

BRAND_COLUMNS = [
    "data_coleta",
    "produto",
    "unidade_medida",
    "bandeira",
    "observacoes",
    "postos_distintos",
    "preco_medio_observado",
    "mediana_observada",
    "preco_minimo_observado",
    "preco_maximo_observado",
    "desvio_padrao",
    "amostra_suficiente",
]


def _prepare_station(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "data_coleta",
        "uf",
        "municipio",
        "produto",
        "unidade_medida",
        "preco_revenda",
    }
    missing = required - set(
        frame.columns
    )
    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            "na base por posto: "
            + ", ".join(
                sorted(missing)
            )
        )

    working = frame.copy()
    working["data_coleta"] = pd.to_datetime(
        working["data_coleta"],
        errors="coerce",
    )
    working["preco_revenda"] = pd.to_numeric(
        working["preco_revenda"],
        errors="coerce",
    )

    for column in (
        "uf",
        "municipio",
        "produto",
        "unidade_medida",
        "bandeira",
    ):
        if column in working.columns:
            working[column] = (
                working[column]
                .astype("string")
                .str.strip()
            )

    working = working.dropna(
        subset=[
            "data_coleta",
            "uf",
            "municipio",
            "produto",
            "unidade_medida",
            "preco_revenda",
        ]
    )
    working = working.loc[
        working[
            "data_coleta"
        ].dt.year.eq(2026)
        & working[
            "preco_revenda"
        ].gt(0)
    ].copy()

    working[
        "_posto_identidade"
    ] = station_identity(
        working
    )
    return working


def _latest_by_product_unit(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    latest = (
        frame.groupby(
            [
                "produto",
                "unidade_medida",
            ],
            dropna=False,
        )["data_coleta"]
        .transform("max")
    )
    return frame.loc[
        frame["data_coleta"].eq(
            latest
        )
    ].copy()


def build_station_coverage(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = _prepare_station(
        frame
    )
    if working.empty:
        return pd.DataFrame(
            columns=COVERAGE_COLUMNS
        )

    grouped = (
        working.groupby(
            [
                "produto",
                "unidade_medida",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            periodo_inicial=(
                "data_coleta",
                "min",
            ),
            periodo_final=(
                "data_coleta",
                "max",
            ),
            observacoes=(
                "preco_revenda",
                "size",
            ),
            postos_distintos=(
                "_posto_identidade",
                "nunique",
            ),
            municipios=(
                "municipio",
                "nunique",
            ),
            ufs=(
                "uf",
                "nunique",
            ),
            preco_medio_observado=(
                "preco_revenda",
                "mean",
            ),
            mediana_observada=(
                "preco_revenda",
                "median",
            ),
            preco_minimo_observado=(
                "preco_revenda",
                "min",
            ),
            preco_maximo_observado=(
                "preco_revenda",
                "max",
            ),
        )
    )

    return grouped[
        COVERAGE_COLUMNS
    ].sort_values(
        [
            "produto",
            "unidade_medida",
        ],
        kind="stable",
    ).reset_index(drop=True)


def build_latest_municipality_distribution(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = _latest_by_product_unit(
        _prepare_station(frame)
    )
    if working.empty:
        return pd.DataFrame(
            columns=(
                MUNICIPAL_DISTRIBUTION_COLUMNS
            )
        )

    grouped = (
        working.groupby(
            [
                "data_coleta",
                "produto",
                "unidade_medida",
                "uf",
                "municipio",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            observacoes=(
                "preco_revenda",
                "size",
            ),
            postos_distintos=(
                "_posto_identidade",
                "nunique",
            ),
            preco_medio_observado=(
                "preco_revenda",
                "mean",
            ),
            mediana_observada=(
                "preco_revenda",
                "median",
            ),
            preco_minimo_observado=(
                "preco_revenda",
                "min",
            ),
            preco_maximo_observado=(
                "preco_revenda",
                "max",
            ),
            q1=(
                "preco_revenda",
                lambda values: values.quantile(
                    0.25
                ),
            ),
            q3=(
                "preco_revenda",
                lambda values: values.quantile(
                    0.75
                ),
            ),
            desvio_padrao=(
                "preco_revenda",
                "std",
            ),
        )
    )

    grouped[
        "intervalo_interquartil"
    ] = (
        grouped["q3"]
        - grouped["q1"]
    )
    grouped[
        "coef_variacao_pct"
    ] = (
        100
        * grouped[
            "desvio_padrao"
        ]
        / grouped[
            "preco_medio_observado"
        ]
    )

    return grouped[
        MUNICIPAL_DISTRIBUTION_COLUMNS
    ].sort_values(
        [
            "produto",
            "uf",
            "municipio",
        ],
        kind="stable",
    ).reset_index(drop=True)


def build_latest_brand_summary(
    frame: pd.DataFrame,
    min_observations: int = 5,
    min_stations: int = 3,
) -> pd.DataFrame:
    working = _latest_by_product_unit(
        _prepare_station(frame)
    )
    if working.empty:
        return pd.DataFrame(
            columns=BRAND_COLUMNS
        )

    if "bandeira" not in working.columns:
        working["bandeira"] = (
            "NÃO INFORMADA"
        )
    else:
        working["bandeira"] = (
            working["bandeira"]
            .replace("", pd.NA)
            .fillna("NÃO INFORMADA")
        )

    grouped = (
        working.groupby(
            [
                "data_coleta",
                "produto",
                "unidade_medida",
                "bandeira",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            observacoes=(
                "preco_revenda",
                "size",
            ),
            postos_distintos=(
                "_posto_identidade",
                "nunique",
            ),
            preco_medio_observado=(
                "preco_revenda",
                "mean",
            ),
            mediana_observada=(
                "preco_revenda",
                "median",
            ),
            preco_minimo_observado=(
                "preco_revenda",
                "min",
            ),
            preco_maximo_observado=(
                "preco_revenda",
                "max",
            ),
            desvio_padrao=(
                "preco_revenda",
                "std",
            ),
        )
    )

    grouped[
        "amostra_suficiente"
    ] = (
        grouped[
            "observacoes"
        ].ge(min_observations)
        & grouped[
            "postos_distintos"
        ].ge(min_stations)
    )

    return grouped[
        BRAND_COLUMNS
    ].sort_values(
        [
            "produto",
            "amostra_suficiente",
            "preco_medio_observado",
        ],
        ascending=[
            True,
            False,
            True,
        ],
        kind="stable",
    ).reset_index(drop=True)


def build_station_analytics_exports(
    frame: pd.DataFrame,
) -> dict[
    str,
    pd.DataFrame,
]:
    return {
        "resumo_postos_2026": (
            build_station_coverage(
                frame
            )
        ),
        "distribuicao_municipios_ultima_coleta": (
            build_latest_municipality_distribution(
                frame
            )
        ),
        "bandeiras_ultima_coleta": (
            build_latest_brand_summary(
                frame
            )
        ),
    }


def build_validated_station_analytics_exports(
    frame: pd.DataFrame,
) -> dict[
    str,
    pd.DataFrame,
]:
    report = (
        build_station_quality_report(
            frame
        )
    )
    if report["status"] != "passed":
        raise ValueError(
            "A base por posto falhou na validação "
            "de qualidade e não pode gerar analytics."
        )

    return (
        build_station_analytics_exports(
            frame
        )
    )


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
    try:
        exports = (
            build_validated_station_analytics_exports(
                frame
            )
        )
    except ValueError as exc:
        raise SystemExit(
            str(exc)
        ) from exc

    outputs = replace_csv_batch(
        STATION_ANALYTICS_DIR,
        exports,
    )

    for output in outputs:
        name = output.stem
        table = exports[name]
        print(
            f"{name}: "
            f"{len(table):,} linhas"
        )


if __name__ == "__main__":
    main()
