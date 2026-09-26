from pathlib import Path

import pandas as pd

from src.consolidate import (
    build_analytics_table,
    build_analytics_table_with_audit,
    infer_geographic_level,
)
from src.download_history import (
    _clear_history_scope,
    _discover_weekly_history_links,
)
from src.quality import build_quality_report
from src.transform import parse_decimal_series


def test_history_discovery_uses_post_2013_section() -> None:
    html = """
    <h2>Série histórica semanal</h2>
    <a href="old-br.xlsx">Brasil</a>
    <a href="#2013">A partir de 2013</a>
    <a href="new-br.xlsx">Brasil</a>
    <a href="regions.xlsx">Regiões</a>
    <a href="states.xlsx">Estados</a>
    <a href="cities-2026.xlsx">Municípios (2026)</a>
    <h2>Série histórica mensal</h2>
    <a href="monthly.xlsx">Brasil</a>
    """

    links = _discover_weekly_history_links(html)

    assert links["brasil"].endswith(
        "new-br.xlsx"
    )
    assert links["municipios_2026"].endswith(
        "cities-2026.xlsx"
    )


def test_decimal_parser_handles_brazilian_and_dot_decimal() -> None:
    parsed = parse_decimal_series(
        pd.Series(
            ["6,12", "6.12", "1.234,56"]
        )
    )
    assert parsed.tolist() == [
        6.12,
        6.12,
        1234.56,
    ]


def test_geographic_level_prefers_most_granular() -> None:
    frame = pd.DataFrame(
        {
            "regiao": [
                None,
                "NORDESTE",
                "NORDESTE",
                "NORDESTE",
            ],
            "uf": [
                None,
                None,
                "CE",
                "CE",
            ],
            "municipio": [
                None,
                None,
                None,
                "FORTALEZA",
            ],
        }
    )

    assert infer_geographic_level(
        frame
    ).tolist() == [
        "brasil",
        "regiao",
        "estado",
        "municipio",
    ]


def test_consolidation_filters_2026_and_removes_duplicates(
    tmp_path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
                "2026-01-04",
                "2025-12-28",
            ],
            "data_final": [
                "2026-01-10",
                "2026-01-10",
                "2026-01-03",
            ],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "uf": ["CE", "CE", "CE"],
            "produto": [
                "GASOLINA",
                "GASOLINA",
                "GASOLINA",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/L",
                "R$/L",
            ],
            "preco_medio_revenda": [
                6.0,
                6.0,
                5.9,
            ],
        }
    )
    frame.to_csv(
        tmp_path / "sample.csv",
        index=False,
    )

    result = build_analytics_table(tmp_path)

    assert len(result) == 1
    assert result.loc[0, "ano"] == 2026
    assert (
        result.loc[
            0,
            "nivel_geografico",
        ]
        == "municipio"
    )


def _valid_quality_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "produto": ["GASOLINA"],
            "preco_medio_revenda": [6.0],
            "preco_minimo_revenda": [5.8],
            "preco_maximo_revenda": [6.2],
            "nivel_geografico": [
                "brasil",
            ],
            "unidade_medida": ["R$/L"],
        }
    )


def test_quality_report_passes_valid_row() -> None:
    report = build_quality_report(
        _valid_quality_frame()
    )

    assert report["status"] == "passed"


def test_quality_report_blocks_non_positive_prices() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "preco_medio_revenda"] = 0

    report = build_quality_report(frame)

    assert (
        report["non_positive_price_rows"]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_invalid_dates() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "data_inicial"] = "invalida"

    report = build_quality_report(frame)

    assert (
        report["invalid_start_date_rows"]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_inverted_period() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "data_final"] = (
        "2026-01-03"
    )

    report = build_quality_report(frame)

    assert (
        report["end_before_start_rows"]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_outside_2026() -> None:
    frame = _valid_quality_frame()
    frame.loc[0, "data_inicial"] = (
        "2025-12-28"
    )

    report = build_quality_report(frame)

    assert report["outside_2026_rows"] == 1
    assert report["status"] == "failed"



def test_history_cleanup_replaces_only_same_scope(
    tmp_path: Path,
) -> None:
    old_a = (
        tmp_path
        / "historico_semanal_brasil__antigo.xlsx"
    )
    old_b = (
        tmp_path
        / "historico_semanal_brasil__outro.xlsx"
    )
    other = (
        tmp_path
        / "historico_semanal_estados__dados.xlsx"
    )
    manifest = (
        tmp_path
        / "history_manifest.json"
    )

    for path in (
        old_a,
        old_b,
        other,
        manifest,
    ):
        path.write_text(
            "conteudo",
            encoding="utf-8",
        )

    _clear_history_scope(
        tmp_path,
        "brasil",
    )

    assert not old_a.exists()
    assert not old_b.exists()
    assert other.exists()
    assert manifest.exists()



def test_aggregate_ingestion_audit_counts_exclusions_and_dedup(
    tmp_path: Path,
) -> None:
    aggregate = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
                "2026-01-04",
                "2025-12-28",
                "data-invalida",
            ],
            "data_final": [
                "2026-01-10",
                "2026-01-10",
                "2026-01-03",
                "2026-01-10",
            ],
            "uf": ["CE", "CE", "CE", "CE"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "produto": [
                "GASOLINA",
                "GASOLINA",
                "GASOLINA",
                "GASOLINA",
            ],
            "unidade_medida": [
                "R$/L",
                "R$/L",
                "R$/L",
                "R$/L",
            ],
            "preco_medio_revenda": [
                6.0,
                6.0,
                5.9,
                6.1,
            ],
        }
    )
    aggregate.to_csv(
        tmp_path / "agregado.csv",
        index=False,
    )

    pd.DataFrame(
        {
            "coluna_a": [1, 2]
        }
    ).to_csv(
        tmp_path / "nao_agregado.csv",
        index=False,
    )

    frame, audit = (
        build_analytics_table_with_audit(
            tmp_path
        )
    )

    assert len(frame) == 1
    assert audit["arquivos_encontrados"] == 2
    assert audit["arquivos_processados"] == 1
    assert (
        audit[
            "arquivos_ignorados_por_schema"
        ]
        == 1
    )
    assert (
        audit[
            "linhas_lidas_total"
        ]
        == 6
    )
    assert (
        audit[
            "linhas_lidas_arquivos_processados"
        ]
        == 4
    )
    assert (
        audit[
            "datas_iniciais_invalidas"
        ]
        == 1
    )
    assert audit["linhas_fora_2026"] == 1
    assert (
        audit[
            "linhas_elegiveis_antes_deduplicacao"
        ]
        == 2
    )
    assert (
        audit[
            "linhas_removidas_por_duplicidade"
        ]
        == 1
    )
    assert audit["linhas_finais"] == 1
    assert audit["status"] == "review"
