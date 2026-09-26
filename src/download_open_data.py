from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import (
    ANP_OPEN_DATA_PAGE,
    RAW_OPEN_DATA_DIR,
)
from .file_formats import (
    UnsupportedDownloadError,
    detect_download_kind,
    extension_for_kind,
)

TIMEOUT_SECONDS = 60
USER_AGENT = "observatorio-combustiveis-brasil/1.0"
MONTHS_2026_H2 = {
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
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


def _discover_2026_links(
    html: str,
) -> list[dict[str, str]]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )
    current_section = ""
    discovered: list[
        dict[str, str]
    ] = []
    seen: set[str] = set()

    for element in soup.find_all(
        ["h3", "a"]
    ):
        if element.name == "h3":
            current_section = _normalize(
                element.get_text(
                    " ",
                    strip=True,
                )
            )
            continue

        href = element.get("href")
        if not href:
            continue

        label = " ".join(
            element.stripped_strings
        )
        normalized_label = _normalize(
            label
        )
        url = urljoin(
            ANP_OPEN_DATA_PAGE,
            href,
        )

        include = False
        dataset = ""

        if (
            current_section
            == "combustiveis automotivos"
            and "1o semestre de 2026"
            in normalized_label
        ):
            include = True
            dataset = (
                "automotivos_2026_s1"
            )

        elif current_section in {
            "oleo diesel (s-500 e s-10) + gnv",
            "etanol hidratado + gasolina c",
        }:
            month = next(
                (
                    month
                    for month
                    in MONTHS_2026_H2
                    if month
                    in normalized_label
                ),
                None,
            )
            if (
                month
                and "2026"
                in normalized_label
            ):
                include = True
                family = (
                    "diesel_gnv"
                    if "diesel"
                    in current_section
                    else "etanol_gasolina"
                )
                dataset = (
                    f"{family}_{month}_2026"
                )

        elif (
            current_section
            == "quatro ultimas semanas"
        ):
            if "diesel" in normalized_label:
                include = True
                dataset = (
                    "diesel_gnv_ultimas_4_semanas"
                )
            elif (
                "etanol"
                in normalized_label
                or "gasolina"
                in normalized_label
            ):
                include = True
                dataset = (
                    "etanol_gasolina_ultimas_4_semanas"
                )

        if include and url not in seen:
            discovered.append(
                {
                    "dataset": dataset,
                    "label": label,
                    "url": url,
                }
            )
            seen.add(url)

    if not discovered:
        raise RuntimeError(
            "Nenhum arquivo aberto de preços de 2026 "
            "foi localizado na ANP."
        )

    return discovered


def _extract_csvs(
    content: bytes,
    destination: Path,
) -> list[Path]:
    extracted: list[Path] = []
    used_names: set[str] = set()

    with zipfile.ZipFile(
        BytesIO(content)
    ) as archive:
        for info in archive.infolist():
            if (
                info.is_dir()
                or not info.filename
                .lower()
                .endswith(".csv")
            ):
                continue

            basename = Path(
                info.filename
            ).name
            if basename in used_names:
                raise ValueError(
                    "ZIP da ANP contém CSVs com "
                    f"nome repetido: {basename}"
                )
            used_names.add(basename)

            target = (
                destination
                / basename
            )
            target.write_bytes(
                archive.read(info)
            )
            extracted.append(target)

    if not extracted:
        raise ValueError(
            "O ZIP baixado da ANP não contém arquivos CSV."
        )

    return extracted


def _download_resource(
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
        detect_download_kind(
            response.content,
            response.url,
            response.headers.get(
                "Content-Type",
                "",
            ),
        )
        return response
    except UnsupportedDownloadError:
        pass

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
            f"A URL da ANP retornou conteúdo inválido: {url}"
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
                (
                    ".csv",
                    ".zip",
                    ".xlsx",
                )
            )
        ):
            candidates.append(href)

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
            detect_download_kind(
                file_response.content,
                file_response.url,
                file_response.headers.get(
                    "Content-Type",
                    "",
                ),
            )
        except UnsupportedDownloadError:
            continue

        return file_response

    raise RuntimeError(
        "A URL da ANP não levou a um arquivo "
        f"CSV/ZIP válido: {url}"
    )


def main() -> None:
    RAW_OPEN_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
        }
    )

    page = session.get(
        ANP_OPEN_DATA_PAGE,
        timeout=TIMEOUT_SECONDS,
    )
    page.raise_for_status()
    links = _discover_2026_links(
        page.text
    )

    collected_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )
    records: list[
        dict[str, object]
    ] = []

    for item in links:
        response = _download_resource(
            session,
            item["url"],
        )
        kind = detect_download_kind(
            response.content,
            response.url,
            response.headers.get(
                "Content-Type",
                "",
            ),
        )
        suffix = extension_for_kind(
            kind
        )

        if kind == "xlsx":
            raise RuntimeError(
                "A camada aberta por posto esperava CSV ou ZIP, "
                f"mas recebeu XLSX em {response.url}"
            )

        stem = re.sub(
            r"[^a-z0-9_-]+",
            "_",
            _normalize(
                item["dataset"]
            ).replace(
                " ",
                "_",
            ),
        )
        raw_path = (
            RAW_OPEN_DATA_DIR
            / f"{stem}{suffix}"
        )
        raw_path.write_bytes(
            response.content
        )

        extracted: list[str] = []
        if kind == "zip":
            extract_dir = (
                RAW_OPEN_DATA_DIR
                / stem
            )
            extract_dir.mkdir(
                parents=True,
                exist_ok=True,
            )
            extracted = [
                str(
                    path.relative_to(
                        RAW_OPEN_DATA_DIR
                    )
                )
                for path
                in _extract_csvs(
                    response.content,
                    extract_dir,
                )
            ]

        records.append(
            {
                **item,
                "final_url": response.url,
                "filename": raw_path.name,
                "detected_format": kind,
                "bytes": len(
                    response.content
                ),
                "sha256": _sha256(
                    response.content
                ),
                "content_type": (
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                ),
                "extracted_csvs": (
                    extracted
                ),
                "collected_at_utc": (
                    collected_at
                ),
            }
        )
        print(
            "Salvo: "
            f"{raw_path.relative_to(RAW_OPEN_DATA_DIR.parent.parent.parent)}"
        )

    manifest = {
        "source": (
            "Agência Nacional do Petróleo, "
            "Gás Natural e Biocombustíveis - ANP"
        ),
        "source_page": (
            ANP_OPEN_DATA_PAGE
        ),
        "collected_at_utc": (
            collected_at
        ),
        "files": records,
    }
    (
        RAW_OPEN_DATA_DIR
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
