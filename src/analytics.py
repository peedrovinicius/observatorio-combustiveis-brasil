from __future__ import annotations

import pandas as pd

from .atomic_outputs import replace_csv_batch
from .config import PROCESSED_DIR
from .consolidate import OUTPUT_NAME
from .quality import build_quality_report

ANALYTICS_DIR = PROCESSED_DIR / "analytics"

KPI_COLUMNS = [
    "produto",
    "unidade_medida",
    "ultima_semana_inicio",
    "ultima_semana_fim",
    "preco_atual",
    "preco_semana_anterior",
    "variacao_semanal_pct",
    "primeiro_preco_2026",
    "variacao_desde_inicio_ano_pct",
    "menor_preco_2026",
    "maior_preco_2026",
    "semanas_observadas",
]

MONTHLY_COLUMNS = [
    "ano",
    "mes",
    "produto",
    "unidade_medida",
    "media_das_semanas",
    "menor_semana",
    "maior_semana",
    "semanas_observadas",
    "variacao_mensal_pct",
]

STATE_RANKING_COLUMNS = [
    "data_inicial",
    "data_final",
    "uf",
    "estado",
    "produto",
    "unidade_medida",
    "postos_pesquisados",
    "preco_medio_revenda",
    "preco_minimo_revenda",
    "preco_maximo_revenda",
    "coef_variacao_revenda",
    "ranking_mais_caro",
    "ranking_mais_barato",
]

CITY_RANKING_COLUMNS = [
    "data_inicial",
    "data_final",
    "uf",
    "municipio",
    "produto",
    "unidade_medida",
    "postos_pesquisados",
    "preco_medio_revenda",
    "preco_minimo_revenda",
    "preco_maximo_revenda",
    "coef_variacao_revenda",
    "ranking_mais_caro",
    "ranking_mais_barato",
]

RATIO_COLUMNS = [
    "data_inicial",
    "uf",
    "municipio",
    "unidade_medida",
    "preco_etanol",
    "preco_gasolina_comum",
    "relacao_etanol_gasolina_pct",
]


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "data_inicial",
        "produto",
        "nivel_geografico",
        "preco_medio_revenda",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(sorted(missing))
        )

    working = frame.copy()
    working["data_inicial"] = pd.to_datetime(
        working["data_inicial"],
        errors="coerce",
    )
    if "data_final" in working.columns:
        working["data_final"] = pd.to_datetime(
            working["data_final"],
            errors="coerce",
        )

    working["produto"] = (
        working["produto"]
        .astype("string")
        .fillna("")
        .str.strip()
        .str.upper()
    )
    if "unidade_medida" in working.columns:
        working["unidade_medida"] = (
            working["unidade_medida"]
            .astype("string")
            .fillna("")
            .str.strip()
        )
    else:
        working["unidade_medida"] = ""
    working["preco_medio_revenda"] = pd.to_numeric(
        working["preco_medio_revenda"],
        errors="coerce",
    )
    return working.dropna(
        subset=["data_inicial", "preco_medio_revenda"]
    )


def _latest_date(frame: pd.DataFrame) -> pd.Timestamp:
    if frame.empty:
        raise ValueError(
            "Não há dados disponíveis para calcular a última data."
        )
    return frame["data_inicial"].max()


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
        )["data_inicial"]
        .transform("max")
    )
    return frame.loc[
        frame["data_inicial"].eq(
            latest
        )
    ].copy()


def build_brazil_kpis(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = _prepare(frame)
    brazil = working.loc[
        working["nivel_geografico"]
        .astype("string")
        .str.lower()
        .eq("brasil")
    ].copy()

    if brazil.empty:
        return pd.DataFrame(columns=KPI_COLUMNS)

    rows: list[dict[str, object]] = []
    for (
        product,
        unit,
    ), group in brazil.groupby(
        [
            "produto",
            "unidade_medida",
        ],
        dropna=False,
    ):
        group = group.sort_values(
            "data_inicial",
            kind="stable",
        )
        if group.empty:
            continue

        latest = group.iloc[-1]
        previous = (
            group.iloc[-2]
            if len(group) > 1
            else None
        )
        first = group.iloc[0]

        current_price = float(
            latest["preco_medio_revenda"]
        )
        previous_price = (
            float(previous["preco_medio_revenda"])
            if previous is not None
            else None
        )
        first_price = float(
            first["preco_medio_revenda"]
        )

        weekly_change = (
            ((current_price / previous_price) - 1) * 100
            if previous_price not in (None, 0)
            else None
        )
        year_change = (
            ((current_price / first_price) - 1) * 100
            if first_price != 0
            else None
        )

        rows.append(
            {
                "produto": product,
                "unidade_medida": unit,
                "ultima_semana_inicio": latest["data_inicial"],
                "ultima_semana_fim": latest.get("data_final"),
                "preco_atual": current_price,
                "preco_semana_anterior": previous_price,
                "variacao_semanal_pct": weekly_change,
                "primeiro_preco_2026": first_price,
                "variacao_desde_inicio_ano_pct": year_change,
                "menor_preco_2026": float(
                    group["preco_medio_revenda"].min()
                ),
                "maior_preco_2026": float(
                    group["preco_medio_revenda"].max()
                ),
                "semanas_observadas": int(
                    group["data_inicial"].nunique()
                ),
            }
        )

    return (
        pd.DataFrame(rows, columns=KPI_COLUMNS)
        .sort_values(
            [
                "produto",
                "unidade_medida",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def build_monthly_brazil(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = _prepare(frame)
    brazil = working.loc[
        working["nivel_geografico"]
        .astype("string")
        .str.lower()
        .eq("brasil")
    ].copy()

    if brazil.empty:
        return pd.DataFrame(columns=MONTHLY_COLUMNS)

    brazil["ano"] = brazil["data_inicial"].dt.year
    brazil["mes"] = brazil["data_inicial"].dt.month

    monthly = (
        brazil.groupby(
            [
                "ano",
                "mes",
                "produto",
                "unidade_medida",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            media_das_semanas=(
                "preco_medio_revenda",
                "mean",
            ),
            menor_semana=(
                "preco_medio_revenda",
                "min",
            ),
            maior_semana=(
                "preco_medio_revenda",
                "max",
            ),
            semanas_observadas=(
                "data_inicial",
                "nunique",
            ),
        )
        .sort_values(
            [
                "produto",
                "unidade_medida",
                "ano",
                "mes",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    monthly["variacao_mensal_pct"] = (
        monthly.groupby(
            [
                "produto",
                "unidade_medida",
            ],
            dropna=False,
        )["media_das_semanas"]
        .pct_change(fill_method=None)
        * 100
    )
    return monthly[MONTHLY_COLUMNS]


def build_latest_state_ranking(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = _prepare(frame)
    states = working.loc[
        working["nivel_geografico"]
        .astype("string")
        .str.lower()
        .eq("estado")
    ].copy()

    if states.empty:
        return pd.DataFrame(
            columns=STATE_RANKING_COLUMNS
        )

    states = _latest_by_product_unit(
        states
    )

    states["ranking_mais_caro"] = (
        states.groupby(
            [
                "produto",
                "unidade_medida",
            ],
            dropna=False,
        )["preco_medio_revenda"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )
    states["ranking_mais_barato"] = (
        states.groupby(
            [
                "produto",
                "unidade_medida",
            ],
            dropna=False,
        )["preco_medio_revenda"]
        .rank(method="min", ascending=True)
        .astype("Int64")
    )

    columns = [
        column
        for column in STATE_RANKING_COLUMNS
        if column in states.columns
    ]
    return (
        states[columns]
        .sort_values(
            [
                "produto",
                "unidade_medida",
                "ranking_mais_caro",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def build_latest_city_ranking(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = _prepare(frame)
    cities = working.loc[
        working["nivel_geografico"]
        .astype("string")
        .str.lower()
        .eq("municipio")
    ].copy()

    if cities.empty:
        return pd.DataFrame(
            columns=CITY_RANKING_COLUMNS
        )

    cities = _latest_by_product_unit(
        cities
    )

    cities["ranking_mais_caro"] = (
        cities.groupby(
            [
                "produto",
                "unidade_medida",
            ],
            dropna=False,
        )["preco_medio_revenda"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )
    cities["ranking_mais_barato"] = (
        cities.groupby(
            [
                "produto",
                "unidade_medida",
            ],
            dropna=False,
        )["preco_medio_revenda"]
        .rank(method="min", ascending=True)
        .astype("Int64")
    )

    columns = [
        column
        for column in CITY_RANKING_COLUMNS
        if column in cities.columns
    ]
    return (
        cities[columns]
        .sort_values(
            [
                "produto",
                "unidade_medida",
                "ranking_mais_caro",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def _classify_fuel(
    product: pd.Series,
) -> pd.Series:
    normalized = (
        product.astype("string").str.upper()
    )
    result = pd.Series(
        pd.NA,
        index=normalized.index,
        dtype="string",
    )

    ethanol = (
        normalized.eq("ETANOL")
        | (
            normalized.str.contains(
                "ETANOL",
                na=False,
            )
            & normalized.str.contains(
                "HIDRAT",
                na=False,
            )
        )
    )
    gasoline = (
        normalized.eq("GASOLINA")
        | (
            normalized.str.contains(
                "GASOLINA",
                na=False,
            )
            & normalized.str.contains(
                "COMUM",
                na=False,
            )
            & ~normalized.str.contains(
                "ADITIV",
                na=False,
            )
        )
    )

    result.loc[ethanol] = "etanol"
    result.loc[gasoline] = "gasolina_comum"
    return result


def build_ethanol_gasoline_ratio(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = _prepare(frame)
    cities = working.loc[
        working["nivel_geografico"]
        .astype("string")
        .str.lower()
        .eq("municipio")
    ].copy()

    if cities.empty:
        return pd.DataFrame(
            columns=RATIO_COLUMNS
        )

    cities["combustivel_comparavel"] = (
        _classify_fuel(
            cities["produto"]
        )
    )
    cities = cities.dropna(
        subset=[
            "combustivel_comparavel"
        ]
    )

    if cities.empty:
        return pd.DataFrame(
            columns=RATIO_COLUMNS
        )

    class_key = [
        "data_inicial",
        *(
            ["uf"]
            if "uf" in cities.columns
            else []
        ),
        *(
            ["municipio"]
            if "municipio"
            in cities.columns
            else []
        ),
        "unidade_medida",
        "combustivel_comparavel",
    ]
    distinct_prices = (
        cities.groupby(
            class_key,
            dropna=False,
        )["preco_medio_revenda"]
        .transform("nunique")
    )
    cities = cities.loc[
        distinct_prices.eq(1)
    ].copy()
    cities = (
        cities.drop_duplicates(
            subset=class_key,
            keep="first",
        )
    )

    if cities.empty:
        return pd.DataFrame(
            columns=RATIO_COLUMNS
        )

    index_columns = [
        column
        for column in [
            "data_inicial",
            "uf",
            "municipio",
            "unidade_medida",
        ]
        if column in cities.columns
    ]

    pivot = (
        cities.pivot_table(
            index=index_columns,
            columns=(
                "combustivel_comparavel"
            ),
            values=(
                "preco_medio_revenda"
            ),
            aggfunc="first",
        )
        .reset_index()
        .rename(
            columns={
                "etanol": "preco_etanol",
                "gasolina_comum": (
                    "preco_gasolina_comum"
                ),
            }
        )
    )

    for column in (
        "preco_etanol",
        "preco_gasolina_comum",
    ):
        if column not in pivot.columns:
            pivot[column] = pd.NA

    pivot = pivot.dropna(
        subset=[
            "preco_etanol",
            "preco_gasolina_comum",
        ]
    ).copy()

    if pivot.empty:
        return pd.DataFrame(
            columns=RATIO_COLUMNS
        )

    location_columns = [
        column
        for column in [
            "uf",
            "municipio",
            "unidade_medida",
        ]
        if column in pivot.columns
    ]
    latest_comparable = (
        pivot.groupby(
            location_columns,
            dropna=False,
        )["data_inicial"]
        .transform("max")
    )
    pivot = pivot.loc[
        pivot["data_inicial"].eq(
            latest_comparable
        )
    ].copy()

    pivot[
        "relacao_etanol_gasolina_pct"
    ] = (
        100
        * pivot["preco_etanol"]
        / pivot[
            "preco_gasolina_comum"
        ]
    )

    return (
        pivot[RATIO_COLUMNS]
        .sort_values(
            [
                "data_inicial",
                "relacao_etanol_gasolina_pct",
            ],
            ascending=[
                False,
                True,
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def build_analytics_exports(
    frame: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    return {
        "kpis_brasil_2026": build_brazil_kpis(
            frame
        ),
        "tendencia_mensal_brasil_2026": (
            build_monthly_brazil(frame)
        ),
        "ranking_ufs_ultima_semana": (
            build_latest_state_ranking(frame)
        ),
        "ranking_municipios_ultima_semana": (
            build_latest_city_ranking(frame)
        ),
        "etanol_gasolina_ultima_semana": (
            build_ethanol_gasoline_ratio(frame)
        ),
    }


def _validate_analytics_provenance(
    frame: pd.DataFrame,
) -> None:
    required = (
        "fonte_arquivo",
        "fonte_planilha",
    )
    missing = [
        column
        for column in required
        if column not in frame.columns
    ]
    if missing:
        raise ValueError(
            "Proveniência obrigatória ausente "
            "nos analytics agregados: "
            + ", ".join(missing)
        )

    for column in required:
        values = (
            frame[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        if values.isna().any():
            raise ValueError(
                "Proveniência obrigatória vazia "
                "nos analytics agregados: "
                f"{column}"
            )


def build_validated_analytics_exports(
    frame: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    _validate_analytics_provenance(
        frame
    )
    report = build_quality_report(
        frame
    )
    if report["status"] != "passed":
        raise ValueError(
            "A série agregada falhou na validação "
            "de qualidade e não pode gerar analytics."
        )

    return build_analytics_exports(
        frame
    )


def main() -> None:
    source = PROCESSED_DIR / OUTPUT_NAME
    if not source.exists():
        raise SystemExit(
            f"Tabela consolidada não encontrada: "
            f"{source}. Execute primeiro "
            "python -m src.consolidate."
        )

    frame = pd.read_csv(
        source,
        low_memory=False,
    )
    try:
        exports = build_validated_analytics_exports(
            frame
        )
    except ValueError as exc:
        raise SystemExit(
            str(exc)
        ) from exc

    outputs = replace_csv_batch(
        ANALYTICS_DIR,
        exports,
    )

    for output in outputs:
        name = output.stem
        table = exports[name]
        print(
            f"{name}: {len(table):,} linhas -> "
            f"{output.relative_to(PROCESSED_DIR.parent.parent)}"
        )


if __name__ == "__main__":
    main()
