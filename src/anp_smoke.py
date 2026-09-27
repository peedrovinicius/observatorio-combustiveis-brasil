from __future__ import annotations

import json
from collections.abc import Iterable

import requests

from .config import (
    ANP_HISTORICAL_PAGE,
    ANP_OPEN_DATA_PAGE,
)
from .download_history import (
    _discover_weekly_history_links,
)
from .download_open_data import (
    _discover_2026_links,
)
from .file_formats import (
    UnsupportedDownloadError,
    detect_download_kind,
)

SAMPLE_BYTES = 65_536
USER_AGENT = (
    "observatorio-combustiveis-brasil/"
    "anp-smoke"
)


def _page_html(
    session: requests.Session,
    url: str,
) -> str:
    response = session.get(
        url,
        timeout=30,
        headers={
            "User-Agent": USER_AGENT,
        },
    )
    response.raise_for_status()
    if not response.text.strip():
        raise RuntimeError(
            f"Página oficial vazia: {url}"
        )
    return response.text


def _sample_response(
    response: requests.Response,
) -> bytes:
    chunks: list[bytes] = []
    size = 0

    for chunk in response.iter_content(
        chunk_size=8192
    ):
        if not chunk:
            continue
        remaining = (
            SAMPLE_BYTES
            - size
        )
        if remaining <= 0:
            break
        part = chunk[
            :remaining
        ]
        chunks.append(
            part
        )
        size += len(
            part
        )
        if size >= SAMPLE_BYTES:
            break

    return b"".join(
        chunks
    )


def _probe_resource(
    session: requests.Session,
    url: str,
    allowed_kinds: Iterable[str],
) -> dict[str, str | int]:
    with session.get(
        url,
        timeout=45,
        stream=True,
        allow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Range": (
                f"bytes=0-{SAMPLE_BYTES - 1}"
            ),
        },
    ) as response:
        response.raise_for_status()
        sample = _sample_response(
            response
        )
        if not sample:
            raise RuntimeError(
                "Recurso oficial retornou "
                f"conteúdo vazio: {url}"
            )

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            )
        )
        allowed = set(
            allowed_kinds
        )
        zip_prefix = sample.startswith(
            (
                b"PK\x03\x04",
                b"PK\x05\x06",
                b"PK\x07\x08",
            )
        )
        try:
            if (
                zip_prefix
                and "zip" in allowed
            ):
                kind = "zip"
            else:
                kind = detect_download_kind(
                    sample,
                    response.url,
                    content_type,
                )
        except UnsupportedDownloadError as exc:
            raise RuntimeError(
                "Recurso oficial não parece "
                f"um arquivo de dados válido: {url}"
            ) from exc

        if kind not in allowed:
            raise RuntimeError(
                "Formato inesperado no recurso "
                f"{url}: {kind}; esperados="
                + ", ".join(
                    sorted(
                        allowed
                    )
                )
            )

        return {
            "url": url,
            "final_url": response.url,
            "status_code": (
                response.status_code
            ),
            "detected_kind": kind,
            "sample_bytes": len(
                sample
            ),
        }


def run_smoke(
    session: requests.Session | None = None,
) -> dict[str, object]:
    owns_session = session is None
    active = (
        session
        if session is not None
        else requests.Session()
    )

    try:
        history_html = _page_html(
            active,
            ANP_HISTORICAL_PAGE,
        )
        history_links = (
            _discover_weekly_history_links(
                history_html
            )
        )
        history_probes = {
            scope: _probe_resource(
                active,
                url,
                {
                    "xlsx",
                    "zip",
                },
            )
            for scope, url
            in history_links.items()
        }

        open_html = _page_html(
            active,
            ANP_OPEN_DATA_PAGE,
        )
        open_links = (
            _discover_2026_links(
                open_html
            )
        )
        open_probes = [
            {
                "dataset": item[
                    "dataset"
                ],
                **_probe_resource(
                    active,
                    item["url"],
                    {
                        "csv",
                        "zip",
                    },
                ),
            }
            for item in open_links
        ]

        return {
            "status": "passed",
            "history_scopes": sorted(
                history_links
            ),
            "history_resources": (
                history_probes
            ),
            "open_data_datasets": [
                item[
                    "dataset"
                ]
                for item in open_links
            ],
            "open_data_resources": (
                open_probes
            ),
        }
    finally:
        if owns_session:
            active.close()


def main() -> None:
    print(
        json.dumps(
            run_smoke(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
