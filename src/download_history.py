from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import (
    unquote,
    urljoin,
    urlparse,
)

import requests
from bs4 import BeautifulSoup

from .config import (
    ANP_HISTORICAL_PAGE,
    RAW_DIR,
)
from .file_formats import (
    UnsupportedDownloadError,
    detect_download_kind,
)

TIMEOUT_SECONDS = 60
USER_AGENT = "observatorio-combustiveis-brasil/1.0"

TARGETS = {
    "brasil": "Brasil",
    "regioes": "Regiões",
    "estados": "Estados",
    "municipios_2026": "Municípios (2026)",
}


def _normalize(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value,
    )
    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )
    return (
        re.sub(r"\s+", " ", value)
        .strip()
        .casefold()
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(
        content
    ).hexdigest()


def _safe_filename(
    url: str,
    fallback: str,
) -> str:
    name = Path(
        unquote(
            urlparse(url).path
        )
    ).name
    if (
        not name
        or "." not in name
    ):
        return fallback
    return re.sub(
        r"[^A-Za-z0-9._()-]+",
        "_",
        name,
    )[:160]


def _clear_history_scope(
    root: Path,
    scope: str,
) -> None:
    prefix = (
        f"historico_semanal_{scope}__"
    )
    for path in root.glob(
        prefix + "*"
    ):
        if path.is_file():
            path.unlink()


def _discover_weekly_history_links(
    html: str,
) -> dict[str, str]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )
    heading = next(
        (
            item
            for item
            in soup.find_all(
                ["h2", "h3"]
            )
            if (
                "serie historica semanal"
                in _normalize(
                    item.get_text(
                        " ",
                        strip=True,
                    )
                )
            )
        ),
        None,
    )
    if heading is None:
        raise RuntimeError(
            "Seção de série histórica semanal "
            "não encontrada na ANP."
        )

    expected = {
        _normalize(label): key
        for key, label
        in TARGETS.items()
    }
    discovered: dict[
        str,
        str,
    ] = {}
    modern_series = False

    for element in heading.find_all_next():
        if (
            element is not heading
            and element.name
            in {"h2", "h3"}
        ):
            break
        if (
            element.name != "a"
            or not element.get(
                "href"
            )
        ):
            continue

        label = " ".join(
            element.stripped_strings
        )
        normalized = _normalize(
            label
        )

        if (
            "a partir de 2013"
            in normalized
        ):
            modern_series = True
            continue
        if not modern_series:
            continue

        key = expected.get(
            normalized
        )
        if (
            key
            and key
            not in discovered
        ):
            discovered[key] = urljoin(
                ANP_HISTORICAL_PAGE,
                element["href"],
            )

    missing = (
        set(TARGETS)
        - set(discovered)
    )
    if missing:
        raise RuntimeError(
            "Links semanais esperados "
            "não encontrados na ANP: "
            + ", ".join(
                sorted(missing)
            )
        )
    return discovered


def _download_xlsx_resource(
    session: requests.Session,
    url: str,
) -> requests.Response:
    response = session.get(
        url,
        timeout=TIMEOUT_SECONDS,
        allow_redirects=True,
    )
    response.raise_for_status()

    try:
        kind = detect_download_kind(
            response.content,
            response.url,
            response.headers.get(
                "Content-Type",
                "",
            ),
        )
    except UnsupportedDownloadError:
        kind = None

    if kind == "xlsx":
        return response
    if kind is not None:
        raise RuntimeError(
            "A série histórica semanal esperava XLSX, "
            f"mas recebeu {kind}: {url}"
        )

    content_type = (
        response.headers
        .get(
            "Content-Type",
            "",
        )
        .casefold()
    )
    if "html" not in content_type:
        raise RuntimeError(
            "A série histórica semanal retornou "
            f"conteúdo inválido: {url}"
        )

    candidates: list[str] = []
    base = (
        response.url[:-5]
        if response.url.endswith(
            "/view"
        )
        else response.url.rstrip("/")
    )
    candidates.append(
        base + "/@@download/file"
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )
    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = urljoin(
            response.url,
            anchor["href"],
        )
        lower = href.casefold()
        if (
            "@@download/file"
            in lower
            or lower.endswith(
                ".xlsx"
            )
        ):
            candidates.append(
                href
            )

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)

        file_response = session.get(
            candidate,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        if not file_response.ok:
            continue

        try:
            kind = detect_download_kind(
                file_response.content,
                file_response.url,
                file_response.headers.get(
                    "Content-Type",
                    "",
                ),
            )
        except UnsupportedDownloadError:
            continue

        if kind == "xlsx":
            return file_response

    raise RuntimeError(
        "A URL da ANP não levou a uma "
        f"planilha XLSX válida: {url}"
    )


def main() -> None:
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
        }
    )

    try:
        page = session.get(
            ANP_HISTORICAL_PAGE,
            timeout=TIMEOUT_SECONDS,
        )
        page.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(
            "Falha ao acessar a série "
            f"histórica da ANP: {exc}"
        ) from exc

    links = (
        _discover_weekly_history_links(
            page.text
        )
    )
    collected_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )
    files: list[
        dict[str, object]
    ] = []

    for scope, url in links.items():
        try:
            response = (
                _download_xlsx_resource(
                    session,
                    url,
                )
            )
        except (
            requests.RequestException,
            RuntimeError,
        ) as exc:
            raise SystemExit(
                "Falha ao baixar a série "
                f"'{scope}': {exc}"
            ) from exc

        detected_format = (
            detect_download_kind(
                response.content,
                response.url,
                response.headers.get(
                    "Content-Type",
                    "",
                ),
            )
        )

        remote_name = _safe_filename(
            response.url,
            f"{scope}.xlsx",
        )
        if not remote_name.casefold().endswith(
            ".xlsx"
        ):
            remote_name = (
                f"{scope}.xlsx"
            )

        filename = (
            f"historico_semanal_"
            f"{scope}__{remote_name}"
        )
        destination = (
            RAW_DIR
            / filename
        )

        _clear_history_scope(
            RAW_DIR,
            scope,
        )

        destination.write_bytes(
            response.content
        )

        files.append(
            {
                "dataset": (
                    "serie_historica_semanal"
                ),
                "scope": scope,
                "source_page": (
                    ANP_HISTORICAL_PAGE
                ),
                "discovered_url": url,
                "final_url": (
                    response.url
                ),
                "filename": filename,
                "detected_format": (
                    detected_format
                ),
                "content_type": (
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                ),
                "bytes": len(
                    response.content
                ),
                "sha256": _sha256(
                    response.content
                ),
                "collected_at_utc": (
                    collected_at
                ),
            }
        )
        print(
            "Salvo: "
            f"{destination.relative_to(RAW_DIR.parent.parent)}"
        )

    manifest_path = (
        RAW_DIR
        / "history_manifest.json"
    )
    manifest_path.write_text(
        json.dumps(
            {
                "source": "ANP",
                "series": (
                    "Levantamento de Preços "
                    "- série histórica semanal"
                ),
                "collected_at_utc": (
                    collected_at
                ),
                "files": files,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "Manifesto: "
        f"{manifest_path.relative_to(RAW_DIR.parent.parent)}"
    )


if __name__ == "__main__":
    main()
