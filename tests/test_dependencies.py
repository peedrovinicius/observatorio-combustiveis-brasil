from src.config import PROJECT_ROOT


def _lines(name: str) -> set[str]:
    return {
        line.strip()
        for line in (
            PROJECT_ROOT
            / name
        ).read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
    }


def test_runtime_requirements_exclude_dev_tools() -> None:
    runtime = _lines(
        "requirements.txt"
    )

    assert not any(
        line.startswith("pytest")
        for line in runtime
    )
    assert not any(
        line.startswith("jupyter")
        for line in runtime
    )


def test_dev_requirements_extend_runtime() -> None:
    dev = _lines(
        "requirements-dev.txt"
    )

    assert "-r requirements.txt" in dev
    assert any(
        line.startswith("pytest")
        for line in dev
    )
    assert not any(
        line.startswith("jupyter")
        for line in dev
    )


def test_notebook_requirements_extend_runtime() -> None:
    notebook = _lines(
        "requirements-notebook.txt"
    )

    assert "-r requirements.txt" in notebook
    assert any(
        line.startswith("jupyter")
        for line in notebook
    )
    assert not any(
        line.startswith("pytest")
        for line in notebook
    )
