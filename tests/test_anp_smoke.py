from __future__ import annotations

import pytest

from src.anp_smoke import (
    _page_html,
    _probe_resource,
)


class _Response:
    def __init__(
        self,
        content: bytes,
        *,
        url: str = "https://example.test/data.csv",
        content_type: str = "text/csv",
        status_code: int = 200,
    ) -> None:
        self._content = content
        self.url = url
        self.status_code = status_code
        self.headers = {
            "Content-Type": content_type,
        }
        self.text = content.decode(
            "utf-8",
            errors="replace",
        )

    def raise_for_status(
        self,
    ) -> None:
        if self.status_code >= 400:
            raise RuntimeError(
                f"HTTP {self.status_code}"
            )

    def iter_content(
        self,
        chunk_size: int,
    ):
        for index in range(
            0,
            len(
                self._content
            ),
            chunk_size,
        ):
            yield self._content[
                index:
                index + chunk_size
            ]

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        return None


class _Session:
    def __init__(
        self,
        response: _Response,
    ) -> None:
        self.response = response

    def get(
        self,
        url: str,
        **kwargs,
    ) -> _Response:
        return self.response


def test_page_html_rejects_empty_page() -> None:
    session = _Session(
        _Response(
            b"   ",
            content_type="text/html",
        )
    )

    with pytest.raises(
        RuntimeError,
        match="Página oficial vazia",
    ):
        _page_html(
            session,
            "https://example.test/page",
        )


def test_probe_resource_accepts_csv_sample() -> None:
    session = _Session(
        _Response(
            b"produto;preco\nGASOLINA;6,10\n",
        )
    )

    result = _probe_resource(
        session,
        "https://example.test/data.csv",
        {
            "csv",
        },
    )

    assert (
        result[
            "detected_kind"
        ]
        == "csv"
    )
    assert (
        result[
            "sample_bytes"
        ]
        > 0
    )


def test_probe_resource_accepts_partial_zip_sample() -> None:
    session = _Session(
        _Response(
            b"PK\x03\x04"
            + b"x" * 100,
            url="https://example.test/data.xlsx",
            content_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
        )
    )

    result = _probe_resource(
        session,
        "https://example.test/data.xlsx",
        {
            "xlsx",
            "zip",
        },
    )

    assert (
        result[
            "detected_kind"
        ]
        in {
            "xlsx",
            "zip",
        }
    )


def test_probe_resource_rejects_html_disguised_as_csv() -> None:
    session = _Session(
        _Response(
            b"<!doctype html><html>erro</html>",
            url="https://example.test/data.csv",
            content_type="text/csv",
        )
    )

    with pytest.raises(
        RuntimeError,
        match="arquivo de dados válido",
    ):
        _probe_resource(
            session,
            "https://example.test/data.csv",
            {
                "csv",
            },
        )
