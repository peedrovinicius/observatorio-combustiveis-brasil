from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
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


def _dataset_artifact_candidates(
    root: Path,
    stem: str,
) -> list[Path]:
    return [
        root / f"{stem}.csv",
        root / f"{stem}.zip",
        root / f"{stem}.xlsx",
        root / stem,
    ]


def _remove_path(
    path: Path,
) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _clear_dataset_artifacts(
    root: Path,
    stem: str,
) -> None:
    for path in (
        _dataset_artifact_candidates(
            root,
            stem,
        )
    ):
        _remove_path(
            path
        )


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
            normalized_name = (
                basename.casefold()
            )
            if (
                normalized_name
                in used_names
            ):
                raise ValueError(
                    "ZIP da ANP contém CSVs com "
                    f"nome repetido: {basename}"
                )
            used_names.add(
                normalized_name
            )

            payload = archive.read(
                info
            )
            kind = detect_download_kind(
                payload,
                basename,
                "text/csv",
            )
            if kind != "csv":
                raise ValueError(
                    "ZIP da ANP contém arquivo "
                    f"não reconhecido como CSV: {basename}"
                )

            target = (
                destination
                / basename
            )
            target.write_bytes(
                payload
            )
            extracted.append(target)

    if not extracted:
        raise ValueError(
            "O ZIP baixado da ANP não contém arquivos CSV."
        )

    return extracted


def _replace_dataset_artifacts(
    root: Path,
    stem: str,
    content: bytes,
    kind: str,
) -> tuple[
    Path,
    list[Path],
]:
    if kind not in {
        "csv",
        "zip",
    }:
        raise ValueError(
            "A camada por posto aceita "
            "somente CSV ou ZIP."
        )

    suffix = extension_for_kind(
        kind
    )
    detected_kind = (
        detect_download_kind(
            content,
            f"{stem}{suffix}",
            "",
        )
    )
    if detected_kind != kind:
        raise ValueError(
            "O formato detectado não corresponde "
            f"ao tipo esperado: {kind}."
        )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix=".dataset_stage_",
        dir=root,
    ) as temporary:
        stage_root = Path(
            temporary
        )
        staged_raw = (
            stage_root
            / f"{stem}{suffix}"
        )
        staged_raw.write_bytes(
            content
        )

        staged_extract: (
            Path
            | None
        ) = None
        extracted_names: list[
            str
        ] = []

        if kind == "zip":
            staged_extract = (
                stage_root
                / stem
            )
            staged_extract.mkdir(
                parents=True,
                exist_ok=True,
            )
            staged_paths = (
                _extract_csvs(
                    content,
                    staged_extract,
                )
            )
            extracted_names = [
                path.name
                for path
                in staged_paths
            ]

        backup_root = (
            stage_root
            / "backup"
        )
        backup_root.mkdir()

        backed_up: list[
            tuple[
                Path,
                Path,
            ]
        ] = []
        installed: list[
            Path
        ] = []

        try:
            for existing in (
                _dataset_artifact_candidates(
                    root,
                    stem,
                )
            ):
                if not existing.exists():
                    continue

                backup = (
                    backup_root
                    / existing.name
                )
                shutil.move(
                    str(existing),
                    str(backup),
                )
                backed_up.append(
                    (
                        existing,
                        backup,
                    )
                )

            raw_path = (
                root
                / staged_raw.name
            )
            shutil.move(
                str(staged_raw),
                str(raw_path),
            )
            installed.append(
                raw_path
            )

            extracted: list[
                Path
            ] = []
            if (
                staged_extract
                is not None
            ):
                extract_dir = (
                    root
                    / stem
                )
                shutil.move(
                    str(
                        staged_extract
                    ),
                    str(
                        extract_dir
                    ),
                )
                installed.append(
                    extract_dir
                )
                extracted = [
                    extract_dir
                    / name
                    for name
                    in extracted_names
                ]

            return (
                raw_path,
                extracted,
            )
        except Exception:
            for path in reversed(
                installed
            ):
                _remove_path(
                    path
                )

            for original, backup in reversed(
                backed_up
            ):
                if backup.exists():
                    shutil.move(
                        str(backup),
                        str(original),
                    )
            raise


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

        raw_path, extracted_paths = (
            _replace_dataset_artifacts(
                RAW_OPEN_DATA_DIR,
                stem,
                response.content,
                kind,
            )
        )
        extracted = [
            str(
                path.relative_to(
                    RAW_OPEN_DATA_DIR
                )
            )
            for path
            in extracted_paths
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
