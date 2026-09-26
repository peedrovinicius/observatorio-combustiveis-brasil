from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR
from .consolidate import OUTPUT_NAME

ANALYTICS_DIR = PROCESSED_DIR / "analytics"


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
            "Colunas obrigatórias ausentes: " + ", ".join(sorted(missing))
        )

    working = frame.copy()
    working["data_inicial"] = pd.to_datetime(
        working["data_inicial"], errors="coerce"
    )
    if "data_final" in working.columns:
        working["data_final"] = pd.to_datetime(
            working["data_final"], errors="coerce"
        )

    working["produto"] = (
        working["produto"].astype("string").fillna("").str.strip().str.upper()
    )
    working["preco_medio_revenda"] = pd.to_numeric(
        working["preco_medio_revenda"], errors="coerce"
    )
    return working.dropna(subset=["data_inicial", "preco_medio_revenda"])


def _latest_date(frame: pd.DataFrame) -> pd.Timestamp:
    if frame.empty:
        raise ValueError("Não há dados disponíveis para calcular a última data.")
    return frame["data_inicial"].max()


def build_brazil_kpis(frame: pd.DataFrame) -> pd.DataFrame:
    working = _prepare(frame)
    brazil = working.loc[
        working["nivel_geografico"].astype("string").str.lower().eq("brasil")
    ].copy()

    rows: list[dict[str, object]] = []
    for product, group in brazil.groupby("produto", dropna=False):
        group = group.sort_values("data_inicial", kind="stable")
        if group.empty:
            continue

        latest = group.iloc[-1]
        previous = group.iloc[-2] if len(group) > 1 else None
        first = group.iloc[0]

        current_price = float(latest["preco_medio_revenda"])
        previous_price = (
            float(previous["preco_medio_revenda"])
            if previous is not None
            else None
        )
        first_price = float(first["preco_medio_revenda"])

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
                "ultima_semana_inicio": latest["data_inicial"],
                "ultima_semana_fim": latest.get("data_final"),
                "preco_atual": current_price,
                "preco_semana_anterior": previous_price,
                "variacao_semanal_pct": weekly_change,
                "primeiro_preco_2026": first_price,
                "variacao_desde_inicio_ano_pct": year_change,
                "menor_preco_2026": float(group["preco_medio_revenda"].min()),
                "maior_preco_2026": float(group["preco_medio_revenda"].max()),
                "semanas_observadas": int(group["data_inicial"].nunique()),
            }
        )

    return pd.DataFrame(rows).sort_values("produto", kind="stable").reset_index(drop=True)


def build_monthly_brazil(frame: pd.DataFrame) -> pd.DataFrame:
    working = _prepare(frame)
    brazil = working.loc[
        working["nivel_geografico"].astype("string").str.lower().eq("brasil")
    ].copy()

    brazil["ano"] = brazil["data_inicial"].dt.year
    brazil["mes"] = brazil["data_inicial"].dt.month

    monthly = (
        brazil.groupby(["ano", "mes", "produto"], as_index=False)
        .agg(
            media_das_semanas=("preco_medio_revenda", "mean"),
            menor_semana=("preco_medio_revenda", "min"),
            maior_semana=("preco_medio_revenda", "max"),
            semanas_observadas=("data_inicial", "nunique"),
        )
        .sort_values(["produto", "ano", "mes"], kind="stable")
        .reset_index(drop=True)
    )

    monthly["variacao_mensal_pct"] = (
        monthly.groupby("produto")["media_das_semanas"].pct_change(fill_method=None)
        * 100
    )
    return monthly


def build_latest_state_ranking(frame: pd.DataFrame) -> pd.DataFrame:
    working = _prepare(frame)
    states = working.loc[
        working["nivel_geografico"].astype("string").str.lower().eq("estado")
    ].copy()
    latest = _latest_date(states)
    states = states.loc[states["data_inicial"].eq(latest)].copy()

    states["ranking_mais_caro"] = (
        states.groupby("produto")["preco_medio_revenda"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )
    states["ranking_mais_barato"] = (
        states.groupby("produto")["preco_medio_revenda"]
        .rank(method="min", ascending=True)
        .astype("Int64")
    )

    columns = [
        column
        for column in [
            "data_inicial",
            "data_final",
            "uf",
            "estado",
            "produto",
            "postos_pesquisados",
            "preco_medio_revenda",
            "preco_minimo_revenda",
            "preco_maximo_revenda",
            "coef_variacao_revenda",
            "ranking_mais_caro",
            "ranking_mais_barato",
        ]
        if column in states.columns
    ]
    return states[columns].sort_values(
        ["produto", "ranking_mais_caro"], kind="stable"
    ).reset_index(drop=True)


def build_latest_city_ranking(frame: pd.DataFrame) -> pd.DataFrame:
    working = _prepare(frame)
    cities = working.loc[
        working["nivel_geografico"].astype("string").str.lower().eq("municipio")
    ].copy()
    latest = _latest_date(cities)
    cities = cities.loc[cities["data_inicial"].eq(latest)].copy()

    cities["ranking_mais_caro"] = (
        cities.groupby("produto")["preco_medio_revenda"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )
    cities["ranking_mais_barato"] = (
        cities.groupby("produto")["preco_medio_revenda"]
        .rank(method="min", ascending=True)
        .astype("Int64")
    )

    columns = [
        column
        for column in [
            "data_inicial",
            "data_final",
            "uf",
            "municipio",
            "produto",
            "postos_pesquisados",
            "preco_medio_revenda",
            "preco_minimo_revenda",
            "preco_maximo_revenda",
            "coef_variacao_revenda",
            "ranking_mais_caro",
            "ranking_mais_barato",
        ]
        if column in cities.columns
    ]
    return cities[columns].sort_values(
        ["produto", "ranking_mais_caro"], kind="stable"
    ).reset_index(drop=True)


def _classify_fuel(product: pd.Series) -> pd.Series:
    normalized = product.astype("string").str.upper()
    result = pd.Series(pd.NA, index=normalized.index, dtype="string")

    ethanol = normalized.str.contains("ETANOL", na=False)
    gasoline = (
        normalized.str.contains("GASOLINA", na=False)
        & ~normalized.str.contains("ADITIV", na=False)
    )

    result.loc[ethanol] = "etanol"
    result.loc[gasoline] = "gasolina_comum"
    return result


def build_ethanol_gasoline_ratio(frame: pd.DataFrame) -> pd.DataFrame:
    working = _prepare(frame)
    cities = working.loc[
        working["nivel_geografico"].astype("string").str.lower().eq("municipio")
    ].copy()
    latest = _latest_date(cities)
    cities = cities.loc[cities["data_inicial"].eq(latest)].copy()
    cities["combustivel_comparavel"] = _classify_fuel(cities["produto"])
    cities = cities.dropna(subset=["combustivel_comparavel"])

    if cities.empty:
        return pd.DataFrame(
            columns=[
                "data_inicial",
                "uf",
                "municipio",
                "preco_etanol",
                "preco_gasolina_comum",
                "relacao_etanol_gasolina_pct",
            ]
        )

    index_columns = [
        column for column in ["data_inicial", "uf", "municipio"] if column in cities.columns
    ]

    pivot = (
        cities.pivot_table(
            index=index_columns,
            columns="combustivel_comparavel",
            values="preco_medio_revenda",
            aggfunc="first",
        )
        .reset_index()
        .rename(
            columns={
                "etanol": "preco_etanol",
                "gasolina_comum": "preco_gasolina_comum",
            }
        )
    )

    for column in ("preco_etanol", "preco_gasolina_comum"):
        if column not in pivot.columns:
            pivot[column] = pd.NA

    pivot = pivot.dropna(subset=["preco_etanol", "preco_gasolina_comum"]).copy()
    pivot["relacao_etanol_gasolina_pct"] = (
        100 * pivot["preco_etanol"] / pivot["preco_gasolina_comum"]
    )

    return pivot.sort_values(
        "relacao_etanol_gasolina_pct", kind="stable"
    ).reset_index(drop=True)


def build_analytics_exports(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "kpis_brasil_2026": build_brazil_kpis(frame),
        "tendencia_mensal_brasil_2026": build_monthly_brazil(frame),
        "ranking_ufs_ultima_semana": build_latest_state_ranking(frame),
        "ranking_municipios_ultima_semana": build_latest_city_ranking(frame),
        "etanol_gasolina_ultima_semana": build_ethanol_gasoline_ratio(frame),
    }


def main() -> None:
    source = PROCESSED_DIR / OUTPUT_NAME
    if not source.exists():
        raise SystemExit(
            f"Tabela consolidada não encontrada: {source}. "
            "Execute primeiro python -m src.consolidate."
        )

    frame = pd.read_csv(source, low_memory=False)
    exports = build_analytics_exports(frame)

    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    for name, table in exports.items():
        output = ANALYTICS_DIR / f"{name}.csv"
        table.to_csv(output, index=False, encoding="utf-8")
        print(
            f"{name}: {len(table):,} linhas -> "
            f"{output.relative_to(PROCESSED_DIR.parent.parent)}"
        )


if __name__ == "__main__":
    main()
