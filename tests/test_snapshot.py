from pathlib import Path

import pytest

from src.snapshot import SNAPSHOT_IMAGES, publish_snapshot


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
