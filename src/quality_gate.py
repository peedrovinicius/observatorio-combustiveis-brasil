from __future__ import annotations

import json
from pathlib import Path


def load_passed_quality_report(
    path: Path,
    label: str,
) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(
            "Relatório de qualidade ausente: "
            f"{label} ({path})."
        )

    try:
        report = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Relatório de qualidade inválido: "
            f"{label} ({path})."
        ) from exc

    if not isinstance(
        report,
        dict,
    ):
        raise ValueError(
            "Relatório de qualidade deve ser "
            f"um objeto JSON: {label}."
        )

    status = str(
        report.get(
            "status",
            "",
        )
    ).strip().casefold()
    if status != "passed":
        raise ValueError(
            "Relatório de qualidade não aprovado: "
            f"{label} (status={status or 'n/d'})."
        )

    return report
