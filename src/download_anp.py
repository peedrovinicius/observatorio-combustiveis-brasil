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
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        page = session.get(ANP_WEEKLY_PAGE, timeout=TIMEOUT_SECONDS)
        page.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(
            "Falha ao acessar a página oficial da ANP. "
            "Verifique sua conexão e tente novamente. "
            f"Detalhe: {exc}"
        ) from exc

    links = _discover_latest_links(page.text)

    collected_at = datetime.now(timezone.utc).isoformat()
    files: list[dict[str, object]] = []

    for dataset_name, file_url in links.items():
        try:
            content, final_url, content_type = _download(session, file_url)
        except requests.RequestException as exc:
            raise SystemExit(
                f"Falha ao baixar o dataset {dataset_name} da ANP: {exc}"
            ) from exc

        fallback = f"{dataset_name}.bin"
        filename = _safe_filename(final_url, fallback)
        destination = RAW_DIR / filename
        destination.write_bytes(content)

        files.append(
            {
                "dataset": dataset_name,
                "source_page": ANP_WEEKLY_PAGE,
                "discovered_url": file_url,
                "final_url": final_url,
                "filename": filename,
                "content_type": content_type,
                "bytes": len(content),
                "sha256": _sha256(content),
                "collected_at_utc": collected_at,
            }
        )
        print(f"Salvo: {destination.relative_to(RAW_DIR.parent.parent)}")

    manifest = {
        "source": "Agência Nacional do Petróleo, Gás Natural e Biocombustíveis - ANP",
        "source_page": ANP_WEEKLY_PAGE,
        "collected_at_utc": collected_at,
        "files": files,
    }
    manifest_path = RAW_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Manifesto: {manifest_path.relative_to(RAW_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
