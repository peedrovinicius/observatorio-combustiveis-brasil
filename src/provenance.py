from __future__ import annotations

import hashlib
import json
import re
from datetime import (
    datetime,
    timedelta,
)
from pathlib import Path

from .config import (
    ANP_HISTORICAL_PAGE,
    ANP_OPEN_DATA_PAGE,
)

MANIFEST_VERSION = 1
TRANSFORM_MANIFEST_VERSION = 1
STATION_TRANSFORM_MANIFEST_VERSION = 1

HISTORY_SCOPES = {
    "brasil",
    "regioes",
    "estados",
    "municipios_2026",
}

SHA256_PATTERN = re.compile(
    r"^[0-9a-f]{64}$"
)


def _load_manifest(
    path: Path,
) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(
            f"Manifesto de proveniência ausente: {path}"
        )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Manifesto de proveniência inválido: {path}"
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Manifesto de proveniência deve "
            "ser um objeto JSON."
        )
    if data.get(
        "manifest_version"
    ) != MANIFEST_VERSION:
        raise ValueError(
            "Versão de manifesto não suportada. "
            "Reexecute o downloader correspondente."
        )

    source = str(
        data.get(
            "source",
            "",
        )
    ).strip()
    source_page = str(
        data.get(
            "source_page",
            "",
        )
    ).strip()
    collected_at = str(
        data.get(
            "collected_at_utc",
            "",
        )
    ).strip()

    if not source:
        raise ValueError(
            "Manifesto de proveniência sem fonte."
        )
    if not source_page.startswith(
        "https://"
    ):
        raise ValueError(
            "Manifesto de proveniência sem "
            "página oficial HTTPS válida."
        )

    try:
        collected = datetime.fromisoformat(
            collected_at.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise ValueError(
            "Timestamp UTC inválido no manifesto."
        ) from exc

    if (
        collected.tzinfo is None
        or collected.utcoffset()
        != timedelta(0)
    ):
        raise ValueError(
            "Timestamp do manifesto deve "
            "estar em UTC."
        )

    files = data.get(
        "files"
    )
    if (
        not isinstance(
            files,
            list,
        )
        or not files
    ):
        raise ValueError(
            "Manifesto de proveniência não possui "
            "uma lista de arquivos válida."
        )
    if not all(
        isinstance(
            item,
            dict,
        )
        for item in files
    ):
        raise ValueError(
            "Registros do manifesto de proveniência "
            "devem ser objetos."
        )

    return data


def _sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()
    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )
            if not chunk:
                break
            digest.update(
                chunk
            )
    return digest.hexdigest()


def sha256_file(
    path: Path,
) -> str:
    return _sha256_file(
        path
    )


def _safe_relative_path(
    root: Path,
    value: object,
) -> tuple[
    Path,
    str,
]:
    text = str(
        value
    ).strip()
    relative = Path(
        text
    )
    if (
        not text
        or relative.is_absolute()
        or ".." in relative.parts
    ):
        raise ValueError(
            "Manifesto contém caminho inseguro: "
            f"{text or '<vazio>'}"
        )

    resolved_root = root.resolve()
    resolved = (
        root
        / relative
    ).resolve()
    try:
        resolved.relative_to(
            resolved_root
        )
    except ValueError as exc:
        raise ValueError(
            "Manifesto contém caminho fora "
            "da camada raw."
        ) from exc

    return (
        resolved,
        relative.as_posix(),
    )


def _verify_file_record(
    root: Path,
    relative_value: object,
    expected_bytes: object,
    expected_sha256: object,
) -> tuple[
    Path,
    str,
]:
    path, relative = (
        _safe_relative_path(
            root,
            relative_value,
        )
    )

    if not path.is_file():
        raise FileNotFoundError(
            "Arquivo manifestado ausente: "
            f"{relative}"
        )

    try:
        size = int(
            expected_bytes
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Tamanho inválido no manifesto: "
            f"{relative}"
        ) from exc

    if size < 0:
        raise ValueError(
            "Tamanho negativo no manifesto: "
            f"{relative}"
        )
    if (
        path.stat().st_size
        != size
    ):
        raise ValueError(
            "Tamanho divergente do manifesto: "
            f"{relative}"
        )

    digest = str(
        expected_sha256
    ).strip().casefold()
    if not SHA256_PATTERN.fullmatch(
        digest
    ):
        raise ValueError(
            "SHA-256 inválido no manifesto: "
            f"{relative}"
        )
    if _sha256_file(
        path
    ) != digest:
        raise ValueError(
            "SHA-256 divergente do manifesto: "
            f"{relative}"
        )

    return (
        path,
        relative,
    )


def verify_history_provenance(
    root: Path,
) -> dict[str, object]:
    manifest = _load_manifest(
        root
        / "history_manifest.json"
    )
    records = manifest["files"]

    if (
        manifest[
            "source_page"
        ]
        != ANP_HISTORICAL_PAGE
    ):
        raise ValueError(
            "Manifesto histórico aponta para "
            "página de origem inesperada."
        )

    scopes: set[str] = set()
    filenames: set[str] = set()

    for item in records:
        scope = str(
            item.get(
                "scope",
                "",
            )
        ).strip()
        filename = str(
            item.get(
                "filename",
                "",
            )
        ).strip()

        if (
            item.get(
                "collected_at_utc"
            )
            != manifest[
                "collected_at_utc"
            ]
        ):
            raise ValueError(
                "Timestamp do arquivo histórico "
                "diverge do manifesto."
            )
        if (
            item.get(
                "source_page"
            )
            != manifest[
                "source_page"
            ]
        ):
            raise ValueError(
                "Página de origem do arquivo "
                "histórico diverge do manifesto."
            )
        for field in (
            "discovered_url",
            "final_url",
        ):
            if not str(
                item.get(
                    field,
                    "",
                )
            ).startswith(
                "https://"
            ):
                raise ValueError(
                    "URL histórica ausente ou "
                    f"inválida: {field}."
                )

        if (
            not scope
            or scope in scopes
        ):
            raise ValueError(
                "Escopo histórico ausente "
                "ou duplicado no manifesto."
            )
        if (
            not filename
            or filename in filenames
        ):
            raise ValueError(
                "Arquivo histórico ausente "
                "ou duplicado no manifesto."
            )
        if (
            item.get(
                "detected_format"
            )
            != "xlsx"
        ):
            raise ValueError(
                "Formato histórico incompatível "
                f"no manifesto: {filename}"
            )
        if not filename.startswith(
            f"historico_semanal_{scope}__"
        ):
            raise ValueError(
                "Nome do arquivo histórico não "
                "corresponde ao escopo do manifesto."
            )

        path, relative = (
            _verify_file_record(
                root,
                filename,
                item.get(
                    "bytes"
                ),
                item.get(
                    "sha256"
                ),
            )
        )
        if (
            path.suffix.casefold()
            != ".xlsx"
            or Path(
                relative
            ).name
            != relative
        ):
            raise ValueError(
                "Arquivo histórico manifestado "
                "deve ser XLSX no diretório raw."
            )

        scopes.add(
            scope
        )
        filenames.add(
            filename
        )

    if scopes != HISTORY_SCOPES:
        missing = sorted(
            HISTORY_SCOPES
            - scopes
        )
        extra = sorted(
            scopes
            - HISTORY_SCOPES
        )
        raise ValueError(
            "Cobertura histórica do manifesto "
            f"inválida. Ausentes={missing}; extras={extra}."
        )

    actual = {
        path.name
        for path in root.glob(
            "historico_semanal_*__*"
        )
        if (
            path.is_file()
            and path.suffix.casefold()
            == ".xlsx"
        )
    }
    if actual != filenames:
        raise ValueError(
            "Arquivos históricos locais não "
            "correspondem exatamente ao manifesto."
        )

    return manifest


def verify_open_data_provenance(
    root: Path,
) -> dict[str, object]:
    manifest = _load_manifest(
        root
        / "manifest.json"
    )
    records = manifest["files"]

    if (
        manifest[
            "source_page"
        ]
        != ANP_OPEN_DATA_PAGE
    ):
        raise ValueError(
            "Manifesto por posto aponta para "
            "página de origem inesperada."
        )

    datasets: set[str] = set()
    raw_files: set[str] = set()
    expected_csvs: set[str] = set()

    for item in records:
        dataset = str(
            item.get(
                "dataset",
                "",
            )
        ).strip()
        filename = str(
            item.get(
                "filename",
                "",
            )
        ).strip()
        kind = str(
            item.get(
                "detected_format",
                "",
            )
        ).strip().casefold()

        if (
            item.get(
                "collected_at_utc"
            )
            != manifest[
                "collected_at_utc"
            ]
        ):
            raise ValueError(
                "Timestamp do arquivo por posto "
                "diverge do manifesto."
            )
        for field in (
            "url",
            "final_url",
        ):
            if not str(
                item.get(
                    field,
                    "",
                )
            ).startswith(
                "https://"
            ):
                raise ValueError(
                    "URL por posto ausente ou "
                    f"inválida: {field}."
                )

        if (
            not dataset
            or dataset in datasets
        ):
            raise ValueError(
                "Dataset lógico ausente ou "
                "duplicado no manifesto por posto."
            )
        if (
            not filename
            or filename in raw_files
        ):
            raise ValueError(
                "Arquivo raw ausente ou duplicado "
                "no manifesto por posto."
            )
        if kind not in {
            "csv",
            "zip",
        }:
            raise ValueError(
                "Formato raw por posto inválido "
                f"no manifesto: {kind or 'n/d'}."
            )

        _, raw_relative = (
            _verify_file_record(
                root,
                filename,
                item.get(
                    "bytes"
                ),
                item.get(
                    "sha256"
                ),
            )
        )
        raw_path = Path(
            raw_relative
        )
        if (
            raw_path.name
            != raw_relative
        ):
            raise ValueError(
                "Arquivo raw por posto deve "
                "estar na raiz da camada."
            )
        if (
            raw_path.stem
            != dataset
        ):
            raise ValueError(
                "Nome do arquivo raw não "
                "corresponde ao dataset lógico."
            )
        expected_suffix = (
            ".csv"
            if kind == "csv"
            else ".zip"
        )
        if (
            raw_path.suffix.casefold()
            != expected_suffix
        ):
            raise ValueError(
                "Extensão do arquivo raw não "
                "corresponde ao formato manifestado."
            )

        extracted = item.get(
            "extracted_files"
        )
        if not isinstance(
            extracted,
            list,
        ):
            raise ValueError(
                "Manifesto por posto não contém "
                "hashes dos CSVs extraídos. "
                "Reexecute o downloader."
            )

        extracted_paths: list[
            str
        ] = []
        extracted_seen: set[
            str
        ] = set()
        for extracted_item in extracted:
            if not isinstance(
                extracted_item,
                dict,
            ):
                raise ValueError(
                    "Registro de CSV extraído "
                    "inválido no manifesto."
                )
            _, extracted_relative = (
                _verify_file_record(
                    root,
                    extracted_item.get(
                        "path"
                    ),
                    extracted_item.get(
                        "bytes"
                    ),
                    extracted_item.get(
                        "sha256"
                    ),
                )
            )
            if not extracted_relative.casefold().endswith(
                ".csv"
            ):
                raise ValueError(
                    "Arquivo extraído manifestado "
                    "não é CSV."
                )
            if (
                Path(
                    extracted_relative
                ).parts[0]
                != dataset
            ):
                raise ValueError(
                    "CSV extraído não pertence "
                    "ao diretório do dataset lógico."
                )
            if (
                extracted_relative
                in extracted_seen
            ):
                raise ValueError(
                    "CSV extraído duplicado "
                    "no manifesto."
                )
            extracted_seen.add(
                extracted_relative
            )
            extracted_paths.append(
                extracted_relative
            )

        legacy_paths = item.get(
            "extracted_csvs"
        )
        if (
            not isinstance(
                legacy_paths,
                list,
            )
            or sorted(
                str(value).replace(
                    "\\",
                    "/",
                )
                for value in legacy_paths
            )
            != sorted(
                extracted_paths
            )
        ):
            raise ValueError(
                "Lista de CSVs extraídos diverge "
                "dos registros com hash."
            )

        if kind == "csv":
            if extracted_paths:
                raise ValueError(
                    "Dataset CSV direto não deve "
                    "ter arquivos extraídos."
                )
            expected_csvs.add(
                raw_relative
            )
        else:
            if not extracted_paths:
                raise ValueError(
                    "Dataset ZIP não possui CSVs "
                    "extraídos manifestados."
                )
            expected_csvs.update(
                extracted_paths
            )

        datasets.add(
            dataset
        )
        raw_files.add(
            filename
        )

    missing_families: list[str] = []
    if (
        "automotivos_2026_s1"
        not in datasets
    ):
        missing_families.append(
            "combustíveis automotivos do 1º semestre"
        )
    if not any(
        name.startswith(
            "diesel_gnv_"
        )
        for name in datasets
    ):
        missing_families.append(
            "diesel/GNV"
        )
    if not any(
        name.startswith(
            "etanol_gasolina_"
        )
        for name in datasets
    ):
        missing_families.append(
            "etanol/gasolina"
        )

    if missing_families:
        raise ValueError(
            "Cobertura do manifesto por posto "
            "incompleta. Famílias ausentes: "
            + ", ".join(
                missing_families
            )
            + "."
        )

    actual_raw_files = {
        path.name
        for path in root.iterdir()
        if (
            path.is_file()
            and path.suffix.casefold()
            in {
                ".csv",
                ".zip",
                ".xlsx",
            }
        )
    }
    if (
        actual_raw_files
        != raw_files
    ):
        raise ValueError(
            "Arquivos raw locais por posto não "
            "correspondem exatamente ao manifesto."
        )

    actual_csvs = {
        path.relative_to(
            root
        ).as_posix()
        for path in root.rglob(
            "*.csv"
        )
        if path.is_file()
    }
    if actual_csvs != expected_csvs:
        raise ValueError(
            "CSVs locais por posto não "
            "correspondem exatamente ao manifesto."
        )

    return manifest



def verified_history_files(
    root: Path,
) -> list[Path]:
    manifest = (
        verify_history_provenance(
            root
        )
    )
    return sorted(
        root
        / str(
            item["filename"]
        )
        for item in manifest[
            "files"
        ]
    )



def verify_history_transform_provenance(
    processed_root: Path,
    raw_root: Path,
) -> list[Path]:
    raw_manifest = (
        raw_root
        / "history_manifest.json"
    )
    verify_history_provenance(
        raw_root
    )

    manifest_path = (
        processed_root
        / "history_transform_manifest.json"
    )
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Manifesto da transformação histórica "
            f"ausente: {manifest_path}"
        )

    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Manifesto da transformação histórica "
            "não é JSON válido."
        ) from exc

    if not isinstance(
        manifest,
        dict,
    ):
        raise ValueError(
            "Manifesto da transformação histórica "
            "deve ser um objeto JSON."
        )
    if (
        manifest.get(
            "manifest_version"
        )
        != TRANSFORM_MANIFEST_VERSION
    ):
        raise ValueError(
            "Versão do manifesto da transformação "
            "histórica não suportada."
        )

    source_digest = str(
        manifest.get(
            "source_manifest_sha256",
            "",
        )
    ).strip().casefold()
    if not SHA256_PATTERN.fullmatch(
        source_digest
    ):
        raise ValueError(
            "SHA-256 do manifesto raw é inválido "
            "no manifesto de transformação."
        )
    if (
        source_digest
        != _sha256_file(
            raw_manifest
        )
    ):
        raise ValueError(
            "Manifesto raw atual diverge daquele "
            "usado na transformação histórica."
        )

    raw_data = json.loads(
        raw_manifest.read_text(
            encoding="utf-8",
        )
    )
    raw_by_file = {
        str(
            item["filename"]
        ): item
        for item in raw_data[
            "files"
        ]
    }

    files = manifest.get(
        "files"
    )
    if (
        not isinstance(
            files,
            list,
        )
        or not files
    ):
        raise ValueError(
            "Manifesto da transformação histórica "
            "não possui lista de arquivos válida."
        )

    filenames: set[str] = set()
    scopes: set[str] = set()
    verified: list[Path] = []

    for item in files:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Registro inválido no manifesto "
                "da transformação histórica."
            )

        filename = str(
            item.get(
                "filename",
                "",
            )
        ).strip()
        source_file = str(
            item.get(
                "source_file",
                "",
            )
        ).strip()
        source_sheet = str(
            item.get(
                "source_sheet",
                "",
            )
        ).strip()
        scope = str(
            item.get(
                "scope",
                "",
            )
        ).strip()

        if (
            not filename
            or filename in filenames
        ):
            raise ValueError(
                "Arquivo processado ausente ou duplicado "
                "no manifesto de transformação."
            )
        if (
            Path(
                filename
            ).name
            != filename
            or not filename.casefold().endswith(
                ".csv"
            )
        ):
            raise ValueError(
                "Nome de CSV processado inválido "
                "no manifesto de transformação."
            )
        if (
            scope
            not in HISTORY_SCOPES
            or not filename.startswith(
                f"historico_semanal_{scope}__"
            )
        ):
            raise ValueError(
                "Escopo do CSV processado é inválido "
                "ou incompatível com o nome."
            )
        if not source_sheet:
            raise ValueError(
                "Aba de origem ausente no manifesto "
                "de transformação."
            )

        raw_record = raw_by_file.get(
            source_file
        )
        if raw_record is None:
            raise ValueError(
                "Arquivo raw de origem não existe "
                "no manifesto histórico atual."
            )
        if (
            raw_record.get(
                "scope"
            )
            != scope
        ):
            raise ValueError(
                "Escopo do CSV processado diverge "
                "do arquivo raw de origem."
            )

        path, relative = (
            _verify_file_record(
                processed_root,
                filename,
                item.get(
                    "bytes"
                ),
                item.get(
                    "sha256"
                ),
            )
        )
        if (
            relative
            != filename
        ):
            raise ValueError(
                "CSV processado deve estar na raiz "
                "de data/processed."
            )

        rows = item.get(
            "rows"
        )
        columns = item.get(
            "columns"
        )
        if (
            not isinstance(
                rows,
                int,
            )
            or rows < 0
            or not isinstance(
                columns,
                int,
            )
            or columns <= 0
        ):
            raise ValueError(
                "Dimensões inválidas no manifesto "
                f"de transformação: {filename}."
            )

        filenames.add(
            filename
        )
        scopes.add(
            scope
        )
        verified.append(
            path
        )

    if scopes != HISTORY_SCOPES:
        missing = sorted(
            HISTORY_SCOPES
            - scopes
        )
        extra = sorted(
            scopes
            - HISTORY_SCOPES
        )
        raise ValueError(
            "Cobertura do manifesto de transformação "
            f"inválida. Ausentes={missing}; extras={extra}."
        )

    actual = {
        path.name
        for path in processed_root.glob(
            "historico_semanal_*__*.csv"
        )
        if path.is_file()
    }
    if actual != filenames:
        raise ValueError(
            "CSVs históricos processados não "
            "correspondem exatamente ao manifesto "
            "de transformação."
        )

    return sorted(
        verified
    )



def verify_station_transform_provenance(
    processed_root: Path,
    raw_root: Path,
    reports_root: Path,
) -> dict[str, object]:
    raw_manifest = (
        raw_root
        / "manifest.json"
    )
    verify_open_data_provenance(
        raw_root
    )

    manifest_path = (
        processed_root
        / "station_transform_manifest.json"
    )
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Manifesto da transformação por posto "
            f"ausente: {manifest_path}"
        )

    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Manifesto da transformação por posto "
            "não é JSON válido."
        ) from exc

    if not isinstance(
        manifest,
        dict,
    ):
        raise ValueError(
            "Manifesto da transformação por posto "
            "deve ser um objeto JSON."
        )
    if (
        manifest.get(
            "manifest_version"
        )
        != STATION_TRANSFORM_MANIFEST_VERSION
    ):
        raise ValueError(
            "Versão do manifesto da transformação "
            "por posto não suportada."
        )

    source_digest = str(
        manifest.get(
            "source_manifest_sha256",
            "",
        )
    ).strip().casefold()
    if not SHA256_PATTERN.fullmatch(
        source_digest
    ):
        raise ValueError(
            "SHA-256 do manifesto raw por posto "
            "é inválido."
        )
    if (
        source_digest
        != _sha256_file(
            raw_manifest
        )
    ):
        raise ValueError(
            "Manifesto raw por posto atual diverge "
            "daquele usado na consolidação."
        )

    files = manifest.get(
        "files"
    )
    if (
        not isinstance(
            files,
            list,
        )
        or len(
            files
        )
        != 2
    ):
        raise ValueError(
            "Manifesto da transformação por posto "
            "deve registrar exatamente base e auditoria."
        )

    records: dict[
        str,
        dict[str, object],
    ] = {}
    for item in files:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Registro inválido no manifesto "
                "da transformação por posto."
            )
        role = str(
            item.get(
                "role",
                "",
            )
        ).strip()
        if (
            not role
            or role in records
        ):
            raise ValueError(
                "Papel ausente ou duplicado no "
                "manifesto da transformação por posto."
            )
        records[
            role
        ] = item

    expected_roles = {
        "station_data",
        "ingestion_audit",
    }
    if set(
        records
    ) != expected_roles:
        raise ValueError(
            "Manifesto da transformação por posto "
            "não contém os artefatos esperados."
        )

    data_item = records[
        "station_data"
    ]
    data_path, relative = (
        _verify_file_record(
            processed_root,
            data_item.get(
                "filename"
            ),
            data_item.get(
                "bytes"
            ),
            data_item.get(
                "sha256"
            ),
        )
    )
    if (
        relative
        != "precos_postos_2026.csv"
    ):
        raise ValueError(
            "Arquivo de dados por posto inesperado "
            "no manifesto de transformação."
        )

    rows = data_item.get(
        "rows"
    )
    columns = data_item.get(
        "columns"
    )
    if (
        not isinstance(
            rows,
            int,
        )
        or rows < 0
        or not isinstance(
            columns,
            int,
        )
        or columns <= 0
    ):
        raise ValueError(
            "Dimensões inválidas para a base "
            "por posto no manifesto."
        )

    audit_item = records[
        "ingestion_audit"
    ]
    audit_path, audit_relative = (
        _verify_file_record(
            reports_root,
            audit_item.get(
                "filename"
            ),
            audit_item.get(
                "bytes"
            ),
            audit_item.get(
                "sha256"
            ),
        )
    )
    if (
        audit_relative
        != "station_ingestion_audit_2026.json"
    ):
        raise ValueError(
            "Arquivo de auditoria por posto inesperado "
            "no manifesto de transformação."
        )

    try:
        audit = json.loads(
            audit_path.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Auditoria de ingestão por posto "
            "não é JSON válido."
        ) from exc

    if not isinstance(
        audit,
        dict,
    ):
        raise ValueError(
            "Auditoria de ingestão por posto "
            "deve ser um objeto JSON."
        )
    if (
        audit.get(
            "linhas_finais"
        )
        != rows
    ):
        raise ValueError(
            "Quantidade de linhas da auditoria por posto "
            "diverge do manifesto de transformação."
        )

    return {
        "manifest": manifest,
        "station_data": data_path,
        "ingestion_audit": audit_path,
    }
