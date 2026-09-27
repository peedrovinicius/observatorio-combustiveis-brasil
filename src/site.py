from __future__ import annotations

import html
import json
import shutil
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

import pandas as pd

from .config import (
    PROCESSED_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
)

ANALYTICS_DIR = (
    PROCESSED_DIR
    / "analytics"
)
DOCS_DIR = (
    PROJECT_ROOT
    / "docs"
)
SNAPSHOT_DIR = (
    PROJECT_ROOT
    / "assets"
    / "snapshot"
)

SITE_IMAGES = [
    "tendencia_brasil_2026.png",
    "ranking_ufs_gasolina.png",
    "etanol_gasolina_municipios.png",
    "dispersao_municipios_postos.png",
    "mediana_bandeiras_postos.png",
]

REPOSITORY_URL = (
    "https://github.com/peedrovinicius/"
    "observatorio-combustiveis-brasil"
)
RESULTS_URL = (
    REPOSITORY_URL
    + "/blob/main/docs/resultados-2026.md"
)


def _currency(
    value: object,
) -> str:
    if pd.isna(value):
        return "n/d"
    return (
        f"R$ {float(value):.2f}"
        .replace(".", ",")
    )


def _percent(
    value: object,
) -> str:
    if pd.isna(value):
        return "n/d"
    return (
        f"{float(value):+.2f}%"
        .replace(".", ",")
    )


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


def _common_gasoline(
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
            "GASOLINA"
            in upper
            and "COMUM"
            in upper
            and "ADITIV"
            not in upper
        ):
            return value
    return None


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
            (
                "Gasolina comum "
                "com múltiplas unidades"
            ),
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


def _kpi_cards(
    kpis: pd.DataFrame,
) -> str:
    cards: list[str] = []

    sort_columns = [
        "produto",
        *(
            ["unidade_medida"]
            if "unidade_medida"
            in kpis.columns
            else []
        ),
    ]
    for _, row in (
        kpis.sort_values(
            sort_columns,
            kind="stable",
        )
        .iterrows()
    ):
        product_text = str(
            row[
                "produto"
            ]
        )
        unit = row.get(
            "unidade_medida"
        )
        unit_text = (
            str(unit).strip()
            if pd.notna(unit)
            else ""
        )
        product = html.escape(
            (
                f"{product_text} · {unit_text}"
                if unit_text
                else product_text
            )
        )
        cards.append(
            f"""
            <article class="card">
              <p class="eyebrow">{product}</p>
              <strong>{_currency(row.get("preco_atual"))}</strong>
              <span>última semana</span>
              <dl>
                <div><dt>Variação semanal</dt><dd>{_percent(row.get("variacao_semanal_pct"))}</dd></div>
                <div><dt>Desde início do ano</dt><dd>{_percent(row.get("variacao_desde_inicio_ano_pct"))}</dd></div>
                <div><dt>Mínimo em 2026</dt><dd>{_currency(row.get("menor_preco_2026"))}</dd></div>
                <div><dt>Máximo em 2026</dt><dd>{_currency(row.get("maior_preco_2026"))}</dd></div>
              </dl>
            </article>
            """
        )

    return "\n".join(cards)


def _ranking_rows(
    ranking: pd.DataFrame,
) -> tuple[str, str]:
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
        return (
            "",
            "Gasolina comum indisponível",
        )

    product = (
        _common_gasoline(
            ranking["produto"]
        )
    )
    if product is None:
        return (
            "",
            "Gasolina comum indisponível",
        )

    frame, series_label = (
        _single_unit_subset(
            ranking,
            product,
        )
    )
    if frame.empty:
        return (
            "",
            series_label,
        )

    frame = (
        frame.sort_values(
            "preco_medio_revenda",
            ascending=False,
            kind="stable",
        )
        .head(10)
    )

    rows: list[str] = []
    for _, row in frame.iterrows():
        label = row.get("uf")
        if (
            pd.isna(label)
            or str(label).strip()
            == ""
        ):
            label = row.get(
                "estado",
                "n/d",
            )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(label))}</td>"
            f"<td>{_currency(row['preco_medio_revenda'])}</td>"
            f"<td>{html.escape(str(row.get('postos_pesquisados', 'n/d')))}</td>"
            "</tr>"
        )

    return (
        "\n".join(rows),
        str(series_label),
    )


def _quality_cards(
    aggregate: (
        dict[str, object]
        | None
    ),
    stations: (
        dict[str, object]
        | None
    ),
) -> str:
    aggregate_status = (
        str(
            aggregate.get(
                "status",
                "n/d",
            )
        )
        if aggregate
        else "n/d"
    )
    station_status = (
        str(
            stations.get(
                "status",
                "n/d",
            )
        )
        if stations
        else "n/d"
    )
    municipalities = (
        str(
            stations.get(
                "municipios",
                "n/d",
            )
        )
        if stations
        else "n/d"
    )
    establishments = (
        str(
            stations.get(
                "postos_distintos_cnpj",
                "n/d",
            )
        )
        if stations
        else "n/d"
    )

    return f"""
      <article class="metric">
        <span>Série agregada</span>
        <strong>{html.escape(aggregate_status)}</strong>
      </article>
      <article class="metric">
        <span>Dados por posto</span>
        <strong>{html.escape(station_status)}</strong>
      </article>
      <article class="metric">
        <span>Municípios cobertos</span>
        <strong>{html.escape(municipalities)}</strong>
      </article>
      <article class="metric">
        <span>Postos por CNPJ</span>
        <strong>{html.escape(establishments)}</strong>
      </article>
    """


def build_site(
    kpis_path: Path,
    ranking_path: Path,
    snapshot_dir: Path,
    docs_dir: Path,
    aggregate_quality_path: (
        Path
        | None
    ) = None,
    station_quality_path: (
        Path
        | None
    ) = None,
) -> Path:
    required = [
        kpis_path,
        ranking_path,
        *[
            snapshot_dir
            / filename
            for filename
            in SITE_IMAGES
        ],
    ]
    missing = [
        path
        for path
        in required
        if not path.exists()
    ]
    if missing:
        formatted = "\n".join(
            f"- {path}"
            for path
            in missing
        )
        raise FileNotFoundError(
            "Não foi possível construir "
            "o relatório web. "
            f"Arquivos ausentes:\n{formatted}"
        )

    kpis = pd.read_csv(
        kpis_path
    )
    ranking = pd.read_csv(
        ranking_path
    )

    docs_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    assets_dir = (
        docs_dir
        / "assets"
    )
    assets_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for filename in SITE_IMAGES:
        shutil.copy2(
            snapshot_dir
            / filename,
            assets_dir
            / filename,
        )

    ranking_rows, ranking_product = (
        _ranking_rows(
            ranking
        )
    )
    generated_at = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    )

    aggregate_quality = (
        _read_json(
            aggregate_quality_path
        )
        if aggregate_quality_path
        else None
    )
    station_quality = (
        _read_json(
            station_quality_path
        )
        if station_quality_path
        else None
    )

    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta
    name="description"
    content="Análise de preços de combustíveis no Brasil com dados públicos da ANP."
  />
  <title>Observatório de Combustíveis Brasil</title>
  <link rel="stylesheet" href="site.css" />
</head>
<body>
  <header class="hero">
    <div class="shell">
      <p class="eyebrow">Dados públicos oficiais da ANP</p>
      <h1>Observatório de Combustíveis Brasil</h1>
      <p class="lead">
        Preços de combustíveis em 2026 analisados com Python,
        PostgreSQL, modelagem dimensional e Power BI.
      </p>
      <p class="updated">Atualização do relatório: {generated_at}</p>
    </div>
  </header>

  <main class="shell">
    <section>
      <div class="section-heading">
        <p class="eyebrow">Brasil</p>
        <h2>Indicadores principais</h2>
      </div>
      <div class="cards">
        {_kpi_cards(kpis)}
      </div>
    </section>

    <section>
      <div class="section-heading">
        <p class="eyebrow">Série temporal</p>
        <h2>Evolução dos preços</h2>
      </div>
      <figure class="panel">
        <img
          src="assets/tendencia_brasil_2026.png"
          alt="Tendência dos preços médios no Brasil em 2026"
        />
        <figcaption>
          Indicador mensal derivado das observações semanais oficiais.
        </figcaption>
      </figure>
    </section>

    <section class="two-column">
      <div>
        <div class="section-heading">
          <p class="eyebrow">Geografia</p>
          <h2>Ranking por UF</h2>
        </div>
        <div class="panel table-panel">
          <p class="note">Produto: {html.escape(ranking_product)}</p>
          <table>
            <thead>
              <tr>
                <th>UF</th>
                <th>Preço médio</th>
                <th>Postos</th>
              </tr>
            </thead>
            <tbody>
              {ranking_rows}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <div class="section-heading">
          <p class="eyebrow">Qualidade</p>
          <h2>Cobertura dos dados</h2>
        </div>
        <div class="quality-grid">
          {_quality_cards(aggregate_quality, station_quality)}
        </div>
      </div>
    </section>

    <section class="two-column">
      <figure class="panel">
        <img
          src="assets/ranking_ufs_gasolina.png"
          alt="Ranking dos maiores preços médios por UF"
        />
      </figure>
      <figure class="panel">
        <img
          src="assets/etanol_gasolina_municipios.png"
          alt="Relação entre preços de etanol e gasolina por município"
        />
      </figure>
    </section>

    <section>
      <div class="section-heading">
        <p class="eyebrow">Mercado por posto</p>
        <h2>Dispersão e bandeiras</h2>
      </div>
      <div class="two-column">
        <figure class="panel">
          <img
            src="assets/dispersao_municipios_postos.png"
            alt="Dispersão dos preços observados por município"
          />
          <figcaption>
            Intervalo interquartil em municípios com pelo menos 3 postos.
          </figcaption>
        </figure>
        <figure class="panel">
          <img
            src="assets/mediana_bandeiras_postos.png"
            alt="Mediana dos preços observados por bandeira"
          />
          <figcaption>
            Comparação exibida somente para bandeiras com amostra suficiente.
          </figcaption>
        </figure>
      </div>
    </section>

    <section class="method">
      <p class="eyebrow">Metodologia</p>
      <h2>Leitura responsável</h2>
      <p>
        Os agregados nacionais, regionais e estaduais preservam os
        indicadores publicados pela ANP. Cálculos derivados pelo projeto
        são identificados separadamente. Valores extremos não são removidos
        automaticamente.
      </p>
      <p>
        <a
          href="{RESULTS_URL}"
          target="_blank"
          rel="noopener noreferrer"
        >Relatório detalhado</a>
        <span aria-hidden="true"> · </span>
        <a
          href="{REPOSITORY_URL}"
          target="_blank"
          rel="noopener noreferrer"
        >Documentação técnica</a>
      </p>
    </section>
  </main>

  <footer>
    <div class="shell">
      Fonte: Agência Nacional do Petróleo, Gás Natural e Biocombustíveis.
    </div>
  </footer>
</body>
</html>
"""

    output = (
        docs_dir
        / "index.html"
    )
    output.write_text(
        page,
        encoding="utf-8",
    )
    return output


def main() -> None:
    output = build_site(
        ANALYTICS_DIR
        / "kpis_brasil_2026.csv",
        ANALYTICS_DIR
        / "ranking_ufs_ultima_semana.csv",
        SNAPSHOT_DIR,
        DOCS_DIR,
        REPORTS_DIR
        / "quality_2026.json",
        REPORTS_DIR
        / "quality_postos_2026.json",
    )
    print(
        "Relatório web: "
        f"{output.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
