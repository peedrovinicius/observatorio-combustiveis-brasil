from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .config import ANP_WEEKLY_PAGE, RAW_DIR

TIMEOUT_SECONDS = 60
USER_AGENT = "observatorio-combustiveis-brasil/1.0"

TARGETS = {
    "precos_medios_semanais": "Preços médios semanais",
    "precos_por_posto": "Preços por posto revendedor",
}


def _safe_filename(url: str, fallback: str) -> str:
    name = Path(unquote(urlparse(url).path)).name
    if not name or "." not in name:
        return fallback
    name = re.sub(r"[^A-Za-z0-9._()-]+", "_", name)
    return name[:180]


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _discover_latest_links(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    discovered: dict[str, str] = {}

    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.stripped_strings)
        for key, label in TARGETS.items():
            if key not in discovered and label.casefold() in text.casefold():
                discovered[key] = urljoin(ANP_WEEKLY_PAGE, anchor["href"])

        if len(discovered) == len(TARGETS):
            break

    missing = set(TARGETS) - set(discovered)
    if missing:
        raise RuntimeError(
            "Não foi possível localizar todos os arquivos esperados na página da ANP. "
            f"Ausentes: {', '.join(sorted(missing))}."
        )

    return discovered


def _download(session: requests.Session, url: str) -> tuple[bytes, str, str]:
    response = session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)
    response.raise_for_status()
    return response.content, response.url, response.headers.get("Content-Type", "")


def main() -> None:
    raise SystemExit(
        "O downloader legado src.download_anp foi desativado. "
        "Use python -m src.download_history para a série agregada "
        "e python -m src.download_open_data para os dados por posto, "
        "ou execute python -m src.pipeline."
    )


if __name__ == "__main__":
    main()
