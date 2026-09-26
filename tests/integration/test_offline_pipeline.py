from pathlib import Path

import pandas as pd

import src.transform as transform_module
from src.analytics import (
    build_validated_analytics_exports,
)
from src.build_model import (
    build_validated_star_schema,
)
from src.consolidate import build_analytics_table
from src.quality import build_quality_report
from src.reporting import (
    build_insights_markdown,
    plot_ethanol_gasoline,
    plot_monthly_trend,
    plot_state_ranking,
    plot_station_brand_median,
    plot_station_municipality_dispersion,
)
from src.station_analytics import (
    build_validated_station_analytics_exports,
)
from src.station_data import (
    build_station_star_schema,
    consolidate_station_data_with_audit,
)
from src.station_quality import (
    build_station_quality_report,
)
from src.transform import transform_workbook


def _write_aggregate_workbook(
    path: Path,
) -> None:
    frame = pd.DataFrame(
        [
            [
                "04/01/2026",
                "10/01/2026",
                "",
                "",
                "",
                "",
                "GASOLINA COMUM",
                100,
                "R$/L",
                "6,00",
                "5,80",
                "6,20",
                "0,10",
                "1,67",
            ],
            [
                "11/01/2026",
                "17/01/2026",
                "",
                "",
                "",
                "",
                "GASOLINA COMUM",
                100,
                "R$/L",
                "6,12",
                "5,90",
                "6,30",
                "0,11",
                "1,80",
            ],
            [
                "11/01/2026",
                "17/01/2026",
                "NORDESTE",
                "CEARA",
                "CE",
                "",
                "GASOLINA COMUM",
                20,
                "R$/L",
                "6,30",
                "6,00",
                "6,50",
                "0,12",
                "1,90",
            ],
            [
                "11/01/2026",
                "17/01/2026",
                "SUDESTE",
                "SAO PAULO",
                "SP",
                "",
                "GASOLINA COMUM",
                20,
                "R$/L",
                "6,10",
                "5,90",
                "6,30",
                "0,10",
                "1,64",
            ],
            [
                "11/01/2026",
                "17/01/2026",
                "NORDESTE",
                "CEARA",
                "CE",
                "FORTALEZA",
                "GASOLINA COMUM",
                10,
                "R$/L",
                "6,25",
                "6,00",
                "6,40",
                "0,10",
                "1,60",
            ],
            [
                "11/01/2026",
                "17/01/2026",
                "NORDESTE",
                "CEARA",
                "CE",
                "FORTALEZA",
                "ETANOL HIDRATADO",
                10,
                "R$/L",
                "4,50",
                "4,30",
                "4,70",
                "0,09",
                "2,00",
            ],
        ],
        columns=[
            "Data Inicial",
            "Data Final",
            "Região",
            "Estado",
            "UF",
            "Município",
            "Produto",
            "Número de Postos Pesquisados",
            "Unidade de Medida",
            "Preço Médio Revenda",
            "Preço Mínimo Revenda",
            "Preço Máximo Revenda",
            "Desvio Padrão Revenda",
            "Coef de Variação Revenda",
        ],
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:
        frame.to_excel(
            writer,
            index=False,
            sheet_name="Dados",
        )


def _station_row(
    cnpj: str,
    revenda: str,
    municipio: str,
    price: str,
    brand: str,
) -> list[str]:
    return [
        "NE",
        "CE",
        municipio,
        revenda,
        cnpj,
        "RUA TESTE",
        cnpj[-2:],
        "",
        "CENTRO",
        "60000-000",
        "GASOLINA",
        "17/01/2026",
        price,
        "",
        "R$ / litro",
        brand,
    ]


def _write_station_csv(
    path: Path,
) -> None:
    rows = [
        _station_row(
            "00.000.000/0001-00",
            "POSTO A",
            "FORTALEZA",
            "6,10",
            "BRANCA",
        ),
        _station_row(
            "00.000.000/0002-00",
            "POSTO B",
            "FORTALEZA",
            "6,20",
            "BRANCA",
        ),
        _station_row(
            "00.000.000/0003-00",
            "POSTO C",
            "FORTALEZA",
            "6,30",
            "BRANCA",
        ),
        _station_row(
            "00.000.000/0004-00",
            "POSTO D",
            "FORTALEZA",
            "6,40",
            "BRANCA",
        ),
        _station_row(
            "00.000.000/0005-00",
            "POSTO E",
            "FORTALEZA",
            "6,50",
            "BRANCA",
        ),
        _station_row(
            "00.000.000/0006-00",
            "POSTO F",
            "CAUCAIA",
            "6,00",
            "IPIRANGA",
        ),
        _station_row(
            "00.000.000/0007-00",
            "POSTO G",
            "CAUCAIA",
            "6,05",
            "IPIRANGA",
        ),
        _station_row(
            "00.000.000/0008-00",
            "POSTO H",
            "CAUCAIA",
            "6,10",
            "IPIRANGA",
        ),
    ]

    columns = [
        "Regiao - Sigla",
        "Estado - Sigla",
        "Municipio",
        "Revenda",
        "CNPJ da Revenda",
        "Nome da Rua",
        "Numero Rua",
        "Complemento",
        "Bairro",
        "Cep",
        "Produto",
        "Data da Coleta",
        "Valor de Venda",
        "Valor de Compra",
        "Unidade de Medida",
        "Bandeira",
    ]

    pd.DataFrame(
        rows,
        columns=columns,
    ).to_csv(
        path,
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )


def test_offline_pipeline_reaches_models_analytics_and_charts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    aggregate_dir = (
        tmp_path
        / "processed"
    )
    aggregate_dir.mkdir()

    workbook = (
        tmp_path
        / "historico.xlsx"
    )
    _write_aggregate_workbook(
        workbook
    )

    monkeypatch.setattr(
        transform_module,
        "PROCESSED_DIR",
        aggregate_dir,
    )

    transformed = (
        transform_workbook(
            workbook
        )
    )
    assert len(transformed) == 1

    aggregate = (
        build_analytics_table(
            aggregate_dir
        )
    )
    aggregate_quality = (
        build_quality_report(
            aggregate
        )
    )
    assert (
        aggregate_quality[
            "status"
        ]
        == "passed"
    )

    aggregate_model = (
        build_validated_star_schema(
            aggregate
        )
    )
    assert (
        len(
            aggregate_model[
                "fato_precos_semanais"
            ]
        )
        == len(aggregate)
    )

    aggregate_analytics = (
        build_validated_analytics_exports(
            aggregate
        )
    )
    assert not (
        aggregate_analytics[
            "kpis_brasil_2026"
        ].empty
    )
    assert not (
        aggregate_analytics[
            "ranking_ufs_ultima_semana"
        ].empty
    )
    assert not (
        aggregate_analytics[
            "etanol_gasolina_ultima_semana"
        ].empty
    )

    station_dir = (
        tmp_path
        / "station"
    )
    station_dir.mkdir()
    _write_station_csv(
        station_dir
        / "postos.csv"
    )

    station_frame, audit = (
        consolidate_station_data_with_audit(
            station_dir
        )
    )
    assert audit["status"] == "passed"
    assert (
        audit["linhas_finais"]
        == 8
    )

    station_quality = (
        build_station_quality_report(
            station_frame
        )
    )
    assert (
        station_quality[
            "status"
        ]
        == "passed"
    )

    station_model = (
        build_station_star_schema(
            station_frame
        )
    )
    assert (
        len(
            station_model[
                "fato_precos_postos"
            ]
        )
        == 8
    )

    station_analytics = (
        build_validated_station_analytics_exports(
            station_frame
        )
    )
    distribution = (
        station_analytics[
            "distribuicao_municipios_ultima_coleta"
        ]
    )
    brands = (
        station_analytics[
            "bandeiras_ultima_coleta"
        ]
    )
    assert not distribution.empty
    assert not brands.empty

    chart_dir = (
        tmp_path
        / "charts"
    )
    chart_dir.mkdir()

    plot_monthly_trend(
        aggregate_analytics[
            "tendencia_mensal_brasil_2026"
        ],
        chart_dir
        / "trend.png",
    )
    plot_state_ranking(
        aggregate_analytics[
            "ranking_ufs_ultima_semana"
        ],
        chart_dir
        / "states.png",
    )
    plot_ethanol_gasoline(
        aggregate_analytics[
            "etanol_gasolina_ultima_semana"
        ],
        chart_dir
        / "ratio.png",
    )
    plot_station_municipality_dispersion(
        distribution,
        chart_dir
        / "dispersion.png",
    )
    plot_station_brand_median(
        brands,
        chart_dir
        / "brands.png",
    )

    for filename in (
        "trend.png",
        "states.png",
        "ratio.png",
        "dispersion.png",
        "brands.png",
    ):
        output = (
            chart_dir
            / filename
        )
        assert output.exists()
        assert (
            output.stat().st_size
            > 0
        )

    insights = (
        build_insights_markdown(
            aggregate_analytics[
                "kpis_brasil_2026"
            ],
            aggregate_analytics[
                "ranking_ufs_ultima_semana"
            ],
            aggregate_quality,
            station_quality,
        )
    )
    assert (
        "GASOLINA COMUM"
        in insights
    )
    assert (
        "Série agregada: **passed**"
        in insights
    )
    assert (
        "Dados por posto: **passed**"
        in insights
    )
