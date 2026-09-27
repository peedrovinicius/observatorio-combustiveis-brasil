from __future__ import annotations

import pandas as pd

from .atomic_outputs import replace_csv_batch
from .config import (
    PROCESSED_DIR,
    RAW_OPEN_DATA_DIR,
    REPORTS_DIR,
)
from .provenance import (
    verify_station_transform_provenance,
)
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
    verify_station_transform_provenance(
        PROCESSED_DIR,
        RAW_OPEN_DATA_DIR,
        REPORTS_DIR,
    )

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

    outputs = replace_csv_batch(
        STATION_MODEL_DIR,
        tables,
    )

    for output in outputs:
        name = output.stem
        table = tables[name]
        print(
            f"{name}: "
            f"{len(table):,} linhas -> "
            f"{output.relative_to(PROCESSED_DIR.parent.parent)}"
        )


if __name__ == "__main__":
    main()
