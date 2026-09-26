from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd


def _validate_output_name(
    name: str,
) -> None:
    if (
        not name
        or Path(name).name != name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
    ):
        raise ValueError(
            "Nome de saída CSV inválido: "
            f"{name!r}"
        )


def replace_csv_batch(
    directory: Path,
    tables: dict[
        str,
        pd.DataFrame,
    ],
) -> list[Path]:
    if not tables:
        raise ValueError(
            "Lote de CSVs vazio."
        )

    names = list(
        tables
    )
    for name in names:
        _validate_output_name(
            name
        )

    normalized = [
        name.casefold()
        for name in names
    ]
    if len(normalized) != len(
        set(normalized)
    ):
        raise ValueError(
            "Lote de CSVs contém "
            "nomes duplicados."
        )

    directory.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix=".csv_batch_",
        dir=directory.parent,
    ) as temporary:
        root = Path(
            temporary
        )
        stage = (
            root
            / "stage"
        )
        backup = (
            root
            / "backup"
        )
        stage.mkdir()
        backup.mkdir()

        staged: list[
            tuple[
                str,
                Path,
            ]
        ] = []
        for name, table in (
            tables.items()
        ):
            path = (
                stage
                / f"{name}.csv"
            )
            table.to_csv(
                path,
                index=False,
                encoding="utf-8",
            )
            staged.append(
                (
                    name,
                    path,
                )
            )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        existing = sorted(
            path
            for path in directory.glob(
                "*.csv"
            )
            if path.is_file()
        )
        backed_up: list[
            tuple[
                Path,
                Path,
            ]
        ] = []
        installed: list[
            Path
        ] = []

        try:
            for path in existing:
                backup_path = (
                    backup
                    / path.name
                )
                shutil.move(
                    str(path),
                    str(backup_path),
                )
                backed_up.append(
                    (
                        path,
                        backup_path,
                    )
                )

            outputs: list[
                Path
            ] = []
            for _, staged_path in staged:
                destination = (
                    directory
                    / staged_path.name
                )
                shutil.move(
                    str(staged_path),
                    str(destination),
                )
                installed.append(
                    destination
                )
                outputs.append(
                    destination
                )

            return outputs
        except Exception:
            for path in reversed(
                installed
            ):
                if path.exists():
                    path.unlink()

            for original, backup_path in reversed(
                backed_up
            ):
                if backup_path.exists():
                    shutil.move(
                        str(backup_path),
                        str(original),
                    )
            raise
