from __future__ import annotations

from collections.abc import Mapping


def validate_download_payload(
    content: bytes,
    headers: Mapping[str, str],
    url: str,
) -> None:
    if not content:
        raise RuntimeError(
            "Download vazio recebido: "
            f"{url}"
        )

    content_encoding = str(
        headers.get(
            "Content-Encoding",
            "",
        )
    ).strip().casefold()
    declared = str(
        headers.get(
            "Content-Length",
            "",
        )
    ).strip()

    if (
        not declared
        or content_encoding
        not in {
            "",
            "identity",
        }
    ):
        return

    try:
        expected = int(
            declared
        )
    except ValueError as exc:
        raise RuntimeError(
            "Content-Length inválido "
            f"recebido de {url}: {declared}"
        ) from exc

    if expected < 0:
        raise RuntimeError(
            "Content-Length negativo "
            f"recebido de {url}."
        )
    if expected != len(
        content
    ):
        raise RuntimeError(
            "Content-Length divergente "
            f"em {url}: esperado={expected}, "
            f"recebido={len(content)}."
        )
