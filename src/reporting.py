from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .config import PROCESSED_DIR, PROJECT_ROOT, REPORTS_DIR

ANALYTICS_DIR = PROCESSED_DIR / "analytics"
ASSETS_DIR = PROJECT_ROOT / "assets" / "generated"


def _format_currency(value: object) -> str:
    if pd.isna(value):
        return "n/d"
    return f"R$ {float(value):.2f}".replace(".", ",")


def _format_percent(value: object) -> str:
    if pd.isna(value):
        return "n/d"
    return f"{float(value):+.2f}%".replace(".", ",")


def _select_common_gasoline(products: pd.Series) -> str | None:
    values = [
        str(value)
        for value in products.dropna().unique()
    ]
    for value in values:
        upper = value.upper()
        if "GASOLINA" in upper and "ADITIV" not in upper:
            return value
    return values[0] if values else None


def build_insights_markdown(
    kpis: pd.DataFrame,
    ranking_ufs: pd.DataFrame,
    quality_aggregate: dict[str, object] | None = None,
    quality_stations: dict[str, object] | None = None,
) -> str:
    lines = [
        "# Insights automáticos",
        "",
        "Relatório gerado exclusivamente a partir das saídas do pipeline.",
        "",
        "## Brasil",
        "",
    ]

    if kpis.empty:
        lines.append("Nenhum KPI nacional disponível.")
    else:
        ordered = kpis.sort_values("produto", kind="stable")
        for _, row in ordered.iterrows():
            product = str(row["produto"])
            lines.extend(
                [
                    f"### {product}",
                    "",
                    f"- Preço na última semana: **{_format_currency(row.get('preco_atual'))}**",
                    f"- Variação semanal: **{_format_percent(row.get('variacao_semanal_pct'))}**",
                    f"- Variação desde o início de 2026: **{_format_percent(row.get('variacao_desde_inicio_ano_pct'))}**",
                    f"- Menor preço médio semanal em 2026: **{_format_currency(row.get('menor_preco_2026'))}**",
                    f"- Maior preço médio semanal em 2026: **{_format_currency(row.get('maior_preco_2026'))}**",
                    "",
                ]
            )

    if not ranking_ufs.empty:
        product = _select_common_gasoline(ranking_ufs["produto"])
        if product:
            subset = ranking_ufs.loc[
                ranking_ufs["produto"].eq(product)
            ].copy()
            subset = subset.sort_values(
                "preco_medio_revenda",
                ascending=False,
                kind="stable",
            )
            lines.extend(
                [
                    "## Ranking por UF",
                    "",
                    f"Produto selecionado: **{product}**",
                    "",
                    "### 5 maiores preços médios",
                    "",
                ]
            )
            for _, row in subset.head(5).iterrows():
                label = row.get("uf") or row.get("estado") or "n/d"
                lines.append(
                    f"- {label}: {_format_currency(row['preco_medio_revenda'])}"
                )

            lines.extend(["", "### 5 menores preços médios", ""])
            for _, row in subset.tail(5).sort_values(
                "preco_medio_revenda",
                kind="stable",
            ).iterrows():
                label = row.get("uf") or row.get("estado") or "n/d"
                lines.append(
                    f"- {label}: {_format_currency(row['preco_medio_revenda'])}"
                )
            lines.append("")

    lines.extend(["## Qualidade dos dados", ""])

    if quality_aggregate:
        lines.append(
            "- Série agregada: "
            f"**{quality_aggregate.get('status', 'n/d')}**"
        )
    if quality_stations:
        lines.append(
            "- Dados por posto: "
            f"**{quality_stations.get('status', 'n/d')}**"
        )
        if "postos_distintos_cnpj" in quality_stations:
            lines.append(
                "- Postos distintos por CNPJ: "
                f"**{quality_stations['postos_distintos_cnpj']}**"
            )
        if "municipios" in quality_stations:
            lines.append(
                "- Municípios cobertos: "
                f"**{quality_stations['municipios']}**"
            )

    lines.extend(
        [
            "",
            "## Observação metodológica",
            "",
            "Os indicadores nacionais, regionais e estaduais preservam os agregados oficiais publicados pela ANP. Indicadores derivados pelo projeto são identificados como tal e não substituem as séries oficiais.",
            "",
        ]
    )

    return "\n".join(lines)


def plot_monthly_trend(monthly: pd.DataFrame, output: Path) -> None:
    frame = monthly.copy()
    frame["periodo"] = pd.to_datetime(
        frame["ano"].astype(str)
        + "-"
        + frame["mes"].astype(str).str.zfill(2)
        + "-01",
        errors="coerce",
    )

    fig, ax = plt.subplots(figsize=(11, 6))
    for product, group in frame.groupby("produto"):
        group = group.sort_values("periodo")
        ax.plot(
            group["periodo"],
            group["media_das_semanas"],
            marker="o",
            label=product,
        )

    ax.set_title("Tendência mensal derivada das observações semanais - Brasil")
    ax.set_xlabel("Mês")
    ax.set_ylabel("Preço médio de revenda")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_state_ranking(ranking: pd.DataFrame, output: Path) -> None:
    product = _select_common_gasoline(ranking["produto"])
    if not product:
        raise ValueError("Ranking por UF sem produtos disponíveis.")

    frame = ranking.loc[ranking["produto"].eq(product)].copy()
    frame = frame.sort_values(
        "preco_medio_revenda",
        ascending=False,
        kind="stable",
    ).head(10)
    frame = frame.sort_values("preco_medio_revenda", kind="stable")

    labels = (
        frame["uf"]
        if "uf" in frame.columns
        else frame["estado"]
    )

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(labels, frame["preco_medio_revenda"])
    ax.set_title(f"10 maiores preços médios por UF - {product}")
    ax.set_xlabel("Preço médio de revenda")
    ax.set_ylabel("UF")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_ethanol_gasoline(ratio: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        ratio["preco_gasolina_comum"],
        ratio["preco_etanol"],
        alpha=0.65,
    )
    ax.set_title("Etanol x gasolina comum - municípios")
    ax.set_xlabel("Preço médio da gasolina comum")
    ax.set_ylabel("Preço médio do etanol")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    kpis_path = ANALYTICS_DIR / "kpis_brasil_2026.csv"
    monthly_path = ANALYTICS_DIR / "tendencia_mensal_brasil_2026.csv"
    ranking_path = ANALYTICS_DIR / "ranking_ufs_ultima_semana.csv"
    ratio_path = ANALYTICS_DIR / "etanol_gasolina_ultima_semana.csv"

    required = [
        kpis_path,
        monthly_path,
        ranking_path,
        ratio_path,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit(
            "Saídas analíticas ausentes. Execute python -m src.pipeline antes de gerar o relatório visual."
        )

    kpis = pd.read_csv(kpis_path)
    monthly = pd.read_csv(monthly_path)
    ranking = pd.read_csv(ranking_path)
    ratio = pd.read_csv(ratio_path)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    plot_monthly_trend(
        monthly,
        ASSETS_DIR / "tendencia_brasil_2026.png",
    )
    plot_state_ranking(
        ranking,
        ASSETS_DIR / "ranking_ufs_gasolina.png",
    )
    plot_ethanol_gasoline(
        ratio,
        ASSETS_DIR / "etanol_gasolina_municipios.png",
    )

    markdown = build_insights_markdown(
        kpis,
        ranking,
        _read_json(REPORTS_DIR / "quality_2026.json"),
        _read_json(REPORTS_DIR / "quality_postos_2026.json"),
    )
    output = REPORTS_DIR / "insights_2026.md"
    output.write_text(markdown, encoding="utf-8")

    print(f"Relatório: {output.relative_to(PROJECT_ROOT)}")
    print(f"Gráficos: {ASSETS_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
