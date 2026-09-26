from pathlib import Path

import pandas as pd

from src.site import SITE_IMAGES, build_site


def _write_inputs(root: Path) -> tuple[Path, Path, Path]:
    kpis = root / "kpis.csv"
    pd.DataFrame(
        {
            "produto": ["GASOLINA COMUM"],
            "preco_atual": [6.25],
            "variacao_semanal_pct": [1.5],
            "variacao_desde_inicio_ano_pct": [2.0],
            "menor_preco_2026": [5.90],
            "maior_preco_2026": [6.40],
        }
    ).to_csv(kpis, index=False)

    ranking = root / "ranking.csv"
    pd.DataFrame(
        {
            "produto": ["GASOLINA COMUM", "GASOLINA COMUM"],
            "uf": ["CE", "SP"],
            "preco_medio_revenda": [6.30, 6.10],
            "postos_pesquisados": [20, 40],
        }
    ).to_csv(ranking, index=False)

    snapshot = root / "snapshot"
    snapshot.mkdir()
    for filename in SITE_IMAGES:
        (snapshot / filename).write_bytes(b"png")

    return kpis, ranking, snapshot


def test_build_site_uses_real_values_from_inputs(
    tmp_path: Path,
) -> None:
    kpis, ranking, snapshot = _write_inputs(tmp_path)
    docs = tmp_path / "docs"

    output = build_site(
        kpis,
        ranking,
        snapshot,
        docs,
    )

    text = output.read_text(encoding="utf-8")
    assert "R$ 6,25" in text
    assert "+1,50%" in text
    assert "CE" in text
    assert "R$ 6,30" in text
    assert "placeholder" not in text.lower()

    for filename in SITE_IMAGES:
        assert (docs / "assets" / filename).exists()


def test_build_site_requires_snapshot_images(
    tmp_path: Path,
) -> None:
    kpis, ranking, _ = _write_inputs(tmp_path)

    missing_snapshot = tmp_path / "missing"
    docs = tmp_path / "docs"

    try:
        build_site(
            kpis,
            ranking,
            missing_snapshot,
            docs,
        )
    except FileNotFoundError as error:
        assert "Arquivos ausentes" in str(error)
    else:
        raise AssertionError("Era esperado FileNotFoundError")
