from pathlib import Path

import pytest

from src.config import PROJECT_ROOT
from src.publish_readme import (
    END_MARKER,
    README_IMAGES,
    START_MARKER,
    update_readme_results,
)


def _write_snapshot_images(
    root: Path,
) -> Path:
    snapshot = root / "snapshot"
    snapshot.mkdir()
    for filename in README_IMAGES:
        (
            snapshot
            / filename
        ).write_bytes(
            b"png"
        )
    return snapshot


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

    snapshot = _write_snapshot_images(
        tmp_path
    )

    update_readme_results(
        readme,
        results,
        snapshot,
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

    snapshot = _write_snapshot_images(
        tmp_path
    )

    update_readme_results(
        readme,
        results,
        snapshot,
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
            tmp_path
            / "missing-snapshot",
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


def test_publish_readme_requires_all_snapshot_images(
    tmp_path: Path,
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Projeto\n\n## Saídas analíticas",
        encoding="utf-8",
    )
    results = tmp_path / "resultados.md"
    results.write_text(
        "resultado",
        encoding="utf-8",
    )
    snapshot = _write_snapshot_images(
        tmp_path
    )
    (
        snapshot
        / README_IMAGES[0]
    ).unlink()

    with pytest.raises(
        FileNotFoundError,
        match="snapshot público está incompleto",
    ):
        update_readme_results(
            readme,
            results,
            snapshot,
        )


def test_publish_readme_rejects_empty_public_asset(
    tmp_path: Path,
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Projeto\n\n## Saídas analíticas",
        encoding="utf-8",
    )
    results = tmp_path / "resultados.md"
    results.write_text(
        "resultado",
        encoding="utf-8",
    )
    snapshot = _write_snapshot_images(
        tmp_path
    )
    (
        snapshot
        / README_IMAGES[0]
    ).write_bytes(b"")

    with pytest.raises(
        ValueError,
        match="arquivos vazios",
    ):
        update_readme_results(
            readme,
            results,
            snapshot,
        )


def test_repository_public_snapshot_is_all_or_nothing() -> None:
    readme = (
        PROJECT_ROOT
        / "README.md"
    ).read_text(
        encoding="utf-8",
    )
    block = (
        readme.split(
            START_MARKER,
            1,
        )[1]
        .split(
            END_MARKER,
            1,
        )[0]
        .strip()
    )

    snapshot_dir = (
        PROJECT_ROOT
        / "assets"
        / "snapshot"
    )
    results = (
        PROJECT_ROOT
        / "docs"
        / "resultados-2026.md"
    )
    site = (
        PROJECT_ROOT
        / "docs"
        / "index.html"
    )
    site_assets = (
        PROJECT_ROOT
        / "docs"
        / "assets"
    )
    snapshot_images = [
        snapshot_dir
        / filename
        for filename in README_IMAGES
    ]
    public_items = [
        results,
        site,
        site_assets,
        *snapshot_images,
    ]
    existing = [
        path.exists()
        for path in public_items
    ]

    if any(existing):
        assert all(existing)
        assert (
            "## Resultados reais de 2026"
            in block
        )
    else:
        assert block == ""


def test_publish_readme_main_blocks_partial_publication() -> None:
    from src.publish_readme import main

    try:
        main()
    except SystemExit as error:
        assert "src.snapshot" in str(error)
    else:
        raise AssertionError(
            "Era esperado SystemExit"
        )
