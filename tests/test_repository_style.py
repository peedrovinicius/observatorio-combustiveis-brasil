from pathlib import Path

from src.config import PROJECT_ROOT

TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".sql",
    ".dax",
    ".ps1",
    ".ipynb",
}

TEXT_ROOTS = [
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "notebooks",
    PROJECT_ROOT / "powerbi",
    PROJECT_ROOT / "reports",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "sql",
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "tests",
]

ROOT_FILES = [
    PROJECT_ROOT / "README.md",
]

FORBIDDEN_DASHES = {
    chr(0x2014),
    chr(0x2013),
}


def _repository_text_files() -> list[Path]:
    files = list(ROOT_FILES)

    for root in TEXT_ROOTS:
        if not root.exists():
            continue

        files.extend(
            path
            for path in root.rglob("*")
            if (
                path.is_file()
                and path.suffix
                in TEXT_EXTENSIONS
            )
        )

    return sorted(set(files))


def test_repository_has_no_typographic_dashes() -> None:
    violations: list[str] = []

    for path in _repository_text_files():
        content = path.read_text(
            encoding="utf-8",
        )
        for line_number, line in enumerate(
            content.splitlines(),
            start=1,
        ):
            if any(
                dash in line
                for dash in FORBIDDEN_DASHES
            ):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:"
                    f"{line_number}: {line.strip()}"
                )

    assert not violations, (
        "Travessões tipográficos encontrados:\n"
        + "\n".join(violations)
    )
