from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import (
    PROCESSED_DIR,
    REPORTS_DIR,
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
) -> list[Path]:
    return sorted(
        path
        for path in directory.glob(
            "*.csv"
        )
        if path.name
        != OUTPUT_NAME
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
        return frame, audit

    frame[
        "nivel_geografico"
    ] = infer_geographic_level(
        frame
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
) -> tuple[
    pd.DataFrame,
    dict[str, object],
]:
    frames: list[pd.DataFrame] = []
    file_audits: list[
        dict[str, object]
    ] = []

    files = _candidate_files(
        directory
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
    if keys:
        combined = (
            combined.drop_duplicates(
                subset=keys,
                keep="last",
            )
        )

    duplicates_removed = (
        rows_before_dedup
        - len(combined)
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
        "linhas_finais": int(
            len(combined)
        ),
        "arquivos": file_audits,
        "status": (
            "passed"
            if invalid_dates == 0
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
            PROCESSED_DIR
        )
    )

    output = (
        PROCESSED_DIR
        / OUTPUT_NAME
    )
    frame.to_csv(
        output,
        index=False,
        encoding="utf-8",
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    AGGREGATE_INGESTION_AUDIT.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
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
