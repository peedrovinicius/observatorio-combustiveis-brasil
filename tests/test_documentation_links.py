import re
from pathlib import Path
from urllib.parse import unquote

from src.config import PROJECT_ROOT


MARKDOWN_LINK = re.compile(
    r"!?[[^]]*](([^)]+))"
)
HTML_SRC = re.compile(
    r"""src=["']([^"']+)["']"""
)


def _markdown_files() -> list[Path]:
    files = [
        PROJECT_ROOT / "README.md",
    ]
    for root_name in (
        "docs",
        "notebooks",
        "powerbi",
        "reports",
    ):
        root = (
            PROJECT_ROOT
            / root_name
        )
        if root.exists():
            files.extend(
                root.rglob("*.md")
            )
    return sorted(
        set(files)
    )


def _local_target(
    document: Path,
    raw_target: str,
) -> Path | None:
    target = (
        raw_target
        .strip()
        .split(
            "#",
            1,
        )[0]
        .strip()
    )
    if not target:
        return None

    lowered = target.casefold()
    if lowered.startswith(
        (
            "http://",
            "https://",
            "mailto:",
            "tel:",
            "data:",
        )
    ):
        return None

    target = unquote(
        target
    )
    return (
        document.parent
        / target
    ).resolve()


def test_relative_documentation_links_exist() -> None:
    violations: list[str] = []

    for document in _markdown_files():
        content = document.read_text(
            encoding="utf-8",
        )
        targets = [
            *MARKDOWN_LINK.findall(
                content
            ),
            *HTML_SRC.findall(
                content
            ),
        ]

        for raw_target in targets:
            target = _local_target(
                document,
                raw_target,
            )
            if (
                target is not None
                and not target.exists()
            ):
                violations.append(
                    f"{document.relative_to(PROJECT_ROOT)} "
                    f"-> {raw_target}"
                )

    assert not violations, (
        "Links locais quebrados:\n"
        + "\n".join(
            violations
        )
    )
