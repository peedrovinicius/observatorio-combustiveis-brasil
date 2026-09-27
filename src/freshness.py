from __future__ import annotations

from pathlib import Path


def validate_artifact_freshness(
    inputs: list[Path],
    artifacts: list[Path],
    label: str,
    recovery: str | None = None,
) -> None:
    if not inputs:
        raise ValueError(
            f"{label}: lista de entradas vazia."
        )
    if not artifacts:
        raise ValueError(
            f"{label}: lista de artefatos vazia."
        )

    paths = [
        *inputs,
        *artifacts,
    ]
    missing = [
        path
        for path in paths
        if not path.exists()
    ]
    if missing:
        formatted = "\n".join(
            f"- {path}"
            for path in missing
        )
        raise FileNotFoundError(
            f"{label}: arquivos ausentes:\n"
            f"{formatted}"
        )

    empty = [
        path
        for path in paths
        if (
            path.is_file()
            and path.stat().st_size <= 0
        )
    ]
    if empty:
        formatted = "\n".join(
            f"- {path}"
            for path in empty
        )
        raise ValueError(
            f"{label}: arquivos vazios:\n"
            f"{formatted}"
        )

    latest_input = max(
        path.stat().st_mtime_ns
        for path in inputs
    )
    stale = [
        path
        for path in artifacts
        if (
            path.stat().st_mtime_ns
            < latest_input
        )
    ]
    if stale:
        formatted = "\n".join(
            f"- {path}"
            for path in stale
        )
        guidance = (
            f" {recovery}"
            if recovery
            else ""
        )
        raise ValueError(
            f"{label} desatualizado."
            f"{guidance}\n"
            f"Artefatos antigos:\n{formatted}"
        )
