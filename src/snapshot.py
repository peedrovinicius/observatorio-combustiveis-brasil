from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import PROJECT_ROOT, REPORTS_DIR

GENERATED_DIR = PROJECT_ROOT / "assets" / "generated"
SNAPSHOT_DIR = PROJECT_ROOT / "assets" / "snapshot"
RESULTS_DOC = PROJECT_ROOT / "docs" / "resultados-2026.md"

SNAPSHOT_IMAGES = [
    "tendencia_brasil_2026.png",
    "ranking_ufs_gasolina.png",
    "etanol_gasolina_municipios.png",
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
            generated_dir / filename
            for filename in SNAPSHOT_IMAGES
        ],
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Arquivos necessários para o snapshot não foram encontrados. "
            "Execute o pipeline completo antes de publicar.\n"
            f"Ausentes:\n{formatted}"
        )

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    results_doc.parent.mkdir(parents=True, exist_ok=True)

    for filename in SNAPSHOT_IMAGES:
        shutil.copy2(
            generated_dir / filename,
            snapshot_dir / filename,
        )

    insights = insights_path.read_text(encoding="utf-8").strip()
    generated_at = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
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
"""

    results_doc.write_text(document, encoding="utf-8")


def main() -> None:
    publish_snapshot(
        REPORTS_DIR / "insights_2026.md",
        GENERATED_DIR,
        SNAPSHOT_DIR,
        RESULTS_DOC,
    )

    print(
        "Snapshot criado. Revise docs/resultados-2026.md "
        "e assets/snapshot/ antes de versionar."
    )


if __name__ == "__main__":
    main()
