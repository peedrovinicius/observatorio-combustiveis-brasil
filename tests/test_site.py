from pathlib import Path

import pandas as pd

from src.site import (
    REPOSITORY_URL,
    _common_gasoline,
    RESULTS_URL,
    SITE_IMAGES,
    build_site,
)


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
            "data_inicial": ["2026-09-20", "2026-09-20"],
            "data_final": ["2026-09-26", "2026-09-26"],
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
    assert "semana 20/09/2026 a 26/09/2026" in text
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



def test_build_site_uses_publish_safe_documentation_links(
    tmp_path: Path,
) -> None:
    kpis, ranking, snapshot = (
        _write_inputs(tmp_path)
    )
    docs = tmp_path / "docs"

    output = build_site(
        kpis,
        ranking,
        snapshot,
        docs,
    )

    text = output.read_text(
        encoding="utf-8"
    )

    assert (
        f'href="{REPOSITORY_URL}"'
        in text
    )
    assert (
        f'href="{RESULTS_URL}"'
        in text
    )
    assert '../README.md' not in text



def test_common_gasoline_returns_none_without_common_gasoline() -> None:
    products = pd.Series(
        [
            "GASOLINA ADITIVADA",
            "ETANOL HIDRATADO",
        ]
    )

    assert (
        _common_gasoline(
            products
        )
        is None
    )


def test_build_site_does_not_substitute_another_product_for_common_gasoline(
    tmp_path: Path,
) -> None:
    kpis = (
        tmp_path
        / "kpis.csv"
    )
    pd.DataFrame(
        {
            "produto": [
                "ETANOL HIDRATADO",
            ],
            "preco_atual": [
                4.50,
            ],
            "variacao_semanal_pct": [
                1.0,
            ],
            "variacao_desde_inicio_ano_pct": [
                2.0,
            ],
            "menor_preco_2026": [
                4.20,
            ],
            "maior_preco_2026": [
                4.70,
            ],
        }
    ).to_csv(
        kpis,
        index=False,
    )

    ranking = (
        tmp_path
        / "ranking.csv"
    )
    pd.DataFrame(
        {
            "produto": [
                "ETANOL HIDRATADO",
                "GASOLINA ADITIVADA",
            ],
            "uf": [
                "CE",
                "SP",
            ],
            "preco_medio_revenda": [
                4.50,
                6.50,
            ],
            "postos_pesquisados": [
                20,
                30,
            ],
        }
    ).to_csv(
        ranking,
        index=False,
    )

    snapshot = (
        tmp_path
        / "snapshot"
    )
    snapshot.mkdir()
    for filename in SITE_IMAGES:
        (
            snapshot
            / filename
        ).write_bytes(
            b"png"
        )

    docs = (
        tmp_path
        / "docs"
    )
    output = build_site(
        kpis,
        ranking,
        snapshot,
        docs,
    )

    text = output.read_text(
        encoding="utf-8"
    )

    assert (
        "Série: Gasolina comum indisponível"
        in text
    )
    assert (
        "Série: ETANOL HIDRATADO"
        not in text
    )
    assert (
        "Série: GASOLINA ADITIVADA"
        not in text
    )


def test_ranking_rows_handles_empty_ranking_schema() -> None:
    from src.site import (
        _ranking_rows,
    )

    rows, product = (
        _ranking_rows(
            pd.DataFrame()
        )
    )

    assert rows == ""
    assert (
        product
        == "Gasolina comum indisponível"
    )


def test_ranking_rows_rejects_mixed_units() -> None:
    from src.site import _ranking_rows

    ranking = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/M3",
            ],
            "uf": [
                "CE",
                "SP",
            ],
            "preco_medio_revenda": [
                6.30,
                6300.0,
            ],
            "postos_pesquisados": [
                20,
                20,
            ],
        }
    )

    rows, label = _ranking_rows(
        ranking
    )

    assert rows == ""
    assert label == (
        "Gasolina comum "
        "com múltiplas unidades"
    )


def test_kpi_cards_expose_unit_when_available() -> None:
    from src.site import _kpi_cards

    cards = _kpi_cards(
        pd.DataFrame(
            {
                "produto": [
                    "GASOLINA COMUM"
                ],
                "unidade_medida": [
                    "R$/L"
                ],
                "preco_atual": [
                    6.25
                ],
            }
        )
    )

    assert "GASOLINA COMUM · R$/L" in cards


def test_common_gasoline_ignores_premium() -> None:
    products = pd.Series(
        [
            "GASOLINA PREMIUM",
            "GASOLINA COMUM",
        ]
    )

    assert (
        _common_gasoline(
            products
        )
        == "GASOLINA COMUM"
    )


def test_common_gasoline_accepts_plain_alias() -> None:
    products = pd.Series(
        [
            "GASOLINA",
            "ETANOL",
        ]
    )

    assert (
        _common_gasoline(
            products
        )
        == "GASOLINA"
    )


def test_common_gasoline_rejects_multiple_aliases() -> None:
    products = pd.Series(
        [
            "GASOLINA",
            "GASOLINA COMUM",
        ]
    )

    assert (
        _common_gasoline(
            products
        )
        is None
    )


def test_quality_cards_prefers_total_station_identity_count() -> None:
    from src.site import _quality_cards

    cards = _quality_cards(
        {"status": "passed"},
        {
            "status": "passed",
            "municipios": 10,
            "postos_distintos": 25,
            "postos_distintos_cnpj": 20,
        },
    )

    assert "Postos distintos" in cards
    assert "<strong>25</strong>" in cards
    assert "Postos por CNPJ" not in cards


def test_ranking_rows_rejects_multiple_dates() -> None:
    from src.site import _ranking_rows

    ranking = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/L",
            ],
            "data_inicial": [
                "2026-09-13",
                "2026-09-20",
            ],
            "uf": [
                "CE",
                "SP",
            ],
            "preco_medio_revenda": [
                6.30,
                6.10,
            ],
        }
    )

    rows, label = _ranking_rows(
        ranking
    )

    assert rows == ""
    assert "período ambíguo" in label


def test_ranking_rows_formats_missing_station_count_as_nd() -> None:
    from src.site import _ranking_rows

    ranking = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
            ],
            "unidade_medida": [
                "R$/L",
            ],
            "data_inicial": [
                "2026-09-20",
            ],
            "data_final": [
                "2026-09-26",
            ],
            "uf": [
                "CE",
            ],
            "preco_medio_revenda": [
                6.30,
            ],
            "postos_pesquisados": [
                pd.NA,
            ],
        }
    )

    rows, _ = _ranking_rows(
        ranking
    )

    assert "<td>n/d</td>" in rows
    assert "nan" not in rows.lower()
    assert "&lt;na&gt;" not in rows.lower()


def test_ranking_rows_formats_station_count_as_integer() -> None:
    from src.site import _ranking_rows

    ranking = pd.DataFrame(
        {
            "produto": ["GASOLINA COMUM"],
            "unidade_medida": ["R$/L"],
            "uf": ["CE"],
            "preco_medio_revenda": [6.30],
            "postos_pesquisados": [1234.0],
        }
    )

    rows, _ = _ranking_rows(
        ranking
    )

    assert "<td>1.234</td>" in rows
    assert "1234.0" not in rows


def test_site_main_blocks_partial_publication() -> None:
    from src.site import main

    try:
        main()
    except SystemExit as error:
        assert "src.snapshot" in str(error)
    else:
        raise AssertionError(
            "Era esperado SystemExit"
        )
