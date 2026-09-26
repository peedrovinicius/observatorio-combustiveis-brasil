from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .config import (
    PROCESSED_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
)

ANALYTICS_DIR = PROCESSED_DIR / "analytics"
STATION_ANALYTICS_DIR = (
    PROCESSED_DIR / "analytics_postos"
)
ASSETS_DIR = (
    PROJECT_ROOT
    / "assets"
    / "generated"
)


def _format_currency(
    value: object,
) -> str:
    if pd.isna(value):
        return "n/d"
    return (
        f"R$ {float(value):.2f}"
        .replace(".", ",")
    )


def _format_percent(
    value: object,
) -> str:
    if pd.isna(value):
        return "n/d"
    return (
        f"{float(value):+.2f}%"
        .replace(".", ",")
    )


def _select_common_gasoline(
    products: pd.Series,
) -> str | None:
    values = [
        str(value)
        for value
        in products.dropna().unique()
    ]
    for value in values:
        upper = value.upper()
        if (
            "GASOLINA" in upper
            and "ADITIV"
            not in upper
        ):
            return value
    return (
        values[0]
        if values
        else None
    )


def _location_label(
    row: pd.Series,
) -> str:
    for column in (
        "uf",
        "estado",
        "municipio",
    ):
        value = row.get(
            column
        )
        if pd.notna(value):
            text = str(
                value
            ).strip()
            if text:
                return text
    return "n/d"


def build_insights_markdown(
    kpis: pd.DataFrame,
    ranking_ufs: pd.DataFrame,
    quality_aggregate: (
        dict[str, object]
        | None
    ) = None,
    quality_stations: (
        dict[str, object]
        | None
    ) = None,
) -> str:
    lines = [
        "# Insights automáticos",
        "",
        (
            "Relatório gerado "
            "exclusivamente a partir "
            "das saídas do pipeline."
        ),
        "",
        "## Brasil",
        "",
    ]

    if kpis.empty:
        lines.append(
            "Nenhum KPI nacional disponível."
        )
    else:
        ordered = (
            kpis.sort_values(
                "produto",
                kind="stable",
            )
        )
        for _, row in ordered.iterrows():
            product = str(
                row["produto"]
            )
            lines.extend(
                [
                    f"### {product}",
                    "",
                    (
                        "- Preço na última semana: "
                        f"**{_format_currency(row.get('preco_atual'))}**"
                    ),
                    (
                        "- Variação semanal: "
                        f"**{_format_percent(row.get('variacao_semanal_pct'))}**"
                    ),
                    (
                        "- Variação desde o início de 2026: "
                        f"**{_format_percent(row.get('variacao_desde_inicio_ano_pct'))}**"
                    ),
                    (
                        "- Menor preço médio semanal em 2026: "
                        f"**{_format_currency(row.get('menor_preco_2026'))}**"
                    ),
                    (
                        "- Maior preço médio semanal em 2026: "
                        f"**{_format_currency(row.get('maior_preco_2026'))}**"
                    ),
                    "",
                ]
            )

    if (
        not ranking_ufs.empty
        and "produto"
        in ranking_ufs.columns
    ):
        product = (
            _select_common_gasoline(
                ranking_ufs[
                    "produto"
                ]
            )
        )
        if product:
            subset = (
                ranking_ufs.loc[
                    ranking_ufs[
                        "produto"
                    ].eq(product)
                ]
                .copy()
            )
            subset = subset.sort_values(
                "preco_medio_revenda",
                ascending=False,
                kind="stable",
            )

            lines.extend(
                [
                    "## Ranking por UF",
                    "",
                    (
                        "Produto selecionado: "
                        f"**{product}**"
                    ),
                    "",
                    (
                        "### 5 maiores "
                        "preços médios"
                    ),
                    "",
                ]
            )

            for _, row in (
                subset.head(5)
                .iterrows()
            ):
                label = (
                    _location_label(
                        row
                    )
                )
                lines.append(
                    f"- {label}: "
                    f"{_format_currency(row['preco_medio_revenda'])}"
                )

            lines.extend(
                [
                    "",
                    (
                        "### 5 menores "
                        "preços médios"
                    ),
                    "",
                ]
            )
            for _, row in (
                subset.tail(5)
                .sort_values(
                    "preco_medio_revenda",
                    kind="stable",
                )
                .iterrows()
            ):
                label = (
                    _location_label(
                        row
                    )
                )
                lines.append(
                    f"- {label}: "
                    f"{_format_currency(row['preco_medio_revenda'])}"
                )
            lines.append("")

    lines.extend(
        [
            "## Qualidade dos dados",
            "",
        ]
    )

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
        if (
            "postos_distintos_cnpj"
            in quality_stations
        ):
            lines.append(
                "- Postos distintos por CNPJ: "
                f"**{quality_stations['postos_distintos_cnpj']}**"
            )
        if (
            "municipios"
            in quality_stations
        ):
            lines.append(
                "- Municípios cobertos: "
                f"**{quality_stations['municipios']}**"
            )

    lines.extend(
        [
            "",
            (
                "## Observação "
                "metodológica"
            ),
            "",
            (
                "Os indicadores nacionais, regionais e estaduais "
                "preservam os agregados oficiais publicados pela ANP. "
                "Indicadores derivados pelo projeto são identificados "
                "como tal e não substituem as séries oficiais."
            ),
            "",
        ]
    )

    return "\n".join(
        lines
    )


def plot_monthly_trend(
    monthly: pd.DataFrame,
    output: Path,
) -> None:
    frame = monthly.copy()
    frame["periodo"] = pd.to_datetime(
        frame["ano"].astype(str)
        + "-"
        + frame["mes"]
        .astype(str)
        .str.zfill(2)
        + "-01",
        errors="coerce",
    )

    fig, ax = plt.subplots(
        figsize=(11, 6)
    )
    for product, group in (
        frame.groupby(
            "produto"
        )
    ):
        group = group.sort_values(
            "periodo"
        )
        ax.plot(
            group["periodo"],
            group[
                "media_das_semanas"
            ],
            marker="o",
            label=product,
        )

    ax.set_title(
        "Tendência mensal derivada das observações semanais - Brasil"
    )
    ax.set_xlabel("Mês")
    ax.set_ylabel(
        "Preço médio de revenda"
    )
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(
        output,
        dpi=160,
    )
    plt.close(fig)


def plot_state_ranking(
    ranking: pd.DataFrame,
    output: Path,
) -> None:
    if (
        ranking.empty
        or "produto"
        not in ranking.columns
    ):
        raise ValueError(
            "Ranking por UF sem dados disponíveis."
        )

    product = (
        _select_common_gasoline(
            ranking["produto"]
        )
    )
    if not product:
        raise ValueError(
            "Ranking por UF sem produtos disponíveis."
        )

    frame = (
        ranking.loc[
            ranking[
                "produto"
            ].eq(product)
        ]
        .copy()
    )
    frame = (
        frame.sort_values(
            "preco_medio_revenda",
            ascending=False,
            kind="stable",
        )
        .head(10)
    )
    frame = frame.sort_values(
        "preco_medio_revenda",
        kind="stable",
    )

    labels = (
        frame["uf"]
        if "uf"
        in frame.columns
        else frame["estado"]
    )

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )
    ax.barh(
        labels,
        frame[
            "preco_medio_revenda"
        ],
    )
    ax.set_title(
        f"10 maiores preços médios por UF - {product}"
    )
    ax.set_xlabel(
        "Preço médio de revenda"
    )
    ax.set_ylabel("UF")
    fig.tight_layout()
    fig.savefig(
        output,
        dpi=160,
    )
    plt.close(fig)


def plot_ethanol_gasoline(
    ratio: pd.DataFrame,
    output: Path,
) -> None:
    fig, ax = plt.subplots(
        figsize=(8, 6)
    )
    ax.scatter(
        ratio[
            "preco_gasolina_comum"
        ],
        ratio[
            "preco_etanol"
        ],
        alpha=0.65,
    )
    ax.set_title(
        "Etanol x gasolina comum - municípios"
    )
    ax.set_xlabel(
        "Preço médio da gasolina comum"
    )
    ax.set_ylabel(
        "Preço médio do etanol"
    )
    fig.tight_layout()
    fig.savefig(
        output,
        dpi=160,
    )
    plt.close(fig)


def _save_empty_chart(
    output: Path,
    title: str,
    message: str,
) -> None:
    fig, ax = plt.subplots(
        figsize=(9, 5)
    )
    ax.axis("off")
    ax.set_title(title)
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        transform=ax.transAxes,
    )
    fig.tight_layout()
    fig.savefig(
        output,
        dpi=160,
    )
    plt.close(fig)


def plot_station_municipality_dispersion(
    distribution: pd.DataFrame,
    output: Path,
) -> None:
    if distribution.empty:
        _save_empty_chart(
            output,
            (
                "Dispersão "
                "municipal por posto"
            ),
            (
                "Sem dados disponíveis "
                "para este recorte."
            ),
        )
        return

    product = (
        _select_common_gasoline(
            distribution[
                "produto"
            ]
        )
    )
    if not product:
        _save_empty_chart(
            output,
            (
                "Dispersão "
                "municipal por posto"
            ),
            (
                "Nenhum produto "
                "disponível para comparação."
            ),
        )
        return

    frame = (
        distribution.loc[
            distribution[
                "produto"
            ].eq(product)
            & distribution[
                "postos_distintos"
            ].ge(3)
        ]
        .copy()
    )

    if frame.empty:
        _save_empty_chart(
            output,
            (
                "Dispersão municipal "
                f"por posto - {product}"
            ),
            (
                "Amostra insuficiente: "
                "nenhum município com "
                "pelo menos 3 postos."
            ),
        )
        return

    frame[
        "localidade"
    ] = (
        frame["uf"]
        .astype("string")
        + " / "
        + frame[
            "municipio"
        ].astype("string")
    )

    frame = (
        frame.sort_values(
            [
                "intervalo_interquartil",
                "postos_distintos",
            ],
            ascending=[
                False,
                False,
            ],
            kind="stable",
        )
        .head(12)
        .sort_values(
            "intervalo_interquartil",
            kind="stable",
        )
    )

    fig, ax = plt.subplots(
        figsize=(10, 7)
    )
    ax.barh(
        frame["localidade"],
        frame[
            "intervalo_interquartil"
        ],
    )
    ax.set_title(
        "Dispersão municipal "
        f"por posto - {product}"
    )
    ax.set_xlabel(
        "Intervalo interquartil "
        "do preço observado"
    )
    ax.set_ylabel(
        "UF / município"
    )
    fig.tight_layout()
    fig.savefig(
        output,
        dpi=160,
    )
    plt.close(fig)


def plot_station_brand_median(
    brands: pd.DataFrame,
    output: Path,
) -> None:
    if brands.empty:
        _save_empty_chart(
            output,
            (
                "Mediana observada "
                "por bandeira"
            ),
            (
                "Sem dados disponíveis "
                "para este recorte."
            ),
        )
        return

    product = (
        _select_common_gasoline(
            brands["produto"]
        )
    )
    if not product:
        _save_empty_chart(
            output,
            (
                "Mediana observada "
                "por bandeira"
            ),
            (
                "Nenhum produto "
                "disponível para comparação."
            ),
        )
        return

    sufficient = (
        brands[
            "amostra_suficiente"
        ]
        .astype("string")
        .str.casefold()
        .isin(
            [
                "true",
                "1",
            ]
        )
    )

    frame = (
        brands.loc[
            brands[
                "produto"
            ].eq(product)
            & sufficient
        ]
        .copy()
    )

    if frame.empty:
        _save_empty_chart(
            output,
            (
                "Mediana observada "
                f"por bandeira - {product}"
            ),
            (
                "Amostra insuficiente "
                "para comparação entre bandeiras."
            ),
        )
        return

    frame = (
        frame.sort_values(
            [
                "postos_distintos",
                "observacoes",
            ],
            ascending=[
                False,
                False,
            ],
            kind="stable",
        )
        .head(10)
        .sort_values(
            "mediana_observada",
            kind="stable",
        )
    )

    fig, ax = plt.subplots(
        figsize=(9, 6)
    )
    ax.barh(
        frame["bandeira"],
        frame[
            "mediana_observada"
        ],
    )
    ax.set_title(
        "Mediana observada "
        f"por bandeira - {product}"
    )
    ax.set_xlabel(
        "Mediana do preço observado"
    )
    ax.set_ylabel(
        "Bandeira"
    )
    fig.tight_layout()
    fig.savefig(
        output,
        dpi=160,
    )
    plt.close(fig)


def _read_json(
    path: Path,
) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main() -> None:
    kpis_path = (
        ANALYTICS_DIR
        / "kpis_brasil_2026.csv"
    )
    monthly_path = (
        ANALYTICS_DIR
        / "tendencia_mensal_brasil_2026.csv"
    )
    ranking_path = (
        ANALYTICS_DIR
        / "ranking_ufs_ultima_semana.csv"
    )
    ratio_path = (
        ANALYTICS_DIR
        / "etanol_gasolina_ultima_semana.csv"
    )
    station_distribution_path = (
        STATION_ANALYTICS_DIR
        / "distribuicao_municipios_ultima_coleta.csv"
    )
    station_brands_path = (
        STATION_ANALYTICS_DIR
        / "bandeiras_ultima_coleta.csv"
    )

    required = [
        kpis_path,
        monthly_path,
        ranking_path,
        ratio_path,
        station_distribution_path,
        station_brands_path,
    ]
    missing = [
        path
        for path in required
        if not path.exists()
    ]
    if missing:
        raise SystemExit(
            "Saídas analíticas ausentes. "
            "Execute python -m src.pipeline "
            "antes de gerar o relatório visual."
        )

    kpis = pd.read_csv(
        kpis_path
    )
    monthly = pd.read_csv(
        monthly_path
    )
    ranking = pd.read_csv(
        ranking_path
    )
    ratio = pd.read_csv(
        ratio_path
    )
    station_distribution = (
        pd.read_csv(
            station_distribution_path
        )
    )
    station_brands = (
        pd.read_csv(
            station_brands_path
        )
    )

    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plot_monthly_trend(
        monthly,
        ASSETS_DIR
        / "tendencia_brasil_2026.png",
    )
    plot_state_ranking(
        ranking,
        ASSETS_DIR
        / "ranking_ufs_gasolina.png",
    )
    plot_ethanol_gasoline(
        ratio,
        ASSETS_DIR
        / "etanol_gasolina_municipios.png",
    )
    plot_station_municipality_dispersion(
        station_distribution,
        ASSETS_DIR
        / "dispersao_municipios_postos.png",
    )
    plot_station_brand_median(
        station_brands,
        ASSETS_DIR
        / "mediana_bandeiras_postos.png",
    )

    markdown = (
        build_insights_markdown(
            kpis,
            ranking,
            _read_json(
                REPORTS_DIR
                / "quality_2026.json"
            ),
            _read_json(
                REPORTS_DIR
                / "quality_postos_2026.json"
            ),
        )
    )
    output = (
        REPORTS_DIR
        / "insights_2026.md"
    )
    output.write_text(
        markdown,
        encoding="utf-8",
    )

    print(
        "Relatório: "
        f"{output.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Gráficos: "
        f"{ASSETS_DIR.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
