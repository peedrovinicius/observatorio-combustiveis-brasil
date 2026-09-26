from pathlib import Path

import pytest

from src.config import PROJECT_ROOT
from src.publish_readme import (
    END_MARKER,
    START_MARKER,
    update_readme_results,
)


def test_publish_readme_inserts_results_block(
    tmp_path: Path,
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Projeto\n\n## Saídas analíticas\n\nConteúdo.",
        encoding="utf-8",
    )
    results = (
        tmp_path
        / "resultados.md"
    )
    results.write_text(
        "resultado",
        encoding="utf-8",
    )

    update_readme_results(
        readme,
        results,
    )

    text = (
        readme.read_text(
            encoding="utf-8"
        )
    )
    assert START_MARKER in text
    assert END_MARKER in text
    assert (
        "Resultados reais de 2026"
        in text
    )
    assert (
        "assets/snapshot/tendencia_brasil_2026.png"
        in text
    )
    assert (
        "assets/snapshot/dispersao_municipios_postos.png"
        in text
    )
    assert (
        "assets/snapshot/mediana_bandeiras_postos.png"
        in text
    )


def test_publish_readme_replaces_existing_block(
    tmp_path: Path,
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Projeto\n\n"
        + START_MARKER
        + "\nconteúdo antigo\n"
        + END_MARKER
        + "\n\n## Saídas analíticas",
        encoding="utf-8",
    )
    results = (
        tmp_path
        / "resultados.md"
    )
    results.write_text(
        "resultado",
        encoding="utf-8",
    )

    update_readme_results(
        readme,
        results,
    )

    text = (
        readme.read_text(
            encoding="utf-8"
        )
    )
    assert (
        text.count(
            START_MARKER
        )
        == 1
    )
    assert (
        "conteúdo antigo"
        not in text
    )
    assert (
        "Resultados reais de 2026"
        in text
    )


def test_publish_readme_requires_results_document(
    tmp_path: Path,
) -> None:
    readme = (
        tmp_path
        / "README.md"
    )
    readme.write_text(
        "# Projeto",
        encoding="utf-8",
    )

    with pytest.raises(
        FileNotFoundError
    ):
        update_readme_results(
            readme,
            tmp_path
            / "missing.md",
        )



def test_repository_readme_keeps_results_markers() -> None:
    readme = (
        PROJECT_ROOT
        / "README.md"
    )
    content = readme.read_text(
        encoding="utf-8",
    )

    assert (
        content.count(
            START_MARKER
        )
        == 1
    )
    assert (
        content.count(
            END_MARKER
        )
        == 1
    )
    assert (
        content.index(
            START_MARKER
        )
        < content.index(
            END_MARKER
        )
    )
    assert (
        content.index(
            END_MARKER
        )
        < content.index(
            "## Saídas analíticas"
        )
    )
