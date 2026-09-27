from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .atomic_outputs import (
    replace_text_file,
)
from .config import RAW_DIR
from .provenance import (
    verify_history_provenance,
)


def _inspect_excel(path: Path) -> dict[str, object]:
    workbook = pd.ExcelFile(path)
    sheets: dict[str, object] = {}

    for sheet in workbook.sheet_names:
        frame = pd.read_excel(path, sheet_name=sheet)
        sheets[sheet] = {
            "rows": int(frame.shape[0]),
            "columns": int(frame.shape[1]),
            "column_names": [str(column) for column in frame.columns],
            "nulls": {
                str(key): int(value)
                for key, value in frame.isna().sum().items()
            },
        }

    return {"type": "excel", "sheets": sheets}


def _read_csv_flexible(path: Path) -> pd.DataFrame:
    attempts = [
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "latin-1"},
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "latin-1"},
    ]
    last_error: Exception | None = None

    for options in attempts:
        try:
            frame = pd.read_csv(path, **options)
            if frame.shape[1] > 1:
                return frame
        except Exception as exc:  # pragma: no cover - diagnostics only
            last_error = exc

    raise RuntimeError(f"Não foi possível ler {path.name}: {last_error}")


def _inspect_csv(path: Path) -> dict[str, object]:
    frame = _read_csv_flexible(path)
    return {
        "type": "csv",
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "column_names": [str(column) for column in frame.columns],
        "nulls": {
            str(key): int(value)
            for key, value in frame.isna().sum().items()
        },
    }


def inspect(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return _inspect_excel(path)
    if suffix == ".csv":
        return _inspect_csv(path)
    return {"type": "unsupported", "suffix": suffix}


def main() -> None:
    verify_history_provenance(
        RAW_DIR
    )

    files = [
        path
        for path in RAW_DIR.iterdir()
        if path.is_file()
        and path.name != "README.md"
        and path.suffix.lower() != ".json"
    ]

    if not files:
        raise SystemExit(
            "Nenhum arquivo bruto encontrado. Execute python -m src.download_history."
        )

    report = {path.name: inspect(path) for path in sorted(files)}
    output = RAW_DIR / "inspection.json"
    replace_text_file(
        output,
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nRelatório salvo em: {output}")


if __name__ == "__main__":
    main()
