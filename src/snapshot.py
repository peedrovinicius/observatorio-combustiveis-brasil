from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    PROJECT_ROOT,
    REPORTS_DIR,
)
from .publish_readme import (
    update_readme_results,
)
from .site import build_site

GENERATED_DIR = (
    PROJECT_ROOT
    / "assets"
    / "generated"
)
SNAPSHOT_DIR = (
    PROJECT_ROOT
    / "assets"
    / "snapshot"
)
RESULTS_DOC = (
    PROJECT_ROOT
    / "docs"
    / "resultados-2026.md"
)
DOCS_DIR = (
    PROJECT_ROOT
    / "docs"
)
ANALYTICS_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "analytics"
)

SNAPSHOT_IMAGES = [
    "tendencia_brasil_2026.png",
    "ranking_ufs_gasolina.png",
    "etanol_gasolina_municipios.png",
    "dispersao_municipios_postos.png",
    "mediana_bandeiras_postos.png",
]


def publish_snapshot(
    insights_path: Path,
    generated_dir: Path,
    snapshot_dir: Path,
    results_doc: Path,
) -> None:
    required = [
        insights_path,
        *[
            generated_dir
            / filename
            for filename
            in SNAPSHOT_IMAGES
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
            "Arquivos necessários para o snapshot "
            "não foram encontrados. "
            "Execute o pipeline completo antes de publicar.\n"
            f"Ausentes:\n{formatted}"
        )

    snapshot_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    results_doc.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    for filename in SNAPSHOT_IMAGES:
        shutil.copy2(
            generated_dir / filename,
            snapshot_dir / filename,
        )

    insights = (
        insights_path
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )
    generated_at = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    )

    document = f"""# Resultados 2026

Snapshot gerado automaticamente a partir dos dados processados pelo pipeline.

Gerado em: **{generated_at}**

> Este arquivo não deve ser editado manualmente para alterar métricas. Reexecute o pipeline e o comando de snapshot para atualizar os resultados.

{insights}

## Visualizações

### Tendência Brasil

![Tendência Brasil](../assets/snapshot/tendencia_brasil_2026.png)

### Ranking de UFs

![Ranking de UFs](../assets/snapshot/ranking_ufs_gasolina.png)

### Etanol x gasolina

![Etanol x gasolina](../assets/snapshot/etanol_gasolina_municipios.png)

### Dispersão municipal por posto

![Dispersão municipal por posto](../assets/snapshot/dispersao_municipios_postos.png)

### Mediana por bandeira

![Mediana por bandeira](../assets/snapshot/mediana_bandeiras_postos.png)
"""

    results_doc.write_text(
        document,
        encoding="utf-8",
    )


def main() -> None:
    publish_snapshot(
        REPORTS_DIR
        / "insights_2026.md",
        GENERATED_DIR,
        SNAPSHOT_DIR,
        RESULTS_DOC,
    )

    build_site(
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

    update_readme_results(
        PROJECT_ROOT
        / "README.md",
        RESULTS_DOC,
    )

    print(
        "Snapshot criado, site estático gerado "
        "e README atualizado localmente. "
        "Revise docs/, assets/snapshot/ "
        "e o diff do README antes de versionar."
    )


if __name__ == "__main__":
    main()
