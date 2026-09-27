from src.config import PROJECT_ROOT


def _workflow() -> str:
    return (
        PROJECT_ROOT
        / ".github"
        / "workflows"
        / "ci.yml"
    ).read_text(
        encoding="utf-8",
    )


def test_ci_uses_current_official_actions() -> None:
    workflow = _workflow()

    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow
    assert "# v7.0.1" in workflow
    assert "# v7.0.0" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "actions/setup-python@v5" not in workflow


def test_ci_uses_test_dependency_profile() -> None:
    workflow = _workflow()

    assert (
        "pip install -r requirements-dev.txt"
        in workflow
    )
    assert (
        "pip install -r requirements.txt"
        not in workflow
    )


def test_ci_limits_permissions_and_duplicate_runs() -> None:
    workflow = _workflow()

    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "cancel-in-progress: true" in workflow
    assert "timeout-minutes: 10" in workflow


def test_ci_runs_matplotlib_headless() -> None:
    workflow = _workflow()

    assert "MPLBACKEND: Agg" in workflow
