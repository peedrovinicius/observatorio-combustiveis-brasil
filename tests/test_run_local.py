from src.config import PROJECT_ROOT


def test_run_local_checks_native_exit_codes() -> None:
    script = (
        PROJECT_ROOT
        / "scripts"
        / "run_local.ps1"
    ).read_text(
        encoding="utf-8",
    )

    assert "function Invoke-NativeChecked" in script
    assert "$LASTEXITCODE -ne 0" in script
    assert (
        '"requirements-dev.txt"'
        in script
    )
    assert (
        '"requirements.txt"'
        not in script
    )
    assert (
        'Invoke-NativeChecked -FilePath $python '
        '-Arguments @("-m", "pytest")'
        in script
    )
    assert (
        'Invoke-NativeChecked -FilePath $python '
        '-Arguments @("-m", "src.pipeline")'
        in script
    )
    assert (
        'Invoke-NativeChecked -FilePath "docker" '
        '-Arguments @("compose", "up", "-d", "--wait", '
        '"--wait-timeout", "60", "postgres")'
        in script
    )
    assert (
        'Invoke-NativeChecked -FilePath $python '
        '-Arguments @("-m", "src.load_postgres")'
        in script
    )
    assert (
        'Invoke-NativeChecked -FilePath $python '
        '-Arguments @("-m", "src.snapshot")'
        in script
    )


def test_run_local_has_no_unchecked_core_commands() -> None:
    script = (
        PROJECT_ROOT
        / "scripts"
        / "run_local.ps1"
    ).read_text(
        encoding="utf-8",
    )

    assert "& $python -m pytest" not in script
    assert "& $python -m src.pipeline" not in script
    assert "& $python -m src.load_postgres" not in script
    assert "& $python -m src.snapshot" not in script
    assert "docker compose up -d postgres" not in script


def test_run_local_waits_for_postgres_health() -> None:
    script = (
        PROJECT_ROOT
        / "scripts"
        / "run_local.ps1"
    ).read_text(
        encoding="utf-8",
    )

    assert '"--wait"' in script
    assert '"--wait-timeout", "60"' in script
    assert (
        script.index('"--wait"')
        < script.index('"src.load_postgres"')
    )
