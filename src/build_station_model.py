from __future__ import annotations

import pandas as pd

from .config import PROCESSED_DIR
from .station_data import (
    STATION_MODEL_DIR,
    STATION_OUTPUT,
    build_station_star_schema,
)
from .station_quality import (
    build_station_quality_report,
)


def build_validated_station_model(
    frame: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    report = (
        build_station_quality_report(
            frame
        )
    )
    if report["status"] != "passed":
        raise ValueError(
            "A base por posto falhou na validação "
            "de qualidade e não pode ser modelada."
        )

    return build_station_star_schema(
        frame
    )


def main() -> None:
    if not STATION_OUTPUT.exists():
        raise SystemExit(
            "Base por posto não encontrada. "
            "Execute python -m src.station_data."
        )

    frame = pd.read_csv(
        STATION_OUTPUT,
        low_memory=False,
    )

    try:
        tables = (
            build_validated_station_model(
                frame
            )
        )
    except ValueError as exc:
        raise SystemExit(
            str(exc)
        ) from exc

    STATION_MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, table in tables.items():
        output = (
            STATION_MODEL_DIR
            / f"{name}.csv"
        )
        table.to_csv(
            output,
            index=False,
            encoding="utf-8",
        )
        print(
            f"{name}: "
            f"{len(table):,} linhas -> "
            f"{output.relative_to(PROCESSED_DIR.parent.parent)}"
        )


if __name__ == "__main__":
    main()
