import os
from pathlib import Path

import pytest

import src.snapshot as snapshot_module
from src.snapshot import (
    SNAPSHOT_IMAGES,
    _replace_snapshot_bundle,
    _validate_report_bundle_freshness,
    publish_snapshot,
)


def _create_required_files(
    root: Path,
) -> tuple[Path, Path]:
    insights = root / "insights.md"
    insights.write_text(
        "# Insights automáticos\n\nConteúdo real.",
        encoding="utf-8",
    )

    generated = root / "generated"
    generated.mkdir()

    for filename in SNAPSHOT_IMAGES:
        (generated / filename).write_bytes(b"png")

    return insights, generated


def test_publish_snapshot_creates_document_and_images(
    tmp_path: Path,
) -> None:
    insights, generated = _create_required_files(tmp_path)
    snapshot = tmp_path / "snapshot"
    results = tmp_path / "resultados.md"

    publish_snapshot(
        insights,
        generated,
        snapshot,
        results,
    )

    assert results.exists()
    text = results.read_text(encoding="utf-8")
    assert "Conteúdo real." in text
    assert "assets/snapshot" in text

    for filename in SNAPSHOT_IMAGES:
        assert (snapshot / filename).exists()


def test_publish_snapshot_fails_without_generated_files(
    tmp_path: Path,
) -> None:
    insights = tmp_path / "insights.md"
    insights.write_text("ok", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        publish_snapshot(
            insights,
            tmp_path / "generated",
            tmp_path / "snapshot",
            tmp_path / "resultados.md",
        )



def _write_bundle_item(
    path: Path,
    content: bytes = b"novo",
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(
        content
    )
    return path


def test_replace_snapshot_bundle_replaces_all_targets(
    tmp_path: Path,
) -> None:
    stage = (
        tmp_path
        / "stage"
    )
    stage.mkdir()

    staged_snapshot = (
        stage
        / "snapshot"
    )
    staged_snapshot.mkdir()
    _write_bundle_item(
        staged_snapshot
        / "novo.png"
    )
    staged_results = (
        stage
        / "docs"
        / "resultados-2026.md"
    )
    _write_bundle_item(
        staged_results
    )
    staged_assets = (
        stage
        / "docs"
        / "assets"
    )
    staged_assets.mkdir()
    _write_bundle_item(
        staged_assets
        / "novo.png"
    )
    staged_index = (
        stage
        / "docs"
        / "index.html"
    )
    _write_bundle_item(
        staged_index
    )
    staged_readme = (
        stage
        / "README.md"
    )
    _write_bundle_item(
        staged_readme
    )

    snapshot = (
        tmp_path
        / "project"
        / "assets"
        / "snapshot"
    )
    snapshot.mkdir(
        parents=True,
    )
    _write_bundle_item(
        snapshot
        / "antigo.png",
        b"antigo",
    )
    results = (
        tmp_path
        / "project"
        / "docs"
        / "resultados-2026.md"
    )
    _write_bundle_item(
        results,
        b"antigo",
    )
    assets = (
        tmp_path
        / "project"
        / "docs"
        / "assets"
    )
    assets.mkdir()
    _write_bundle_item(
        assets
        / "antigo.png",
        b"antigo",
    )
    index = (
        tmp_path
        / "project"
        / "docs"
        / "index.html"
    )
    _write_bundle_item(
        index,
        b"antigo",
    )
    readme = (
        tmp_path
        / "project"
        / "README.md"
    )
    _write_bundle_item(
        readme,
        b"antigo",
    )

    _replace_snapshot_bundle(
        [
            (
                staged_snapshot,
                snapshot,
            ),
            (
                staged_results,
                results,
            ),
            (
                staged_assets,
                assets,
            ),
            (
                staged_index,
                index,
            ),
            (
                staged_readme,
                readme,
            ),
        ]
    )

    assert not (
        snapshot
        / "antigo.png"
    ).exists()
    assert (
        snapshot
        / "novo.png"
    ).exists()
    assert (
        results.read_bytes()
        == b"novo"
    )
    assert (
        assets
        / "novo.png"
    ).exists()
    assert (
        index.read_bytes()
        == b"novo"
    )
    assert (
        readme.read_bytes()
        == b"novo"
    )


def test_replace_snapshot_bundle_failure_restores_every_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = (
        tmp_path
        / "stage"
    )
    stage.mkdir()

    staged_snapshot = (
        stage
        / "snapshot"
    )
    staged_snapshot.mkdir()
    _write_bundle_item(
        staged_snapshot
        / "novo.png"
    )
    staged_results = (
        stage
        / "docs"
        / "resultados-2026.md"
    )
    _write_bundle_item(
        staged_results
    )
    staged_assets = (
        stage
        / "docs"
        / "assets"
    )
    staged_assets.mkdir()
    _write_bundle_item(
        staged_assets
        / "novo.png"
    )
    staged_index = (
        stage
        / "docs"
        / "index.html"
    )
    _write_bundle_item(
        staged_index
    )
    staged_readme = (
        stage
        / "README.md"
    )
    _write_bundle_item(
        staged_readme
    )

    project = (
        tmp_path
        / "project"
    )
    snapshot = (
        project
        / "assets"
        / "snapshot"
    )
    snapshot.mkdir(
        parents=True,
    )
    old_snapshot = (
        snapshot
        / "antigo.png"
    )
    _write_bundle_item(
        old_snapshot,
        b"snapshot-antigo",
    )

    results = (
        project
        / "docs"
        / "resultados-2026.md"
    )
    _write_bundle_item(
        results,
        b"resultados-antigos",
    )
    assets = (
        project
        / "docs"
        / "assets"
    )
    assets.mkdir()
    old_asset = (
        assets
        / "antigo.png"
    )
    _write_bundle_item(
        old_asset,
        b"asset-antigo",
    )
    index = (
        project
        / "docs"
        / "index.html"
    )
    _write_bundle_item(
        index,
        b"index-antigo",
    )
    readme = (
        project
        / "README.md"
    )
    _write_bundle_item(
        readme,
        b"readme-antigo",
    )

    original_move = (
        snapshot_module.shutil.move
    )

    def failing_move(
        source: str,
        destination: str,
    ):
        source_path = Path(
            source
        )
        destination_path = Path(
            destination
        )
        if (
            source_path.name
            == "index.html"
            and destination_path
            == index
        ):
            raise OSError(
                "falha simulada"
            )
        return original_move(
            source,
            destination,
        )

    monkeypatch.setattr(
        snapshot_module.shutil,
        "move",
        failing_move,
    )

    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        _replace_snapshot_bundle(
            [
                (
                    staged_snapshot,
                    snapshot,
                ),
                (
                    staged_results,
                    results,
                ),
                (
                    staged_assets,
                    assets,
                ),
                (
                    staged_index,
                    index,
                ),
                (
                    staged_readme,
                    readme,
                ),
            ]
        )

    assert (
        old_snapshot.read_bytes()
        == b"snapshot-antigo"
    )
    assert (
        results.read_bytes()
        == b"resultados-antigos"
    )
    assert (
        old_asset.read_bytes()
        == b"asset-antigo"
    )
    assert (
        index.read_bytes()
        == b"index-antigo"
    )
    assert (
        readme.read_bytes()
        == b"readme-antigo"
    )
    assert not (
        snapshot
        / "novo.png"
    ).exists()
    assert not (
        assets
        / "novo.png"
    ).exists()


def test_replace_snapshot_bundle_rejects_empty_staged_file(
    tmp_path: Path,
) -> None:
    staged = (
        tmp_path
        / "stage"
        / "README.md"
    )
    _write_bundle_item(
        staged,
        b"",
    )

    with pytest.raises(
        ValueError,
        match="Item vazio",
    ):
        _replace_snapshot_bundle(
            [
                (
                    staged,
                    tmp_path
                    / "project"
                    / "README.md",
                )
            ]
        )



def test_publish_snapshot_rejects_empty_required_file(
    tmp_path: Path,
) -> None:
    insights, generated = (
        _create_required_files(
            tmp_path
        )
    )
    (
        generated
        / SNAPSHOT_IMAGES[0]
    ).write_bytes(
        b""
    )

    with pytest.raises(
        ValueError,
        match="estão vazios",
    ):
        publish_snapshot(
            insights,
            generated,
            tmp_path
            / "snapshot",
            tmp_path
            / "resultados.md",
        )


def test_report_bundle_freshness_accepts_current_artifacts(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    artifact = tmp_path / "chart.png"
    source.write_text(
        "dados",
        encoding="utf-8",
    )
    artifact.write_bytes(
        b"png"
    )
    os.utime(
        source,
        (100, 100),
    )
    os.utime(
        artifact,
        (200, 200),
    )

    _validate_report_bundle_freshness(
        [source],
        [artifact],
    )


def test_report_bundle_freshness_rejects_stale_artifact(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    artifact = tmp_path / "chart.png"
    source.write_text(
        "dados",
        encoding="utf-8",
    )
    artifact.write_bytes(
        b"png"
    )
    os.utime(
        source,
        (200, 200),
    )
    os.utime(
        artifact,
        (100, 100),
    )

    with pytest.raises(
        ValueError,
        match="Bundle visual desatualizado",
    ):
        _validate_report_bundle_freshness(
            [source],
            [artifact],
        )


def test_report_bundle_freshness_requires_all_inputs(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "chart.png"
    artifact.write_bytes(
        b"png"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Arquivos ausentes",
    ):
        _validate_report_bundle_freshness(
            [tmp_path / "missing.csv"],
            [artifact],
        )
