import pandas as pd

from src.quality import (
    build_quality_report,
)


def test_aggregate_quality_rejects_empty_dataset() -> None:
    frame = pd.DataFrame(
        columns=[
            "data_inicial",
            "produto",
            "preco_medio_revenda",
            "nivel_geografico",
        ]
    )

    report = build_quality_report(
        frame
    )

    assert report["empty_dataset"] is True
    assert report["status"] == "failed"
