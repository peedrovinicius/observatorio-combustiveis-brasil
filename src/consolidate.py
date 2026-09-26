from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR

OUTPUT_NAME = "precos_semanais_2026.csv"


def infer_geographic_level(frame: pd.DataFrame) -> pd.Series:
    level = pd.Series("brasil", index=frame.index, dtype="string")

    if "regiao" in frame.columns:
        mask = frame["regiao"].notna() & frame["regiao"].astype(str).str.strip().ne("")
        level.loc[mask] = "regiao"

    for column in ("uf", "estado"):
        if column in frame.columns:
            mask = frame[column].notna() & frame[column].astype(str).str.strip().ne("")
            level.loc[mask] = "estado"

    if "municipio" in frame.columns:
        mask = (
            frame["municipio"].notna()
            & frame["municipio"].astype(str).str.strip().ne("")
        )
        level.loc[mask] = "municipio"

    return level


def _candidate_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.glob("*.csv")
        if path.name != OUTPUT_NAME
    )


def build_analytics_table(directory: Path = PROCESSED_DIR) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for path in _candidate_files(directory):
        frame = pd.read_csv(path, low_memory=False)

        if "produto" not in frame.columns or "preco_medio_revenda" not in frame.columns:
            continue
        if "data_inicial" not in frame.columns:
            continue

        frame["data_inicial"] = pd.to_datetime(frame["data_inicial"], errors="coerce")
        if "data_final" in frame.columns:
            frame["data_final"] = pd.to_datetime(frame["data_final"], errors="coerce")

        frame = frame.loc[frame["data_inicial"].dt.year.eq(2026)].copy()
        if frame.empty:
            continue

        frame["nivel_geografico"] = infer_geographic_level(frame)
        frame["ano"] = frame["data_inicial"].dt.year.astype("Int64")
        frame["mes"] = frame["data_inicial"].dt.month.astype("Int64")
        frame["semana_iso"] = (
            frame["data_inicial"].dt.isocalendar().week.astype("Int64")
        )
        frames.append(frame)

    if not frames:
        raise RuntimeError(
            "Nenhum CSV agregado de 2026 foi encontrado em data/processed. "
            "Execute download_history e transform antes da consolidação."
        )

    combined = pd.concat(frames, ignore_index=True, sort=False)

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
    keys = [column for column in key_candidates if column in combined.columns]
    if keys:
        combined = combined.drop_duplicates(subset=keys, keep="last")

    sort_candidates = [
        "data_inicial",
        "nivel_geografico",
        "regiao",
        "uf",
        "estado",
        "municipio",
        "produto",
    ]
    sort_by = [column for column in sort_candidates if column in combined.columns]
    if sort_by:
        combined = combined.sort_values(sort_by, kind="stable")

    return combined.reset_index(drop=True)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame = build_analytics_table(PROCESSED_DIR)
    output = PROCESSED_DIR / OUTPUT_NAME
    frame.to_csv(output, index=False, encoding="utf-8")

    print(f"Tabela analítica: {output.relative_to(PROCESSED_DIR.parent.parent)}")
    print(f"Linhas: {len(frame):,}")
    print(f"Colunas: {len(frame.columns)}")


if __name__ == "__main__":
    main()
