from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

from .atomic_outputs import (
    replace_staged_files,
)
from .config import (
    PROCESSED_DIR,
    REPORTS_DIR,
)
from .provenance import (
    HISTORY_SCOPES,
)
from .transform import (
    history_scope_from_path,
)

OUTPUT_NAME = "precos_semanais_2026.csv"
AGGREGATE_INGESTION_AUDIT = (
    REPORTS_DIR
    / "aggregate_ingestion_audit_2026.json"
)

AGGREGATE_REQUIRED_COLUMNS = {
    "data_inicial",
    "produto",
    "preco_medio_revenda",
}

EXPECTED_LEVEL_BY_HISTORY_SCOPE = {
    "brasil": "brasil",
    "regioes": "regiao",
    "estados": "estado",
    "municipios_2026": "municipio",
}


def infer_geographic_level(
    frame: pd.DataFrame,
) -> pd.Series:
    level = pd.Series(
        "brasil",
        index=frame.index,
        dtype="string",
    )

    if "regiao" in frame.columns:
        mask = (
            frame["regiao"].notna()
            & frame["regiao"]
            .astype(str)
            .str.strip()
            .ne("")
        )
        level.loc[mask] = "regiao"

    for column in (
        "uf",
        "estado",
    ):
        if column in frame.columns:
            mask = (
                frame[column].notna()
                & frame[column]
                .astype(str)
                .str.strip()
                .ne("")
            )
            level.loc[mask] = "estado"

    if "municipio" in frame.columns:
        mask = (
            frame["municipio"].notna()
            & frame["municipio"]
            .astype(str)
            .str.strip()
            .ne("")
        )
        level.loc[mask] = "municipio"

    return level


def _candidate_files(
    directory: Path,
    history_only: bool = False,
) -> list[Path]:
    files = sorted(
        path
        for path in directory.glob(
            "*.csv"
        )
        if path.name
        != OUTPUT_NAME
    )
    if history_only:
        files = [
            path
            for path in files
            if history_scope_from_path(
                path
            )
            is not None
        ]
    return files


def _validate_history_scope_coverage(
    files: list[Path],
) -> None:
    scopes = {
        scope
        for path in files
        if (
            scope
            := history_scope_from_path(
                path
            )
        )
    }
    if scopes != HISTORY_SCOPES:
        missing = sorted(
            HISTORY_SCOPES
            - scopes
        )
        extra = sorted(
            scopes
            - HISTORY_SCOPES
        )
        raise RuntimeError(
            "Cobertura processada histórica "
            f"incompleta. Ausentes={missing}; "
            f"extras={extra}."
        )


def _prepare_aggregate_file(
    path: Path,
) -> tuple[
    pd.DataFrame | None,
    dict[str, object],
]:
    frame = pd.read_csv(
        path,
        low_memory=False,
    )
    missing = sorted(
        AGGREGATE_REQUIRED_COLUMNS
        - set(frame.columns)
    )

    audit: dict[str, object] = {
        "fonte_arquivo": path.name,
        "linhas_origem": int(
            len(frame)
        ),
        "colunas_ausentes": missing,
    }

    if missing:
        audit.update(
            {
                "status": "ignored",
                "datas_iniciais_invalidas": 0,
                "linhas_fora_2026": 0,
                "linhas_elegiveis_2026": 0,
            }
        )
        return None, audit

    frame = frame.copy()
    frame["data_inicial"] = (
        pd.to_datetime(
            frame["data_inicial"],
            errors="coerce",
        )
    )

    if "data_final" in frame.columns:
        frame["data_final"] = (
            pd.to_datetime(
                frame["data_final"],
                errors="coerce",
            )
        )

    valid_start = (
        frame[
            "data_inicial"
        ].notna()
    )
    in_2026 = (
        valid_start
        & frame[
            "data_inicial"
        ].dt.year.eq(2026)
    )

    audit.update(
        {
            "status": "processed",
            "datas_iniciais_invalidas": int(
                (~valid_start).sum()
            ),
            "linhas_fora_2026": int(
                (
                    valid_start
                    & ~frame[
                        "data_inicial"
                    ].dt.year.eq(2026)
                ).sum()
            ),
            "linhas_elegiveis_2026": int(
                in_2026.sum()
            ),
        }
    )

    frame = frame.loc[
        in_2026
    ].copy()
    if frame.empty:
        audit[
            "linhas_nivel_geografico_incompativel"
        ] = 0
        return frame, audit

    frame[
        "nivel_geografico"
    ] = infer_geographic_level(
        frame
    )

    scope = history_scope_from_path(
        path
    )
    expected_level = (
        EXPECTED_LEVEL_BY_HISTORY_SCOPE.get(
            scope
        )
    )
    audit[
        "linhas_nivel_geografico_incompativel"
    ] = (
        int(
            frame[
                "nivel_geografico"
            ]
            .ne(
                expected_level
            )
            .sum()
        )
        if expected_level
        else 0
    )
    frame["ano"] = (
        frame[
            "data_inicial"
        ].dt.year.astype("Int64")
    )
    frame["mes"] = (
        frame[
            "data_inicial"
        ].dt.month.astype("Int64")
    )
    frame["semana_iso"] = (
        frame["data_inicial"]
        .dt.isocalendar()
        .week
        .astype("Int64")
    )
    return frame, audit


def build_analytics_table_with_audit(
    directory: Path = PROCESSED_DIR,
    *,
    history_only: bool = False,
    require_complete_history: bool = False,
) -> tuple[
    pd.DataFrame,
    dict[str, object],
]:
    frames: list[pd.DataFrame] = []
    file_audits: list[
        dict[str, object]
    ] = []

    files = _candidate_files(
        directory,
        history_only=history_only,
    )
    if require_complete_history:
        _validate_history_scope_coverage(
            files
        )
    for path in files:
        frame, file_audit = (
            _prepare_aggregate_file(
                path
            )
        )
        file_audits.append(
            file_audit
        )
        if (
            frame is not None
            and not frame.empty
        ):
            frames.append(frame)

    if require_complete_history:
        incompatible = [
            item[
                "fonte_arquivo"
            ]
            for item in file_audits
            if int(
                item.get(
                    "linhas_nivel_geografico_incompativel",
                    0,
                )
            )
            > 0
        ]
        if incompatible:
            raise RuntimeError(
                "Nível geográfico incompatível "
                "com o escopo histórico em: "
                + ", ".join(
                    incompatible
                )
            )

    if not frames:
        raise RuntimeError(
            "Nenhum CSV agregado de 2026 foi encontrado "
            "em data/processed. Execute download_history "
            "e transform antes da consolidação."
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )
    rows_before_dedup = len(
        combined
    )

    key_candidates = [
        "data_inicial",
        "data_final",
        "nivel_geografico",
        "regiao",
        "uf",
        "estado",
        "municipio",
        "produto",
        "unidade_medida",
    ]
    keys = [
        column
        for column
        in key_candidates
        if column
        in combined.columns
    ]

    semantic_columns = [
        column
        for column in combined.columns
        if column
        not in {
            "fonte_arquivo",
            "fonte_planilha",
        }
    ]
    combined = (
        combined.drop_duplicates(
            subset=semantic_columns,
            keep="first",
        )
    )
    duplicates_removed = (
        rows_before_dedup
        - len(combined)
    )

    conflicting_duplicate_rows = (
        int(
            combined.duplicated(
                subset=keys,
                keep=False,
            ).sum()
        )
        if keys
        else 0
    )

    sort_candidates = [
        "data_inicial",
        "nivel_geografico",
        "regiao",
        "uf",
        "estado",
        "municipio",
        "produto",
    ]
    sort_by = [
        column
        for column
        in sort_candidates
        if column
        in combined.columns
    ]
    if sort_by:
        combined = (
            combined.sort_values(
                sort_by,
                kind="stable",
            )
        )

    invalid_dates = sum(
        int(
            item[
                "datas_iniciais_invalidas"
            ]
        )
        for item in file_audits
    )
    ignored_files = sum(
        item["status"]
        == "ignored"
        for item in file_audits
    )
    processed_without_2026 = sum(
        (
            item["status"]
            == "processed"
            and int(
                item[
                    "linhas_elegiveis_2026"
                ]
            )
            == 0
        )
        for item in file_audits
    )

    audit = {
        "arquivos_encontrados": int(
            len(files)
        ),
        "arquivos_processados": int(
            len(files)
            - ignored_files
        ),
        "arquivos_ignorados_por_schema": int(
            ignored_files
        ),
        "arquivos_processados_sem_linhas_2026": int(
            processed_without_2026
        ),
        "linhas_nivel_geografico_incompativel": int(
            sum(
                int(
                    item.get(
                        "linhas_nivel_geografico_incompativel",
                        0,
                    )
                )
                for item in file_audits
            )
        ),
        "linhas_lidas_total": int(
            sum(
                int(
                    item[
                        "linhas_origem"
                    ]
                )
                for item
                in file_audits
            )
        ),
        "linhas_lidas_arquivos_processados": int(
            sum(
                int(
                    item[
                        "linhas_origem"
                    ]
                )
                for item
                in file_audits
                if item[
                    "status"
                ]
                == "processed"
            )
        ),
        "datas_iniciais_invalidas": int(
            invalid_dates
        ),
        "linhas_fora_2026": int(
            sum(
                int(
                    item[
                        "linhas_fora_2026"
                    ]
                )
                for item
                in file_audits
            )
        ),
        "linhas_elegiveis_antes_deduplicacao": int(
            rows_before_dedup
        ),
        "linhas_removidas_por_duplicidade": int(
            duplicates_removed
        ),
        "linhas_com_duplicidade_divergente": int(
            conflicting_duplicate_rows
        ),
        "linhas_finais": int(
            len(combined)
        ),
        "arquivos": file_audits,
        "status": (
            "passed"
            if (
                invalid_dates == 0
                and ignored_files == 0
                and processed_without_2026
                == 0
                and conflicting_duplicate_rows
                == 0
            )
            else "review"
        ),
    }

    return (
        combined.reset_index(
            drop=True
        ),
        audit,
    )


def build_analytics_table(
    directory: Path = PROCESSED_DIR,
) -> pd.DataFrame:
    frame, _ = (
        build_analytics_table_with_audit(
            directory
        )
    )
    return frame


def main() -> None:
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    frame, audit = (
        build_analytics_table_with_audit(
            PROCESSED_DIR,
            history_only=True,
            require_complete_history=True,
        )
    )

    output = (
        PROCESSED_DIR
        / OUTPUT_NAME
    )

    with tempfile.TemporaryDirectory(
        prefix=".aggregate_bundle_",
        dir=PROCESSED_DIR.parent,
    ) as temporary:
        stage = Path(
            temporary
        )
        staged_output = (
            stage
            / OUTPUT_NAME
        )
        staged_audit = (
            stage
            / AGGREGATE_INGESTION_AUDIT.name
        )

        frame.to_csv(
            staged_output,
            index=False,
            encoding="utf-8",
        )
        staged_audit.write_text(
            json.dumps(
                audit,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        replace_staged_files(
            [
                (
                    staged_output,
                    output,
                ),
                (
                    staged_audit,
                    AGGREGATE_INGESTION_AUDIT,
                ),
            ]
        )

    print(
        "Tabela analítica: "
        f"{output.relative_to(PROCESSED_DIR.parent.parent)}"
    )
    print(
        "Auditoria de ingestão: "
        f"{AGGREGATE_INGESTION_AUDIT.relative_to(PROCESSED_DIR.parent.parent)}"
    )
    print(
        f"Linhas: {len(frame):,}"
    )
    print(
        f"Colunas: {len(frame.columns)}"
    )


if __name__ == "__main__":
    main()
