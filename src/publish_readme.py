from __future__ import annotations

from pathlib import Path

from .config import PROJECT_ROOT
from .publication_contract import (
    PUBLIC_IMAGE_FILES,
)

README_PATH = (
    PROJECT_ROOT
    / "README.md"
)
RESULTS_DOC = (
    PROJECT_ROOT
    / "docs"
    / "resultados-2026.md"
)
SNAPSHOT_DIR = (
    PROJECT_ROOT
    / "assets"
    / "snapshot"
)
README_IMAGES = PUBLIC_IMAGE_FILES
START_MARKER = (
    "<!-- RESULTS:START -->"
)
END_MARKER = (
    "<!-- RESULTS:END -->"
)


def build_results_block() -> str:
    return f"""{START_MARKER}

## Resultados reais de 2026

Os resultados abaixo são gerados pelo pipeline a partir das fontes públicas oficiais da ANP.

[Ver relatório completo](docs/resultados-2026.md)

<p align="center">
  <img src="assets/snapshot/tendencia_brasil_2026.png" alt="Tendência dos preços no Brasil em 2026" width="95%" />
</p>

<p align="center">
  <img src="assets/snapshot/ranking_ufs_gasolina.png" alt="Ranking de preços por UF" width="47%" />
  <img src="assets/snapshot/etanol_gasolina_municipios.png" alt="Relação entre etanol e gasolina por município" width="47%" />
</p>

<p align="center">
  <img src="assets/snapshot/dispersao_municipios_postos.png" alt="Dispersão dos preços observados por município" width="47%" />
  <img src="assets/snapshot/mediana_bandeiras_postos.png" alt="Mediana dos preços observados por bandeira" width="47%" />
</p>

{END_MARKER}"""


def update_readme_results(
    readme_path: Path = README_PATH,
    results_doc: Path = RESULTS_DOC,
    snapshot_dir: Path = SNAPSHOT_DIR,
) -> None:
    required = [
        results_doc,
        *[
            snapshot_dir
            / filename
            for filename
            in README_IMAGES
        ],
    ]
    missing = [
        path
        for path in required
        if not path.exists()
    ]
    if missing:
        formatted = "\n".join(
            f"- {path}"
            for path in missing
        )
        raise FileNotFoundError(
            "O snapshot público está incompleto. "
            "Gere o snapshot antes de atualizar o README.\n"
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
            "O snapshot público contém arquivos vazios.\n"
            f"Vazios:\n{formatted}"
        )

    content = (
        readme_path
        .read_text(
            encoding="utf-8"
        )
    )
    block = (
        build_results_block()
    )

    if (
        START_MARKER
        in content
        and END_MARKER
        in content
    ):
        before = (
            content
            .split(
                START_MARKER,
                1,
            )[0]
            .rstrip()
        )
        after = (
            content
            .split(
                END_MARKER,
                1,
            )[1]
            .lstrip()
        )
        updated = (
            before
            + "\n\n"
            + block
            + "\n\n"
            + after
        )
    else:
        anchor = (
            "## Saídas analíticas"
        )
        if anchor not in content:
            raise ValueError(
                "Não foi encontrado um ponto seguro "
                "para inserir os resultados."
            )
        updated = content.replace(
            anchor,
            block
            + "\n\n"
            + anchor,
            1,
        )

    readme_path.write_text(
        updated,
        encoding="utf-8",
    )


def main() -> None:
    raise SystemExit(
        "A publicação isolada do README foi desativada. "
        "Use python -m src.snapshot para atualizar o "
        "bundle público completo."
    )


if __name__ == "__main__":
    main()
