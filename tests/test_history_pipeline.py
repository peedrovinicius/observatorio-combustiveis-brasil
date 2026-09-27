import hashlib
import json
import io
from pathlib import Path

import pandas as pd
import pytest

from src.consolidate import (
    _candidate_files,
    _validate_history_scope_coverage,
    build_analytics_table,
    build_analytics_table_with_audit,
    infer_geographic_level,
)
from src.download_history import (
    _clear_history_scope,
    _discover_weekly_history_links,
    _replace_history_batch,
)
from src.quality import build_quality_report
import src.transform as transform_module
from src.transform import (
    clear_processed_history_scope,
    history_scope_from_path,
    parse_decimal_series,
    transform_workbook,
    transform_workbooks,
)


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



def test_history_discovery_rejects_duplicate_scope() -> None:
    html = """
    <h2>Série histórica semanal</h2>
    <a href="#2013">A partir de 2013</a>
    <a href="br-a.xlsx">Brasil</a>
    <a href="br-b.xlsx">Brasil</a>
    <a href="regions.xlsx">Regiões</a>
    <a href="states.xlsx">Estados</a>
    <a href="cities.xlsx">Municípios (2026)</a>
    """

    with pytest.raises(
        RuntimeError,
        match="escopo histórico brasil",
    ):
        _discover_weekly_history_links(
            html
        )


def test_decimal_parser_handles_brazilian_and_dot_decimal() -> None:
    parsed = parse_decimal_series(
        pd.Series(
            [
                "6,12",
                "6.12",
                "1.234,56",
                "1,234.56",
            ]
        )
    )
    assert parsed.tolist() == [
        6.12,
        6.12,
        1234.56,
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


def test_quality_report_blocks_region_without_identifier() -> None:
    frame = _valid_quality_frame()
    frame.loc[
        0,
        "nivel_geografico",
    ] = "regiao"

    report = build_quality_report(
        frame
    )

    assert (
        report[
            "missing_region_identifier_rows"
        ]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_accepts_state_with_uf_only() -> None:
    frame = _valid_quality_frame()
    frame.loc[
        0,
        "nivel_geografico",
    ] = "estado"
    frame["uf"] = ["CE"]

    report = build_quality_report(
        frame
    )

    assert (
        report[
            "missing_state_identifier_rows"
        ]
        == 0
    )
    assert report["status"] == "passed"


def test_quality_report_accepts_state_with_name_only() -> None:
    frame = _valid_quality_frame()
    frame.loc[
        0,
        "nivel_geografico",
    ] = "estado"
    frame["estado"] = [
        "CEARA"
    ]

    report = build_quality_report(
        frame
    )

    assert (
        report[
            "missing_state_identifier_rows"
        ]
        == 0
    )
    assert report["status"] == "passed"


def test_quality_report_blocks_state_without_identifier() -> None:
    frame = _valid_quality_frame()
    frame.loc[
        0,
        "nivel_geografico",
    ] = "estado"

    report = build_quality_report(
        frame
    )

    assert (
        report[
            "missing_state_identifier_rows"
        ]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_municipality_without_name() -> None:
    frame = _valid_quality_frame()
    frame.loc[
        0,
        "nivel_geografico",
    ] = "municipio"
    frame["uf"] = ["CE"]

    report = build_quality_report(
        frame
    )

    assert (
        report[
            "missing_municipality_identifier_rows"
        ]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_blocks_municipality_without_state_context() -> None:
    frame = _valid_quality_frame()
    frame.loc[
        0,
        "nivel_geografico",
    ] = "municipio"
    frame["municipio"] = [
        "FORTALEZA"
    ]

    report = build_quality_report(
        frame
    )

    assert (
        report[
            "missing_municipality_state_identifier_rows"
        ]
        == 1
    )
    assert report["status"] == "failed"


def test_quality_report_accepts_municipality_with_uf() -> None:
    frame = _valid_quality_frame()
    frame.loc[
        0,
        "nivel_geografico",
    ] = "municipio"
    frame["municipio"] = [
        "FORTALEZA"
    ]
    frame["uf"] = ["CE"]

    report = build_quality_report(
        frame
    )

    assert (
        report[
            "missing_municipality_identifier_rows"
        ]
        == 0
    )
    assert (
        report[
            "missing_municipality_state_identifier_rows"
        ]
        == 0
    )
    assert report["status"] == "passed"




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



def test_history_scope_keeps_underscored_scope_name() -> None:
    path = Path(
        "historico_semanal_municipios_2026__dados.xlsx"
    )

    assert (
        history_scope_from_path(
            path
        )
        == "municipios_2026"
    )


def test_processed_history_cleanup_is_scope_specific(
    tmp_path: Path,
) -> None:
    brazil_old = (
        tmp_path
        / "historico_semanal_brasil__antigo__dados.csv"
    )
    brazil_new = (
        tmp_path
        / "historico_semanal_brasil__novo__dados.csv"
    )
    states = (
        tmp_path
        / "historico_semanal_estados__dados__dados.csv"
    )
    consolidated = (
        tmp_path
        / "precos_semanais_2026.csv"
    )

    for path in (
        brazil_old,
        brazil_new,
        states,
        consolidated,
    ):
        path.write_text(
            "conteudo",
            encoding="utf-8",
        )

    clear_processed_history_scope(
        tmp_path,
        "brasil",
    )

    assert not brazil_old.exists()
    assert not brazil_new.exists()
    assert states.exists()
    assert consolidated.exists()


def _write_valid_history_workbook(
    path: Path,
) -> None:
    frame = pd.DataFrame(
        {
            "Data Inicial": [
                "04/01/2026",
            ],
            "Data Final": [
                "10/01/2026",
            ],
            "Produto": [
                "GASOLINA COMUM",
            ],
            "Preço Médio Revenda": [
                "6,00",
            ],
        }
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


def test_transform_replaces_stale_processed_scope_after_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed = (
        tmp_path
        / "processed"
    )
    processed.mkdir()

    old = (
        processed
        / "historico_semanal_brasil__arquivo_antigo__dados.csv"
    )
    other_scope = (
        processed
        / "historico_semanal_estados__arquivo__dados.csv"
    )
    old.write_text(
        "antigo",
        encoding="utf-8",
    )
    other_scope.write_text(
        "preservar",
        encoding="utf-8",
    )

    workbook = (
        tmp_path
        / "historico_semanal_brasil__arquivo_novo.xlsx"
    )
    _write_valid_history_workbook(
        workbook
    )

    monkeypatch.setattr(
        transform_module,
        "PROCESSED_DIR",
        processed,
    )

    outputs = transform_workbook(
        workbook
    )

    assert not old.exists()
    assert other_scope.exists()
    assert len(outputs) == 1
    assert outputs[0].exists()
    assert (
        outputs[0].name
        == "historico_semanal_brasil__arquivo_novo__dados.csv"
    )


def test_transform_keeps_old_scope_when_new_workbook_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed = (
        tmp_path
        / "processed"
    )
    processed.mkdir()

    old = (
        processed
        / "historico_semanal_brasil__arquivo_antigo__dados.csv"
    )
    old.write_text(
        "antigo",
        encoding="utf-8",
    )

    workbook = (
        tmp_path
        / "historico_semanal_brasil__arquivo_invalido.xlsx"
    )
    with pd.ExcelWriter(
        workbook,
        engine="openpyxl",
    ) as writer:
        pd.DataFrame(
            {
                "coluna_sem_schema": [
                    "x",
                ]
            }
        ).to_excel(
            writer,
            index=False,
            sheet_name="Invalida",
        )

    monkeypatch.setattr(
        transform_module,
        "PROCESSED_DIR",
        processed,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Nenhuma tabela reconhecida"
        ),
    ):
        transform_workbook(
            workbook
        )

    assert old.exists()



def _xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    frame = pd.DataFrame(
        {
            "Data Inicial": [
                "04/01/2026",
            ],
            "Produto": [
                "GASOLINA COMUM",
            ],
            "Preço Médio Revenda": [
                6.0,
            ],
        }
    )
    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:
        frame.to_excel(
            writer,
            index=False,
            sheet_name="Dados",
        )
    return buffer.getvalue()


def test_history_batch_invalid_file_preserves_previous_snapshot(
    tmp_path: Path,
) -> None:
    old_brazil = (
        tmp_path
        / "historico_semanal_brasil__antigo.xlsx"
    )
    old_states = (
        tmp_path
        / "historico_semanal_estados__antigo.xlsx"
    )
    manifest = (
        tmp_path
        / "history_manifest.json"
    )

    old_brazil.write_bytes(
        b"brasil-antigo"
    )
    old_states.write_bytes(
        b"estados-antigo"
    )
    manifest.write_text(
        '{"versao":"antiga"}',
        encoding="utf-8",
    )

    with pytest.raises(
        Exception,
    ):
        _replace_history_batch(
            tmp_path,
            [
                (
                    "brasil",
                    "historico_semanal_brasil__novo.xlsx",
                    _xlsx_bytes(),
                ),
                (
                    "estados",
                    "historico_semanal_estados__novo.xlsx",
                    b"<html>erro</html>",
                ),
            ],
            '{"versao":"nova"}',
        )

    assert (
        old_brazil.read_bytes()
        == b"brasil-antigo"
    )
    assert (
        old_states.read_bytes()
        == b"estados-antigo"
    )
    assert (
        manifest.read_text(
            encoding="utf-8"
        )
        == '{"versao":"antiga"}'
    )
    assert not (
        tmp_path
        / "historico_semanal_brasil__novo.xlsx"
    ).exists()


def test_history_batch_replaces_all_scopes_and_manifest_together(
    tmp_path: Path,
) -> None:
    old_brazil = (
        tmp_path
        / "historico_semanal_brasil__antigo.xlsx"
    )
    old_states = (
        tmp_path
        / "historico_semanal_estados__antigo.xlsx"
    )
    unrelated = (
        tmp_path
        / "arquivo_nao_historico.txt"
    )
    manifest = (
        tmp_path
        / "history_manifest.json"
    )

    old_brazil.write_bytes(
        b"brasil-antigo"
    )
    old_states.write_bytes(
        b"estados-antigo"
    )
    unrelated.write_text(
        "preservar",
        encoding="utf-8",
    )
    manifest.write_text(
        '{"versao":"antiga"}',
        encoding="utf-8",
    )

    content = _xlsx_bytes()
    destinations = (
        _replace_history_batch(
            tmp_path,
            [
                (
                    "brasil",
                    "historico_semanal_brasil__novo.xlsx",
                    content,
                ),
                (
                    "estados",
                    "historico_semanal_estados__novo.xlsx",
                    content,
                ),
            ],
            '{"versao":"nova"}',
        )
    )

    assert not old_brazil.exists()
    assert not old_states.exists()
    assert unrelated.exists()
    assert len(destinations) == 2
    assert all(
        path.exists()
        for path in destinations
    )
    assert (
        manifest.read_text(
            encoding="utf-8"
        )
        == '{"versao":"nova"}'
    )


def test_history_batch_install_failure_restores_all_scopes_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.download_history as history

    old_brazil = (
        tmp_path
        / "historico_semanal_brasil__antigo.xlsx"
    )
    old_states = (
        tmp_path
        / "historico_semanal_estados__antigo.xlsx"
    )
    manifest = (
        tmp_path
        / "history_manifest.json"
    )

    old_brazil.write_bytes(
        b"brasil-antigo"
    )
    old_states.write_bytes(
        b"estados-antigo"
    )
    manifest.write_text(
        '{"versao":"antiga"}',
        encoding="utf-8",
    )

    original_move = (
        history.shutil.move
    )
    failed = False

    def failing_move(
        source: str,
        destination: str,
    ):
        nonlocal failed
        if failed:
            raise AssertionError(
                "rollback não deve reutilizar shutil.move"
            )

        source_path = Path(
            source
        )
        destination_path = Path(
            destination
        )
        if (
            source_path.name
            == "historico_semanal_estados__novo.xlsx"
            and destination_path.parent
            == tmp_path
        ):
            failed = True
            raise OSError(
                "falha simulada"
            )
        return original_move(
            source,
            destination,
        )

    monkeypatch.setattr(
        history.shutil,
        "move",
        failing_move,
    )

    content = _xlsx_bytes()
    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        _replace_history_batch(
            tmp_path,
            [
                (
                    "brasil",
                    "historico_semanal_brasil__novo.xlsx",
                    content,
                ),
                (
                    "estados",
                    "historico_semanal_estados__novo.xlsx",
                    content,
                ),
            ],
            '{"versao":"nova"}',
        )

    assert (
        old_brazil.read_bytes()
        == b"brasil-antigo"
    )
    assert (
        old_states.read_bytes()
        == b"estados-antigo"
    )
    assert (
        manifest.read_text(
            encoding="utf-8"
        )
        == '{"versao":"antiga"}'
    )
    assert not (
        tmp_path
        / "historico_semanal_brasil__novo.xlsx"
    ).exists()
    assert not (
        tmp_path
        / "historico_semanal_estados__novo.xlsx"
    ).exists()


def test_history_batch_rejects_duplicate_scopes(
    tmp_path: Path,
) -> None:
    content = _xlsx_bytes()

    with pytest.raises(
        ValueError,
        match="escopos duplicados",
    ):
        _replace_history_batch(
            tmp_path,
            [
                (
                    "brasil",
                    "historico_semanal_brasil__a.xlsx",
                    content,
                ),
                (
                    "brasil",
                    "historico_semanal_brasil__b.xlsx",
                    content,
                ),
            ],
            "{}",
        )




def test_history_batch_rejects_versioned_manifest_hash_mismatch(
    tmp_path: Path,
) -> None:
    content = _xlsx_bytes()
    filename = (
        "historico_semanal_brasil__novo.xlsx"
    )
    manifest = json.dumps(
        {
            "manifest_version": 1,
            "files": [
                {
                    "scope": "brasil",
                    "filename": filename,
                    "detected_format": "xlsx",
                    "bytes": len(
                        content
                    ),
                    "sha256": "0" * 64,
                }
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="SHA-256 do manifesto histórico",
    ):
        _replace_history_batch(
            tmp_path,
            [
                (
                    "brasil",
                    filename,
                    content,
                )
            ],
            manifest,
        )

    assert not (
        tmp_path
        / filename
    ).exists()


def test_history_batch_rejects_invalid_manifest_before_replacement(
    tmp_path: Path,
) -> None:
    old = (
        tmp_path
        / "historico_semanal_brasil__antigo.xlsx"
    )
    old.write_bytes(
        b"versao-anterior"
    )

    with pytest.raises(
        ValueError,
        match="JSON válido",
    ):
        _replace_history_batch(
            tmp_path,
            [
                (
                    "brasil",
                    "historico_semanal_brasil__novo.xlsx",
                    _xlsx_bytes(),
                )
            ],
            "{invalido",
        )

    assert (
        old.read_bytes()
        == b"versao-anterior"
    )


def test_history_batch_rejects_filename_outside_scope(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="incompatível com o escopo",
    ):
        _replace_history_batch(
            tmp_path,
            [
                (
                    "brasil",
                    "../historico_semanal_brasil__novo.xlsx",
                    _xlsx_bytes(),
                )
            ],
            "{}",
        )



def test_transform_batch_invalid_workbook_preserves_all_processed_scopes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed = (
        tmp_path
        / "processed"
    )
    processed.mkdir()

    old_brazil = (
        processed
        / "historico_semanal_brasil__antigo__dados.csv"
    )
    old_states = (
        processed
        / "historico_semanal_estados__antigo__dados.csv"
    )
    old_brazil.write_text(
        "brasil-antigo",
        encoding="utf-8",
    )
    old_states.write_text(
        "estados-antigo",
        encoding="utf-8",
    )

    brazil = (
        tmp_path
        / "historico_semanal_brasil__novo.xlsx"
    )
    states = (
        tmp_path
        / "historico_semanal_estados__invalido.xlsx"
    )
    _write_valid_history_workbook(
        brazil
    )
    with pd.ExcelWriter(
        states,
        engine="openpyxl",
    ) as writer:
        pd.DataFrame(
            {
                "sem_schema": [
                    "x",
                ]
            }
        ).to_excel(
            writer,
            index=False,
            sheet_name="Invalida",
        )

    monkeypatch.setattr(
        transform_module,
        "PROCESSED_DIR",
        processed,
    )

    with pytest.raises(
        RuntimeError,
        match="Nenhuma tabela reconhecida",
    ):
        transform_workbooks(
            [
                brazil,
                states,
            ]
        )

    assert (
        old_brazil.read_text(
            encoding="utf-8"
        )
        == "brasil-antigo"
    )
    assert (
        old_states.read_text(
            encoding="utf-8"
        )
        == "estados-antigo"
    )


def test_transform_batch_replaces_multiple_scopes_together(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed = (
        tmp_path
        / "processed"
    )
    processed.mkdir()

    old_brazil = (
        processed
        / "historico_semanal_brasil__antigo__dados.csv"
    )
    old_states = (
        processed
        / "historico_semanal_estados__antigo__dados.csv"
    )
    derived = (
        processed
        / "precos_semanais_2026.csv"
    )
    old_brazil.write_text(
        "brasil-antigo",
        encoding="utf-8",
    )
    old_states.write_text(
        "estados-antigo",
        encoding="utf-8",
    )
    derived.write_text(
        "preservar",
        encoding="utf-8",
    )

    brazil = (
        tmp_path
        / "historico_semanal_brasil__novo.xlsx"
    )
    states = (
        tmp_path
        / "historico_semanal_estados__novo.xlsx"
    )
    _write_valid_history_workbook(
        brazil
    )
    _write_valid_history_workbook(
        states
    )

    monkeypatch.setattr(
        transform_module,
        "PROCESSED_DIR",
        processed,
    )

    outputs = transform_workbooks(
        [
            brazil,
            states,
        ]
    )

    assert len(outputs) == 2
    assert all(
        path.exists()
        for path in outputs
    )
    assert not old_brazil.exists()
    assert not old_states.exists()
    assert derived.exists()


def test_transform_batch_install_failure_restores_all_processed_scopes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed = (
        tmp_path
        / "processed"
    )
    processed.mkdir()

    old_brazil = (
        processed
        / "historico_semanal_brasil__antigo__dados.csv"
    )
    old_states = (
        processed
        / "historico_semanal_estados__antigo__dados.csv"
    )
    old_brazil.write_text(
        "brasil-antigo",
        encoding="utf-8",
    )
    old_states.write_text(
        "estados-antigo",
        encoding="utf-8",
    )

    brazil = (
        tmp_path
        / "historico_semanal_brasil__novo.xlsx"
    )
    states = (
        tmp_path
        / "historico_semanal_estados__novo.xlsx"
    )
    _write_valid_history_workbook(
        brazil
    )
    _write_valid_history_workbook(
        states
    )

    monkeypatch.setattr(
        transform_module,
        "PROCESSED_DIR",
        processed,
    )

    original_move = (
        transform_module.shutil.move
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
            "historico_semanal_estados__novo__dados.csv"
            == source_path.name
            and destination_path.parent
            == processed
        ):
            raise OSError(
                "falha simulada"
            )
        return original_move(
            source,
            destination,
        )

    monkeypatch.setattr(
        transform_module.shutil,
        "move",
        failing_move,
    )

    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        transform_workbooks(
            [
                brazil,
                states,
            ]
        )

    assert (
        old_brazil.read_text(
            encoding="utf-8"
        )
        == "brasil-antigo"
    )
    assert (
        old_states.read_text(
            encoding="utf-8"
        )
        == "estados-antigo"
    )
    assert not (
        processed
        / "historico_semanal_brasil__novo__dados.csv"
    ).exists()
    assert not (
        processed
        / "historico_semanal_estados__novo__dados.csv"
    ).exists()


def test_transform_rejects_duplicate_normalized_sheet_names(
    tmp_path: Path,
) -> None:
    workbook = (
        tmp_path
        / "historico_semanal_brasil__duplicado.xlsx"
    )
    frame = pd.DataFrame(
        {
            "Data Inicial": [
                "04/01/2026",
            ],
            "Produto": [
                "GASOLINA COMUM",
            ],
            "Preço Médio Revenda": [
                6.0,
            ],
        }
    )
    with pd.ExcelWriter(
        workbook,
        engine="openpyxl",
    ) as writer:
        frame.to_excel(
            writer,
            index=False,
            sheet_name="Dados 1",
        )
        frame.to_excel(
            writer,
            index=False,
            sheet_name="Dados-1",
        )

    with pytest.raises(
        ValueError,
        match="nomes de CSV duplicados",
    ):
        transform_workbook(
            workbook
        )



def test_strict_aggregate_candidates_ignore_unrelated_csv(
    tmp_path: Path,
) -> None:
    history = (
        tmp_path
        / "historico_semanal_brasil__dados__dados.csv"
    )
    unrelated = (
        tmp_path
        / "manual.csv"
    )
    history.write_text(
        "x",
        encoding="utf-8",
    )
    unrelated.write_text(
        "x",
        encoding="utf-8",
    )

    assert _candidate_files(
        tmp_path,
        history_only=True,
    ) == [
        history
    ]


def test_history_scope_coverage_requires_all_four_scopes(
    tmp_path: Path,
) -> None:
    files = []
    for scope in (
        "brasil",
        "regioes",
        "estados",
    ):
        path = (
            tmp_path
            / (
                f"historico_semanal_{scope}"
                "__dados__dados.csv"
            )
        )
        path.write_text(
            "x",
            encoding="utf-8",
        )
        files.append(
            path
        )

    with pytest.raises(
        RuntimeError,
        match="Cobertura processada histórica incompleta",
    ):
        _validate_history_scope_coverage(
            files
        )


def test_consolidation_preserves_conflicting_duplicate_rows(
    tmp_path: Path,
) -> None:
    first = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
            ],
            "data_final": [
                "2026-01-10",
            ],
            "municipio": [
                "FORTALEZA",
            ],
            "uf": ["CE"],
            "produto": [
                "GASOLINA",
            ],
            "unidade_medida": [
                "R$/L",
            ],
            "preco_medio_revenda": [
                6.0,
            ],
        }
    )
    second = first.copy()
    second.loc[
        0,
        "preco_medio_revenda",
    ] = 6.2

    first.to_csv(
        tmp_path / "a.csv",
        index=False,
    )
    second.to_csv(
        tmp_path / "b.csv",
        index=False,
    )

    frame, audit = (
        build_analytics_table_with_audit(
            tmp_path
        )
    )

    assert len(frame) == 2
    assert (
        audit[
            "linhas_removidas_por_duplicidade"
        ]
        == 0
    )
    assert (
        audit[
            "linhas_com_duplicidade_divergente"
        ]
        == 2
    )
    assert audit["status"] == "review"
