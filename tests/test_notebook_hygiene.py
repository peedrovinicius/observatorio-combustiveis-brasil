import json

from src.config import PROJECT_ROOT


def test_notebooks_do_not_commit_execution_state() -> None:
    notebooks = sorted(
        (
            PROJECT_ROOT
            / "notebooks"
        ).glob("*.ipynb")
    )

    assert notebooks

    for path in notebooks:
        notebook = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

        for index, cell in enumerate(
            notebook.get(
                "cells",
                [],
            )
        ):
            if (
                cell.get(
                    "cell_type"
                )
                != "code"
            ):
                continue

            assert (
                cell.get(
                    "execution_count"
                )
                is None
            ), (
                f"{path.name}: célula {index} "
                "possui execution_count salvo"
            )
            assert (
                cell.get(
                    "outputs",
                    []
                )
                == []
            ), (
                f"{path.name}: célula {index} "
                "possui output persistido"
            )


def test_notebooks_use_python_kernel_metadata() -> None:
    notebooks = sorted(
        (
            PROJECT_ROOT
            / "notebooks"
        ).glob("*.ipynb")
    )

    assert notebooks

    for path in notebooks:
        notebook = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
        kernelspec = (
            notebook.get(
                "metadata",
                {}
            )
            .get(
                "kernelspec",
                {}
            )
        )

        assert (
            kernelspec.get(
                "language"
            )
            == "python"
        )
        assert (
            kernelspec.get(
                "name"
            )
            == "python3"
        )
