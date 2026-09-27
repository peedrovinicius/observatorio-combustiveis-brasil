from __future__ import annotations

import json
import shutil
import tempfile
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
    matches: list[str] = []

    for raw_value in (
        products.dropna().unique()
    ):
        value = str(raw_value)
        upper = value.strip().upper()
        is_common = (
            upper == "GASOLINA"
            or (
                "GASOLINA" in upper
                and "COMUM" in upper
                and "ADITIV"
                not in upper
            )
        )
        if is_common:
            matches.append(value)

    unique_matches = list(
        dict.fromkeys(matches)
    )
    if len(unique_matches) != 1:
        return None
    return unique_matches[0]

def _single_unit_subset(
    frame: pd.DataFrame,
    product: str,
) -> tuple[pd.DataFrame, str]:
    subset = frame.loc[
        frame["produto"].eq(product)
    ].copy()

    if (
        subset.empty
        or "unidade_medida"
        not in subset.columns
    ):
        return subset, product

    unit_key = (
        subset["unidade_medida"]
        .astype("string")
        .fillna("")
        .str.strip()
    )
    units = sorted(
        set(
            unit_key.tolist()
        )
    )
    if len(units) > 1:
        return (
            subset.iloc[0:0].copy(),
            f"{product} (múltiplas unidades)",
        )

    unit = units[0] if units else ""
    subset = subset.loc[
        unit_key.eq(unit)
    ].copy()
    label = (
        f"{product} · {unit}"
        if unit
        else product
    )
    return subset, label


def _ranking_period_label(
    frame: pd.DataFrame,
) -> str | None:
    if (
        frame.empty
        or "data_inicial"
        not in frame.columns
    ):
        return None

    starts = (
        pd.to_datetime(
            frame["data_inicial"],
            errors="coerce",
        )
        .dropna()
        .dt.normalize()
        .unique()
    )
    if len(starts) != 1:
        return (
            "período ambíguo"
            if len(starts) > 1
            else None
        )

    start = pd.Timestamp(
        starts[0]
    )
    label = start.strftime(
        "%d/%m/%Y"
    )

    if "data_final" in frame.columns:
        ends = (
            pd.to_datetime(
                frame["data_final"],
                errors="coerce",
            )
            .dropna()
            .dt.normalize()
            .unique()
        )
        if len(ends) > 1:
            return "período ambíguo"
        if len(ends) == 1:
            label += (
                " a "
                + pd.Timestamp(
                    ends[0]
                ).strftime(
                    "%d/%m/%Y"
                )
            )

    return "semana " + label


def _station_collection_label(
    frame: pd.DataFrame,
) -> str | None:
    if (
        frame.empty
        or "data_coleta"
        not in frame.columns
    ):
        return None

    dates = (
        pd.to_datetime(
            frame["data_coleta"],
            errors="coerce",
        )
        .dropna()
        .dt.normalize()
        .unique()
    )
    if len(dates) != 1:
        return (
            "coleta ambígua"
            if len(dates) > 1
            else None
        )

    return (
        "coleta "
        + pd.Timestamp(
            dates[0]
        ).strftime(
            "%d/%m/%Y"
        )
    )


def _station_dispersion_title(
    series_label: str,
    collection_label: str | None,
) -> str:
    title = (
        "12 maiores dispersões municipais "
        f"por posto - {series_label}"
    )
    if collection_label:
        title += f" - {collection_label}"
    return title


def _station_brand_title(
    series_label: str,
    collection_label: str | None,
) -> str:
    title = (
        "Mediana por bandeira entre "
        "as 10 maiores coberturas - "
        f"{series_label}"
    )
    if collection_label:
        title += f" - {collection_label}"
    return title


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
        sort_columns = [
            "produto",
            *(
                ["unidade_medida"]
                if "unidade_medida"
                in kpis.columns
                else []
            ),
        ]
        ordered = (
            kpis.sort_values(
                sort_columns,
                kind="stable",
            )
        )
        for _, row in ordered.iterrows():
            product = str(
                row["produto"]
            )
            unit = row.get(
                "unidade_medida"
            )
            unit_text = (
                str(unit).strip()
                if pd.notna(unit)
                else ""
            )
            series_label = (
                f"{product} · {unit_text}"
                if unit_text
                else product
            )
            lines.extend(
                [
                    f"### {series_label}",
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
            subset, series_label = (
                _single_unit_subset(
                    ranking_ufs,
                    product,
                )
            )
            lines.extend(
                [
                    "## Ranking por UF",
                    "",
                    (
                        "Série selecionada: "
                        f"**{series_label}**"
                    ),
                    "",
                ]
            )

            if subset.empty:
                lines.extend(
                    [
                        (
                            "Ranking não exibido: "
                            "o recorte contém múltiplas "
                            "unidades de medida."
                        ),
                        "",
                    ]
                )
            else:
                period_label = (
                    _ranking_period_label(
                        subset
                    )
                )
                if period_label == (
                    "período ambíguo"
                ):
                    lines.extend(
                        [
                            (
                                "Ranking não exibido: "
                                "a série contém múltiplas "
                                "datas e não é temporalmente "
                                "comparável."
                            ),
                            "",
                        ]
                    )
                    subset = (
                        subset.iloc[
                            0:0
                        ].copy()
                    )
                elif period_label:
                    lines.extend(
                        [
                            (
                                "Período: "
                                f"**{period_label}**"
                            ),
                            "",
                        ]
                    )

            if not subset.empty:
                subset = subset.sort_values(
                    "preco_medio_revenda",
                    ascending=False,
                    kind="stable",
                )
                lines.extend(
                    [
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
        station_count = (
            quality_stations.get(
                "postos_distintos",
                quality_stations.get(
                    "postos_distintos_cnpj",
                ),
            )
        )
        if station_count is not None:
            lines.append(
                "- Postos distintos: "
                f"**{station_count}**"
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
    required = {
        "ano",
        "mes",
        "produto",
        "media_das_semanas",
    }
    if (
        monthly.empty
        or not required.issubset(
            monthly.columns
        )
    ):
        _save_empty_chart(
            output,
            "Tendência mensal - Brasil",
            (
                "Sem dados mensais "
                "disponíveis para este recorte."
            ),
        )
        return

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
    frame = frame.dropna(
        subset=[
            "periodo",
            "media_das_semanas",
        ]
    )
    if frame.empty:
        _save_empty_chart(
            output,
            "Tendência mensal - Brasil",
            (
                "Nenhuma observação mensal "
                "válida para este recorte."
            ),
        )
        return

    fig, ax = plt.subplots(
        figsize=(11, 6)
    )
    group_columns = [
        "produto",
        *(
            ["unidade_medida"]
            if "unidade_medida"
            in frame.columns
            else []
        ),
    ]
    for key, group in (
        frame.groupby(
            group_columns,
            dropna=False,
        )
    ):
        if isinstance(
            key,
            tuple,
        ):
            product = str(key[0])
            unit = (
                ""
                if pd.isna(key[1])
                else str(key[1]).strip()
            )
        else:
            product = str(key)
            unit = ""
        label = (
            f"{product} · {unit}"
            if unit
            else product
        )
        group = group.sort_values(
            "periodo"
        )
        ax.plot(
            group["periodo"],
            group[
                "media_das_semanas"
            ],
            marker="o",
            label=label,
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
    required = {
        "produto",
        "preco_medio_revenda",
    }
    if (
        ranking.empty
        or not required.issubset(
            ranking.columns
        )
    ):
        _save_empty_chart(
            output,
            "Ranking de preços por UF",
            (
                "Sem dados disponíveis "
                "para este recorte."
            ),
        )
        return

    product = (
        _select_common_gasoline(
            ranking["produto"]
        )
    )
    if not product:
        _save_empty_chart(
            output,
            "Ranking de preços por UF",
            (
                "Gasolina comum não disponível "
                "para este recorte."
            ),
        )
        return

    frame, series_label = (
        _single_unit_subset(
            ranking,
            product,
        )
    )
    if frame.empty:
        _save_empty_chart(
            output,
            "Ranking de preços por UF",
            (
                "Gasolina comum possui "
                "múltiplas unidades neste recorte."
            ),
        )
        return

    period_label = (
        _ranking_period_label(
            frame
        )
    )
    if period_label == (
        "período ambíguo"
    ):
        _save_empty_chart(
            output,
            "Ranking de preços por UF",
            (
                "Ranking indisponível: "
                "a série contém múltiplas datas."
            ),
        )
        return

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
    title = (
        f"10 maiores preços médios por UF - {series_label}"
    )
    if period_label:
        title += f" - {period_label}"
    ax.set_title(
        title
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
    required = {
        "preco_gasolina_comum",
        "preco_etanol",
    }
    if (
        ratio.empty
        or not required.issubset(
            ratio.columns
        )
    ):
        _save_empty_chart(
            output,
            "Etanol x gasolina comum",
            (
                "Sem municípios com preços "
                "comparáveis neste recorte."
            ),
        )
        return

    frame = ratio.dropna(
        subset=[
            "preco_gasolina_comum",
            "preco_etanol",
        ]
    ).copy()
    if (
        "unidade_medida"
        in frame.columns
    ):
        units = (
            frame["unidade_medida"]
            .astype("string")
            .fillna("")
            .str.strip()
            .unique()
        )
        if len(units) > 1:
            _save_empty_chart(
                output,
                "Etanol x gasolina comum",
                (
                    "Há múltiplas unidades "
                    "de medida neste recorte."
                ),
            )
            return
    if frame.empty:
        _save_empty_chart(
            output,
            "Etanol x gasolina comum",
            (
                "Sem municípios com preços "
                "comparáveis neste recorte."
            ),
        )
        return

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )
    ax.scatter(
        frame[
            "preco_gasolina_comum"
        ],
        frame[
            "preco_etanol"
        ],
        alpha=0.65,
    )
    unit_label = ""
    if "unidade_medida" in frame.columns:
        unit = (
            frame["unidade_medida"]
            .astype("string")
            .fillna("")
            .str.strip()
            .iloc[0]
        )
        if unit:
            unit_label = f" - {unit}"

    ax.set_title(
        "Etanol x gasolina comum - "
        "última semana comparável por município"
        + unit_label
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

    product_frame, series_label = (
        _single_unit_subset(
            distribution,
            product,
        )
    )
    if (
        product_frame.empty
        and "múltiplas unidades"
        in series_label
    ):
        _save_empty_chart(
            output,
            (
                "Dispersão municipal "
                f"por posto - {series_label}"
            ),
            (
                "O recorte contém múltiplas "
                "unidades de medida e não pode "
                "ser combinado em um único gráfico."
            ),
        )
        return

    collection_label = (
        _station_collection_label(
            product_frame
        )
    )
    if collection_label == (
        "coleta ambígua"
    ):
        _save_empty_chart(
            output,
            "Dispersão municipal por posto",
            (
                "Gráfico indisponível: "
                "a série contém múltiplas "
                "datas de coleta."
            ),
        )
        return

    frame = (
        product_frame.loc[
            product_frame[
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
                f"por posto - {series_label}"
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
        _station_dispersion_title(
            series_label,
            collection_label,
        )
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

    product_frame, series_label = (
        _single_unit_subset(
            brands,
            product,
        )
    )
    if (
        product_frame.empty
        and "múltiplas unidades"
        in series_label
    ):
        _save_empty_chart(
            output,
            (
                "Mediana observada "
                f"por bandeira - {series_label}"
            ),
            (
                "O recorte contém múltiplas "
                "unidades de medida e não pode "
                "ser combinado em um único gráfico."
            ),
        )
        return

    collection_label = (
        _station_collection_label(
            product_frame
        )
    )
    if collection_label == (
        "coleta ambígua"
    ):
        _save_empty_chart(
            output,
            "Mediana observada por bandeira",
            (
                "Gráfico indisponível: "
                "a série contém múltiplas "
                "datas de coleta."
            ),
        )
        return

    sufficient = sufficient.loc[
        product_frame.index
    ]
    frame = (
        product_frame.loc[
            sufficient
        ]
        .copy()
    )

    if frame.empty:
        _save_empty_chart(
            output,
            (
                "Mediana observada "
                f"por bandeira - {series_label}"
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
        _station_brand_title(
            series_label,
            collection_label,
        )
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


def _remove_path(
    path: Path,
) -> None:
    if path.is_dir():
        shutil.rmtree(
            path
        )
    elif path.exists():
        path.unlink()


def _publish_report_bundle(
    staged_assets: Path,
    staged_insights: Path,
    assets_dir: Path,
    insights_path: Path,
) -> None:
    if (
        not staged_assets.is_dir()
    ):
        raise FileNotFoundError(
            "Diretório de gráficos em "
            "staging não encontrado."
        )
    if (
        not staged_insights.is_file()
    ):
        raise FileNotFoundError(
            "Relatório de insights em "
            "staging não encontrado."
        )

    required_images = {
        "tendencia_brasil_2026.png",
        "ranking_ufs_gasolina.png",
        "etanol_gasolina_municipios.png",
        "dispersao_municipios_postos.png",
        "mediana_bandeiras_postos.png",
    }
    staged_image_paths = [
        path
        for path in staged_assets.iterdir()
        if path.is_file()
    ]
    staged_images = {
        path.name
        for path in staged_image_paths
    }
    if staged_images != required_images:
        missing = sorted(
            required_images
            - staged_images
        )
        extra = sorted(
            staged_images
            - required_images
        )
        details: list[str] = []
        if missing:
            details.append(
                "ausentes: "
                + ", ".join(
                    missing
                )
            )
        if extra:
            details.append(
                "inesperados: "
                + ", ".join(
                    extra
                )
            )
        raise ValueError(
            "Conjunto de gráficos inválido"
            + (
                ": "
                + "; ".join(details)
                if details
                else ""
            )
        )

    empty_images = sorted(
        path.name
        for path in staged_image_paths
        if path.stat().st_size <= 0
    )
    if empty_images:
        raise ValueError(
            "Gráficos vazios no staging: "
            + ", ".join(
                empty_images
            )
        )

    if (
        staged_insights.stat().st_size
        <= 0
    ):
        raise ValueError(
            "Relatório de insights vazio "
            "no staging."
        )

    assets_dir.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    insights_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    backup_root = (
        staged_assets.parent
        / "backup"
    )
    backup_root.mkdir(
        exist_ok=False
    )
    backup_assets = (
        backup_root
        / "generated"
    )
    backup_insights = (
        backup_root
        / insights_path.name
    )

    had_assets = (
        assets_dir.exists()
    )
    had_insights = (
        insights_path.exists()
    )
    installed_assets = False
    installed_insights = False

    try:
        if had_assets:
            shutil.move(
                str(assets_dir),
                str(backup_assets),
            )
        if had_insights:
            shutil.move(
                str(insights_path),
                str(backup_insights),
            )

        shutil.move(
            str(staged_assets),
            str(assets_dir),
        )
        installed_assets = True

        shutil.move(
            str(staged_insights),
            str(insights_path),
        )
        installed_insights = True
    except Exception:
        if installed_insights:
            _remove_path(
                insights_path
            )
        if installed_assets:
            _remove_path(
                assets_dir
            )

        if (
            had_insights
            and backup_insights.exists()
        ):
            shutil.move(
                str(backup_insights),
                str(insights_path),
            )
        if (
            had_assets
            and backup_assets.exists()
        ):
            shutil.move(
                str(backup_assets),
                str(assets_dir),
            )
        raise


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

    with tempfile.TemporaryDirectory(
        prefix=".report_stage_",
        dir=PROJECT_ROOT,
    ) as temporary:
        stage_root = Path(
            temporary
        )
        staged_assets = (
            stage_root
            / "generated"
        )
        staged_assets.mkdir()
        staged_insights = (
            stage_root
            / "insights_2026.md"
        )

        plot_monthly_trend(
            monthly,
            staged_assets
            / "tendencia_brasil_2026.png",
        )
        plot_state_ranking(
            ranking,
            staged_assets
            / "ranking_ufs_gasolina.png",
        )
        plot_ethanol_gasoline(
            ratio,
            staged_assets
            / "etanol_gasolina_municipios.png",
        )
        plot_station_municipality_dispersion(
            station_distribution,
            staged_assets
            / "dispersao_municipios_postos.png",
        )
        plot_station_brand_median(
            station_brands,
            staged_assets
            / "mediana_bandeiras_postos.png",
        )
        staged_insights.write_text(
            markdown,
            encoding="utf-8",
        )

        _publish_report_bundle(
            staged_assets,
            staged_insights,
            ASSETS_DIR,
            output,
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
