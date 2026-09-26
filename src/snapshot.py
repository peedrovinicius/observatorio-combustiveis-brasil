from __future__ import annotations

import shutil
import tempfile
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

    empty = [
        path
        for path in required
        if (
            path.is_file()
            and path.stat().st_size <= 0
        )
    ]
    if empty:
        formatted = "\n".join(
            f"- {path}"
            for path in empty
        )
        raise ValueError(
            "Arquivos necessários para o snapshot "
            "estão vazios.\n"
            f"Vazios:\n{formatted}"
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


def _remove_path(
    path: Path,
) -> None:
    if path.is_dir():
        shutil.rmtree(
            path
        )
    elif path.exists():
        path.unlink()


def _replace_snapshot_bundle(
    replacements: list[
        tuple[
            Path,
            Path,
        ]
    ],
) -> None:
    if not replacements:
        raise ValueError(
            "Bundle de snapshot vazio."
        )

    destinations = [
        destination
        for _, destination
        in replacements
    ]
    if len(destinations) != len(
        set(destinations)
    ):
        raise ValueError(
            "Bundle de snapshot contém "
            "destinos duplicados."
        )

    for staged, destination in replacements:
        if not staged.exists():
            raise FileNotFoundError(
                "Item do snapshot em staging "
                f"não encontrado: {staged}"
            )
        if (
            staged.is_file()
            and staged.stat().st_size <= 0
        ):
            raise ValueError(
                "Item vazio no staging do snapshot: "
                f"{staged.name}"
            )
        if (
            staged.is_dir()
            and not any(
                staged.iterdir()
            )
        ):
            raise ValueError(
                "Diretório vazio no staging do snapshot: "
                f"{staged.name}"
            )
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    stage_root = (
        replacements[0][0].parent
    )
    backup_root = (
        stage_root
        / "snapshot_backup"
    )
    backup_root.mkdir(
        exist_ok=False
    )

    backed_up: list[
        tuple[
            Path,
            Path,
        ]
    ] = []
    installed: list[
        Path
    ] = []

    try:
        for index, (
            _,
            destination,
        ) in enumerate(
            replacements
        ):
            if not destination.exists():
                continue
            backup = (
                backup_root
                / f"{index}_{destination.name}"
            )
            shutil.move(
                str(destination),
                str(backup),
            )
            backed_up.append(
                (
                    destination,
                    backup,
                )
            )

        for staged, destination in replacements:
            shutil.move(
                str(staged),
                str(destination),
            )
            installed.append(
                destination
            )
    except Exception:
        for destination in reversed(
            installed
        ):
            _remove_path(
                destination
            )

        for destination, backup in reversed(
            backed_up
        ):
            if backup.exists():
                shutil.move(
                    str(backup),
                    str(destination),
                )
        raise


def main() -> None:
    readme_path = (
        PROJECT_ROOT
        / "README.md"
    )

    with tempfile.TemporaryDirectory(
        prefix=".snapshot_stage_",
        dir=PROJECT_ROOT,
    ) as temporary:
        stage_root = Path(
            temporary
        )
        staged_snapshot = (
            stage_root
            / "snapshot"
        )
        staged_docs = (
            stage_root
            / "docs"
        )
        staged_results = (
            staged_docs
            / "resultados-2026.md"
        )
        staged_readme = (
            stage_root
            / "README.md"
        )

        publish_snapshot(
            REPORTS_DIR
            / "insights_2026.md",
            GENERATED_DIR,
            staged_snapshot,
            staged_results,
        )

        build_site(
            ANALYTICS_DIR
            / "kpis_brasil_2026.csv",
            ANALYTICS_DIR
            / "ranking_ufs_ultima_semana.csv",
            staged_snapshot,
            staged_docs,
            REPORTS_DIR
            / "quality_2026.json",
            REPORTS_DIR
            / "quality_postos_2026.json",
        )

        shutil.copy2(
            readme_path,
            staged_readme,
        )
        update_readme_results(
            staged_readme,
            staged_results,
        )

        _replace_snapshot_bundle(
            [
                (
                    staged_snapshot,
                    SNAPSHOT_DIR,
                ),
                (
                    staged_results,
                    RESULTS_DOC,
                ),
                (
                    staged_docs
                    / "assets",
                    DOCS_DIR
                    / "assets",
                ),
                (
                    staged_docs
                    / "index.html",
                    DOCS_DIR
                    / "index.html",
                ),
                (
                    staged_readme,
                    readme_path,
                ),
            ]
        )

    print(
        "Snapshot criado, site estático gerado "
        "e README atualizado localmente. "
        "Revise docs/, assets/snapshot/ "
        "e o diff do README antes de versionar."
    )


if __name__ == "__main__":
    main()
