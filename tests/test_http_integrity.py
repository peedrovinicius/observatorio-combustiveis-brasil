import pytest

from src.http_integrity import (
    validate_download_payload,
)


def test_http_payload_accepts_exact_content_length() -> None:
    validate_download_payload(
        b"abc",
        {
            "Content-Length": "3",
        },
        "https://example.test/file.csv",
    )


def test_http_payload_accepts_missing_content_length() -> None:
    validate_download_payload(
        b"abc",
        {},
        "https://example.test/file.csv",
    )


def test_http_payload_rejects_empty_content() -> None:
    with pytest.raises(
        RuntimeError,
        match="Download vazio",
    ):
        validate_download_payload(
            b"",
            {},
            "https://example.test/file.csv",
        )


def test_http_payload_rejects_declared_length_mismatch() -> None:
    with pytest.raises(
        RuntimeError,
        match="Content-Length divergente",
    ):
        validate_download_payload(
            b"abc",
            {
                "Content-Length": "4",
            },
            "https://example.test/file.csv",
        )


def test_http_payload_skips_length_check_when_compressed() -> None:
    validate_download_payload(
        b"conteudo-descomprimido",
        {
            "Content-Length": "7",
            "Content-Encoding": "gzip",
        },
        "https://example.test/file.csv",
    )


def test_http_payload_rejects_invalid_content_length() -> None:
    with pytest.raises(
        RuntimeError,
        match="Content-Length inválido",
    ):
        validate_download_payload(
            b"abc",
            {
                "Content-Length": "abc",
            },
            "https://example.test/file.csv",
        )
