from pathlib import Path

import pandas as pd
import pytest

import src.reporting as reporting_module
from src.reporting import (
    _location_label,
    _publish_report_bundle,
    _select_common_gasoline,
    build_insights_markdown,
    plot_ethanol_gasoline,
    plot_monthly_trend,
    plot_state_ranking,
    plot_station_brand_median,
    plot_station_municipality_dispersion,
)


def test_select_common_gasoline_excludes_additive() -> None:
    products = pd.Series(
        [
            "GASOLINA ADITIVADA",
            "GASOLINA COMUM",
            "ETANOL HIDRATADO",
        ]
    )

    assert (
        _select_common_gasoline(
            products
        )
        == "GASOLINA COMUM"
    )


def test_location_label_handles_missing_uf() -> None:
    row = pd.Series(
        {
            "uf": pd.NA,
            "estado": "CEARA",
        }
    )

    assert (
        _location_label(row)
        == "CEARA"
    )


def test_insights_use_data_values() -> None:
    kpis = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM"
            ],
            "preco_atual": [6.25],
            "variacao_semanal_pct": [
                1.5
            ],
            "variacao_desde_inicio_ano_pct": [
                2.0
            ],
            "menor_preco_2026": [
                5.90
            ],
            "maior_preco_2026": [
                6.40
            ],
        }
    )
    ranking = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "uf": ["CE", "SP"],
            "preco_medio_revenda": [
                6.30,
                6.10,
            ],
        }
    )

    text = build_insights_markdown(
        kpis,
        ranking,
        {
            "status": "passed"
        },
        {
            "status": "passed",
            "postos_distintos_cnpj": 100,
            "municipios": 20,
        },
    )

    assert "R$ 6,25" in text
    assert "+1,50%" in text
    assert "CE: R$ 6,30" in text
    assert (
        "Postos distintos por CNPJ: **100**"
        in text
    )


def test_station_dispersion_chart_is_created(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "uf": [
                "CE",
                "CE",
            ],
            "municipio": [
                "FORTALEZA",
                "CAUCAIA",
            ],
            "postos_distintos": [
                5,
                4,
            ],
            "intervalo_interquartil": [
                0.20,
                0.10,
            ],
        }
    )
    output = (
        tmp_path
        / "dispersao.png"
    )

    plot_station_municipality_dispersion(
        frame,
        output,
    )

    assert output.exists()
    assert (
        output.stat().st_size
        > 0
    )


def test_station_brand_chart_handles_insufficient_sample(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM"
            ],
            "bandeira": ["A"],
            "postos_distintos": [1],
            "observacoes": [1],
            "mediana_observada": [
                6.20
            ],
            "amostra_suficiente": [
                False
            ],
        }
    )
    output = (
        tmp_path
        / "bandeiras.png"
    )

    plot_station_brand_median(
        frame,
        output,
    )

    assert output.exists()
    assert (
        output.stat().st_size
        > 0
    )



def test_select_common_gasoline_returns_none_without_common_gasoline() -> None:
    products = pd.Series(
        [
            "GASOLINA ADITIVADA",
            "ETANOL HIDRATADO",
        ]
    )

    assert (
        _select_common_gasoline(
            products
        )
        is None
    )


def test_monthly_chart_handles_empty_data(
    tmp_path: Path,
) -> None:
    output = (
        tmp_path
        / "mensal.png"
    )

    plot_monthly_trend(
        pd.DataFrame(),
        output,
    )

    assert output.exists()
    assert output.stat().st_size > 0


def test_state_ranking_chart_handles_missing_common_gasoline(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "produto": [
                "ETANOL HIDRATADO",
            ],
            "uf": [
                "CE",
            ],
            "preco_medio_revenda": [
                4.50,
            ],
        }
    )
    output = (
        tmp_path
        / "ranking.png"
    )

    plot_state_ranking(
        frame,
        output,
    )

    assert output.exists()
    assert output.stat().st_size > 0


def test_ethanol_gasoline_chart_handles_empty_data(
    tmp_path: Path,
) -> None:
    output = (
        tmp_path
        / "relacao.png"
    )

    plot_ethanol_gasoline(
        pd.DataFrame(),
        output,
    )

    assert output.exists()
    assert output.stat().st_size > 0



def _create_report_stage(
    root: Path,
) -> tuple[Path, Path]:
    assets = (
        root
        / "generated"
    )
    assets.mkdir(
        parents=True,
    )
    for filename in [
        "tendencia_brasil_2026.png",
        "ranking_ufs_gasolina.png",
        "etanol_gasolina_municipios.png",
        "dispersao_municipios_postos.png",
        "mediana_bandeiras_postos.png",
    ]:
        (
            assets
            / filename
        ).write_bytes(
            b"novo"
        )

    insights = (
        root
        / "insights_2026.md"
    )
    insights.write_text(
        "insights novos",
        encoding="utf-8",
    )
    return (
        assets,
        insights,
    )


def test_publish_report_bundle_replaces_visual_snapshot(
    tmp_path: Path,
) -> None:
    stage = (
        tmp_path
        / "stage"
    )
    stage.mkdir()
    staged_assets, staged_insights = (
        _create_report_stage(
            stage
        )
    )

    assets = (
        tmp_path
        / "assets"
        / "generated"
    )
    assets.mkdir(
        parents=True,
    )
    (
        assets
        / "antigo.png"
    ).write_bytes(
        b"antigo"
    )

    insights = (
        tmp_path
        / "reports"
        / "insights_2026.md"
    )
    insights.parent.mkdir()
    insights.write_text(
        "insights antigos",
        encoding="utf-8",
    )

    _publish_report_bundle(
        staged_assets,
        staged_insights,
        assets,
        insights,
    )

    assert not (
        assets
        / "antigo.png"
    ).exists()
    assert len(
        list(
            assets.glob(
                "*.png"
            )
        )
    ) == 5
    assert (
        insights.read_text(
            encoding="utf-8"
        )
        == "insights novos"
    )


def test_publish_report_bundle_rejects_incomplete_stage_before_replacement(
    tmp_path: Path,
) -> None:
    staged_assets = (
        tmp_path
        / "stage"
        / "generated"
    )
    staged_assets.mkdir(
        parents=True,
    )
    (
        staged_assets
        / "tendencia_brasil_2026.png"
    ).write_bytes(
        b"novo"
    )
    staged_insights = (
        tmp_path
        / "stage"
        / "insights_2026.md"
    )
    staged_insights.write_text(
        "novo",
        encoding="utf-8",
    )

    assets = (
        tmp_path
        / "assets"
        / "generated"
    )
    assets.mkdir(
        parents=True,
    )
    old = (
        assets
        / "antigo.png"
    )
    old.write_bytes(
        b"antigo"
    )
    insights = (
        tmp_path
        / "reports"
        / "insights_2026.md"
    )
    insights.parent.mkdir()
    insights.write_text(
        "antigo",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Conjunto de gráficos inválido",
    ):
        _publish_report_bundle(
            staged_assets,
            staged_insights,
            assets,
            insights,
        )

    assert old.exists()
    assert (
        insights.read_text(
            encoding="utf-8"
        )
        == "antigo"
    )


def test_publish_report_bundle_install_failure_restores_previous_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = (
        tmp_path
        / "stage"
    )
    stage.mkdir()
    staged_assets, staged_insights = (
        _create_report_stage(
            stage
        )
    )

    assets = (
        tmp_path
        / "assets"
        / "generated"
    )
    assets.mkdir(
        parents=True,
    )
    old_image = (
        assets
        / "antigo.png"
    )
    old_image.write_bytes(
        b"antigo"
    )

    insights = (
        tmp_path
        / "reports"
        / "insights_2026.md"
    )
    insights.parent.mkdir()
    insights.write_text(
        "insights antigos",
        encoding="utf-8",
    )

    original_move = (
        reporting_module.shutil.move
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
            == "insights_2026.md"
            and destination_path
            == insights
        ):
            raise OSError(
                "falha simulada"
            )
        return original_move(
            source,
            destination,
        )

    monkeypatch.setattr(
        reporting_module.shutil,
        "move",
        failing_move,
    )

    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        _publish_report_bundle(
            staged_assets,
            staged_insights,
            assets,
            insights,
        )

    assert old_image.exists()
    assert (
        old_image.read_bytes()
        == b"antigo"
    )
    assert (
        insights.read_text(
            encoding="utf-8"
        )
        == "insights antigos"
    )



def test_publish_report_bundle_rejects_empty_image_before_replacement(
    tmp_path: Path,
) -> None:
    stage = (
        tmp_path
        / "stage"
    )
    stage.mkdir()
    staged_assets, staged_insights = (
        _create_report_stage(
            stage
        )
    )
    (
        staged_assets
        / "ranking_ufs_gasolina.png"
    ).write_bytes(
        b""
    )

    assets = (
        tmp_path
        / "assets"
        / "generated"
    )
    assets.mkdir(
        parents=True,
    )
    old = (
        assets
        / "antigo.png"
    )
    old.write_bytes(
        b"antigo"
    )
    insights = (
        tmp_path
        / "reports"
        / "insights_2026.md"
    )
    insights.parent.mkdir()
    insights.write_text(
        "antigo",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Gráficos vazios",
    ):
        _publish_report_bundle(
            staged_assets,
            staged_insights,
            assets,
            insights,
        )

    assert old.exists()
    assert (
        insights.read_text(
            encoding="utf-8"
        )
        == "antigo"
    )


def test_publish_report_bundle_rejects_empty_insights_before_replacement(
    tmp_path: Path,
) -> None:
    stage = (
        tmp_path
        / "stage"
    )
    stage.mkdir()
    staged_assets, staged_insights = (
        _create_report_stage(
            stage
        )
    )
    staged_insights.write_text(
        "",
        encoding="utf-8",
    )

    assets = (
        tmp_path
        / "assets"
        / "generated"
    )
    assets.mkdir(
        parents=True,
    )
    old = (
        assets
        / "antigo.png"
    )
    old.write_bytes(
        b"antigo"
    )
    insights = (
        tmp_path
        / "reports"
        / "insights_2026.md"
    )
    insights.parent.mkdir()
    insights.write_text(
        "antigo",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Relatório de insights vazio",
    ):
        _publish_report_bundle(
            staged_assets,
            staged_insights,
            assets,
            insights,
        )

    assert old.exists()
    assert (
        insights.read_text(
            encoding="utf-8"
        )
        == "antigo"
    )


def test_state_ranking_chart_rejects_mixed_units(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
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
        }
    )
    output = tmp_path / "ranking.png"

    plot_state_ranking(
        frame,
        output,
    )

    assert output.exists()
    assert output.stat().st_size > 0


def test_single_unit_subset_rejects_mixed_units() -> None:
    from src.reporting import (
        _single_unit_subset,
    )

    frame = pd.DataFrame(
        {
            "produto": [
                "GASOLINA COMUM",
                "GASOLINA COMUM",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/M3",
            ],
        }
    )

    subset, label = _single_unit_subset(
        frame,
        "GASOLINA COMUM",
    )

    assert subset.empty
    assert "múltiplas unidades" in label


def test_select_common_gasoline_ignores_premium() -> None:
    products = pd.Series(
        [
            "GASOLINA PREMIUM",
            "GASOLINA COMUM",
        ]
    )

    assert (
        _select_common_gasoline(
            products
        )
        == "GASOLINA COMUM"
    )


def test_select_common_gasoline_accepts_plain_station_label() -> None:
    products = pd.Series(
        [
            "GASOLINA",
            "ETANOL",
        ]
    )

    assert (
        _select_common_gasoline(
            products
        )
        == "GASOLINA"
    )
