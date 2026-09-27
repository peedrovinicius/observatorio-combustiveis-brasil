from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd

from .atomic_outputs import (
    replace_staged_files,
)
from .config import (
    PROCESSED_DIR,
    RAW_OPEN_DATA_DIR,
    REPORTS_DIR,
)

STATION_OUTPUT = PROCESSED_DIR / "precos_postos_2026.csv"
STATION_MODEL_DIR = PROCESSED_DIR / "model_postos"
STATION_INGESTION_AUDIT = (
    REPORTS_DIR / "station_ingestion_audit_2026.json"
)

COLUMN_ALIASES = {
    "regiao_sigla": "regiao",
    "estado_sigla": "uf",
    "municipio": "municipio",
    "revenda": "revenda",
    "cnpj_da_revenda": "cnpj_revenda",
    "nome_da_rua": "logradouro",
    "numero_rua": "numero",
    "complemento": "complemento",
    "bairro": "bairro",
    "cep": "cep",
    "produto": "produto",
    "data_da_coleta": "data_coleta",
    "valor_de_venda": "preco_revenda",
    "valor_de_compra": "preco_compra",
    "unidade_de_medida": "unidade_medida",
    "bandeira": "bandeira",
}

REQUIRED_SOURCE_COLUMNS = {
    "uf",
    "municipio",
    "produto",
    "data_coleta",
    "preco_revenda",
    "unidade_medida",
}

STATION_MODEL_REQUIRED_COLUMNS = {
    "data_coleta",
    "produto",
    "unidade_medida",
    "preco_revenda",
    "fonte_arquivo",
}

BUSINESS_KEY = [
    "data_coleta",
    "_posto_identidade",
    "produto",
    "unidade_medida",
]

FALLBACK_STATION_COLUMNS = [
    "uf",
    "municipio",
    "revenda",
    "logradouro",
    "numero",
]


def _normalize_name(value: object) -> str:
    text = unicodedata.normalize(
        "NFKD",
        str(value).strip(),
    )
    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )
    text = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        text,
    ).strip("_").lower()
    return COLUMN_ALIASES.get(text, text)


def _parse_decimal(series: pd.Series) -> pd.Series:
    def parse(value: object) -> float | None:
        if pd.isna(value):
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = (
            str(value)
            .strip()
            .replace("R$", "")
            .replace(" ", "")
        )
        if not text:
            return None
        if "," in text:
            text = (
                text
                .replace(".", "")
                .replace(",", ".")
            )

        try:
            return float(text)
        except ValueError:
            return None

    return series.map(parse)


def normalize_cnpj(
    series: pd.Series,
) -> pd.Series:
    normalized = (
        series.astype("string")
        .str.upper()
        .str.replace(
            r"[^0-9A-Z]",
            "",
            regex=True,
        )
        .str.strip()
        .replace("", pd.NA)
    )
    valid = normalized.str.fullmatch(
        r"[0-9A-Z]{12}[0-9]{2}",
        na=False,
    )
    return normalized.where(
        valid,
        pd.NA,
    )


def _nonblank_station_field(
    frame: pd.DataFrame,
    column: str,
) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(
            False,
            index=frame.index,
            dtype="boolean",
        )
    return (
        frame[column]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
        .notna()
    )


def station_identity_issue_masks(
    frame: pd.DataFrame,
) -> dict[str, pd.Series]:
    if "cnpj_revenda" in frame.columns:
        raw_cnpj = (
            frame["cnpj_revenda"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        normalized_cnpj = (
            normalize_cnpj(
                frame["cnpj_revenda"]
            )
        )
    else:
        raw_cnpj = pd.Series(
            pd.NA,
            index=frame.index,
            dtype="string",
        )
        normalized_cnpj = pd.Series(
            pd.NA,
            index=frame.index,
            dtype="string",
        )

    needs_fallback = (
        normalized_cnpj.isna()
    )
    has_uf = (
        _nonblank_station_field(
            frame,
            "uf",
        )
    )
    has_municipio = (
        _nonblank_station_field(
            frame,
            "municipio",
        )
    )
    has_revenda = (
        _nonblank_station_field(
            frame,
            "revenda",
        )
    )
    has_logradouro = (
        _nonblank_station_field(
            frame,
            "logradouro",
        )
    )
    has_numero = (
        _nonblank_station_field(
            frame,
            "numero",
        )
    )

    return {
        "invalid_cnpj": (
            raw_cnpj.notna()
            & normalized_cnpj.isna()
        ),
        "fallback_incomplete": (
            needs_fallback
            & ~(
                has_uf
                & has_municipio
                & has_revenda
                & has_logradouro
                & has_numero
            )
        ),
        "fallback_missing_uf": (
            needs_fallback
            & ~has_uf
        ),
        "fallback_missing_municipio": (
            needs_fallback
            & ~has_municipio
        ),
        "fallback_missing_revenda": (
            needs_fallback
            & ~has_revenda
        ),
        "fallback_missing_logradouro": (
            needs_fallback
            & ~has_logradouro
        ),
        "fallback_missing_numero": (
            needs_fallback
            & ~has_numero
        ),
    }


def station_identity(
    frame: pd.DataFrame,
) -> pd.Series:
    index = frame.index

    if "cnpj_revenda" in frame.columns:
        cnpj = normalize_cnpj(
            frame["cnpj_revenda"]
        )
    else:
        cnpj = pd.Series(
            pd.NA,
            index=index,
            dtype="string",
        )

    fallback_parts: list[pd.Series] = []
    for column in FALLBACK_STATION_COLUMNS:
        if column in frame.columns:
            values = (
                frame[column]
                .astype("string")
                .fillna("")
                .str.strip()
                .str.upper()
            )
        else:
            values = pd.Series(
                "",
                index=index,
                dtype="string",
            )
        fallback_parts.append(values)

    fallback = fallback_parts[0]
    for part in fallback_parts[1:]:
        fallback = fallback.str.cat(
            part,
            sep="|",
        )

    identity = pd.Series(
        "cnpj:" + cnpj,
        index=index,
        dtype="string",
    )
    identity = identity.mask(
        cnpj.isna(),
        "fallback:" + fallback,
    )
    return identity


def station_key(
    frame: pd.DataFrame,
) -> pd.Series:
    identity = station_identity(
        frame
    )
    return identity.map(
        lambda value: hashlib.sha256(
            str(value).encode(
                "utf-8"
            )
        ).hexdigest()
    ).astype("string")


def source_priority(source: object) -> int:
    text = str(source).casefold()
    if "ultimas_4_semanas" in text:
        return 20
    if re.search(
        r"(julho|agosto|setembro|outubro|novembro|dezembro)_2026",
        text,
    ):
        return 10
    if (
        "2026_s1" in text
        or "2026-01" in text
    ):
        return 5
    return 0


def source_reference(
    path: Path,
    source_root: Path | None = None,
) -> str:
    if source_root is not None:
        try:
            return path.relative_to(
                source_root
            ).as_posix()
        except ValueError:
            pass
    return path.name


def deduplicate_station_rows(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    working = frame.copy()
    working["_posto_identidade"] = (
        station_identity(working)
    )

    if "fonte_arquivo" in working.columns:
        working["_source_priority"] = (
            working["fonte_arquivo"]
            .map(source_priority)
            .astype("Int64")
        )
    else:
        working["_source_priority"] = 0

    working["_source_order"] = range(
        len(working)
    )
    working = working.sort_values(
        [
            "_source_priority",
            "_source_order",
        ],
        kind="stable",
    )

    keys = [
        key
        for key in BUSINESS_KEY
        if key in working.columns
    ]
    issues = station_identity_issue_masks(
        working
    )
    reliable_identity = ~issues[
        "fallback_incomplete"
    ]

    reliable = (
        working.loc[
            reliable_identity
        ]
        .drop_duplicates(
            subset=keys,
            keep="last",
        )
    )
    unreliable = working.loc[
        ~reliable_identity
    ]
    working = pd.concat(
        [
            reliable,
            unreliable,
        ],
        ignore_index=False,
    ).sort_values(
        "_source_order",
        kind="stable",
    )

    return working.drop(
        columns=[
            "_posto_identidade",
            "_source_priority",
            "_source_order",
        ],
        errors="ignore",
    )


def _read_csv(path: Path) -> pd.DataFrame:
    attempts = [
        {
            "sep": ";",
            "encoding": "utf-8-sig",
        },
        {
            "sep": ";",
            "encoding": "latin-1",
        },
        {
            "sep": ",",
            "encoding": "utf-8-sig",
        },
    ]

    for options in attempts:
        try:
            frame = pd.read_csv(
                path,
                low_memory=False,
                dtype="string",
                **options,
            )
            if frame.shape[1] >= 10:
                return frame
        except UnicodeDecodeError:
            continue

    raise ValueError(
        f"Não foi possível interpretar "
        f"{path.name} como CSV da ANP."
    )


def prepare_station_file(
    path: Path,
    source_root: Path | None = None,
) -> pd.DataFrame:
    frame = _read_csv(path)
    frame.columns = [
        _normalize_name(column)
        for column in frame.columns
    ]

    missing = (
        REQUIRED_SOURCE_COLUMNS
        - set(frame.columns)
    )
    if missing:
        raise ValueError(
            f"{path.name}: colunas obrigatórias "
            f"ausentes: {sorted(missing)}"
        )

    frame["data_coleta"] = pd.to_datetime(
        frame["data_coleta"],
        errors="coerce",
        dayfirst=True,
    )
    frame["preco_revenda"] = _parse_decimal(
        frame["preco_revenda"]
    )

    if "preco_compra" in frame.columns:
        frame["preco_compra"] = (
            _parse_decimal(
                frame["preco_compra"]
            )
        )

    for column in (
        "regiao",
        "uf",
        "municipio",
        "revenda",
        "cnpj_revenda",
        "produto",
        "unidade_medida",
        "bandeira",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
    ):
        if column in frame.columns:
            frame[column] = (
                frame[column]
                .astype("string")
                .str.strip()
            )

    frame["fonte_arquivo"] = (
        source_reference(
            path,
            source_root,
        )
    )
    return frame


def audit_prepared_station_frame(
    frame: pd.DataFrame,
    source_name: str,
) -> dict[str, object]:
    dates = frame["data_coleta"]
    prices = frame["preco_revenda"]

    valid_date = dates.notna()
    in_2026 = (
        valid_date
        & dates.dt.year.eq(2026)
    )
    valid_price = prices.notna()
    positive_price = (
        valid_price
        & prices.gt(0)
    )
    eligible = (
        in_2026
        & positive_price
    )

    return {
        "fonte_arquivo": source_name,
        "linhas_origem": int(len(frame)),
        "datas_invalidas": int(
            (~valid_date).sum()
        ),
        "linhas_fora_2026": int(
            (
                valid_date
                & ~dates.dt.year.eq(2026)
            ).sum()
        ),
        "precos_invalidos": int(
            (~valid_price).sum()
        ),
        "precos_nao_positivos": int(
            (
                valid_price
                & ~prices.gt(0)
            ).sum()
        ),
        "linhas_elegiveis_antes_deduplicacao": int(
            eligible.sum()
        ),
        "linhas_excluidas_antes_deduplicacao": int(
            len(frame) - eligible.sum()
        ),
    }


def clean_prepared_station_frame(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    mask = (
        frame["data_coleta"].notna()
        & frame["data_coleta"].dt.year.eq(2026)
        & frame["preco_revenda"].notna()
        & frame["preco_revenda"].gt(0)
    )
    return frame.loc[mask].copy()


def transform_station_file(
    path: Path,
) -> pd.DataFrame:
    prepared = prepare_station_file(path)
    return clean_prepared_station_frame(
        prepared
    )


def _overlap_audit(
    frame: pd.DataFrame,
) -> dict[str, int]:
    if frame.empty:
        return {
            "grupos_sobrepostos": 0,
            "grupos_com_preco_divergente": 0,
        }

    working = frame.copy()
    issues = station_identity_issue_masks(
        working
    )
    working = working.loc[
        ~issues[
            "fallback_incomplete"
        ]
    ].copy()
    if working.empty:
        return {
            "grupos_sobrepostos": 0,
            "grupos_com_preco_divergente": 0,
        }

    working["_posto_identidade"] = (
        station_identity(working)
    )
    keys = [
        key
        for key in BUSINESS_KEY
        if key in working.columns
    ]

    grouped = (
        working.groupby(
            keys,
            dropna=False,
        )["preco_revenda"]
        .agg(
            linhas="size",
            precos_distintos="nunique",
        )
        .reset_index(drop=True)
    )

    return {
        "grupos_sobrepostos": int(
            grouped["linhas"].gt(1).sum()
        ),
        "grupos_com_preco_divergente": int(
            (
                grouped["linhas"].gt(1)
                & grouped[
                    "precos_distintos"
                ].gt(1)
            ).sum()
        ),
    }


def consolidate_station_data_with_audit(
    directory: Path = RAW_OPEN_DATA_DIR,
) -> tuple[pd.DataFrame, dict[str, object]]:
    files = sorted(
        directory.rglob("*.csv")
    )
    if not files:
        raise RuntimeError(
            "Nenhum CSV de preços por posto encontrado."
        )

    frames: list[pd.DataFrame] = []
    file_audits: list[
        dict[str, object]
    ] = []

    for path in files:
        prepared = prepare_station_file(
            path,
            source_root=directory,
        )
        source_name = str(
            prepared[
                "fonte_arquivo"
            ].iloc[0]
        )
        file_audits.append(
            audit_prepared_station_frame(
                prepared,
                source_name,
            )
        )
        frames.append(
            clean_prepared_station_frame(
                prepared
            )
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )
    rows_before_dedup = len(combined)
    identity_issues = (
        station_identity_issue_masks(
            combined
        )
    )
    identity_audit = {
        "cnpjs_com_formato_invalido": int(
            identity_issues[
                "invalid_cnpj"
            ].sum()
        ),
        "fallbacks_incompletos": int(
            identity_issues[
                "fallback_incomplete"
            ].sum()
        ),
        "fallbacks_sem_uf": int(
            identity_issues[
                "fallback_missing_uf"
            ].sum()
        ),
        "fallbacks_sem_municipio": int(
            identity_issues[
                "fallback_missing_municipio"
            ].sum()
        ),
        "fallbacks_sem_revenda": int(
            identity_issues[
                "fallback_missing_revenda"
            ].sum()
        ),
        "fallbacks_sem_logradouro": int(
            identity_issues[
                "fallback_missing_logradouro"
            ].sum()
        ),
        "fallbacks_sem_numero": int(
            identity_issues[
                "fallback_missing_numero"
            ].sum()
        ),
    }
    overlap = _overlap_audit(
        combined
    )

    combined = deduplicate_station_rows(
        combined
    )

    sort_candidates = [
        "data_coleta",
        "uf",
        "municipio",
        "produto",
        "cnpj_revenda",
        "revenda",
    ]
    sort_columns = [
        column
        for column in sort_candidates
        if column in combined.columns
    ]

    combined = (
        combined.sort_values(
            sort_columns,
            kind="stable",
            na_position="last",
        )
        .reset_index(drop=True)
    )

    audit = {
        "arquivos_processados": len(files),
        "linhas_origem": int(
            sum(
                item["linhas_origem"]
                for item in file_audits
            )
        ),
        "linhas_elegiveis_antes_deduplicacao": int(
            rows_before_dedup
        ),
        "linhas_removidas_por_sobreposicao": int(
            rows_before_dedup
            - len(combined)
        ),
        **overlap,
        **identity_audit,
        "linhas_finais": int(
            len(combined)
        ),
        "arquivos": file_audits,
    }

    invalid_total = sum(
        int(item["datas_invalidas"])
        + int(item["precos_invalidos"])
        + int(
            item["precos_nao_positivos"]
        )
        for item in file_audits
    )
    identity_issue_total = (
        identity_audit[
            "cnpjs_com_formato_invalido"
        ]
        + identity_audit[
            "fallbacks_incompletos"
        ]
    )
    audit["status"] = (
        "passed"
        if (
            invalid_total == 0
            and identity_issue_total == 0
        )
        else "review"
    )

    return combined, audit


def consolidate_station_data(
    directory: Path = RAW_OPEN_DATA_DIR,
) -> pd.DataFrame:
    frame, _ = (
        consolidate_station_data_with_audit(
            directory
        )
    )
    return frame


def build_station_star_schema(
    frame: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    missing = (
        STATION_MODEL_REQUIRED_COLUMNS
        - set(frame.columns)
    )
    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes "
            "para o modelo por posto: "
            + ", ".join(
                sorted(missing)
            )
        )

    working = frame.copy()

    dim_data = pd.DataFrame(
        {
            "data_coleta": sorted(
                working[
                    "data_coleta"
                ]
                .dropna()
                .unique()
            )
        }
    )
    dim_data.insert(
        0,
        "data_coleta_id",
        range(
            1,
            len(dim_data) + 1,
        ),
    )
    date_values = pd.to_datetime(
        dim_data["data_coleta"]
    )
    dim_data["ano"] = (
        date_values.dt.year
    )
    dim_data["mes"] = (
        date_values.dt.month
    )
    dim_data["semana_iso"] = (
        date_values
        .dt.isocalendar()
        .week
        .astype("Int64")
    )

    dim_produto = (
        working[
            [
                "produto",
                "unidade_medida",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "produto",
                "unidade_medida",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )
    dim_produto.insert(
        0,
        "produto_posto_id",
        range(
            1,
            len(dim_produto) + 1,
        ),
    )

    posto_cols = [
        column
        for column in [
            "cnpj_revenda",
            "revenda",
            "bandeira",
            "regiao",
            "uf",
            "municipio",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cep",
        ]
        if column in working.columns
    ]

    working["_posto_identidade"] = (
        station_identity(
            working
        )
    )
    working["_posto_chave"] = (
        station_key(
            working
        )
    )
    if "fonte_arquivo" in working.columns:
        working["_source_priority"] = (
            working["fonte_arquivo"]
            .map(source_priority)
            .astype("Int64")
        )
    else:
        working["_source_priority"] = 0

    working["_source_order"] = range(
        len(working)
    )
    latest_station = (
        working.sort_values(
            [
                "data_coleta",
                "_source_priority",
                "_source_order",
            ],
            kind="stable",
        )
        .drop_duplicates(
            subset=[
                "_posto_identidade"
            ],
            keep="last",
        )
        .copy()
    )

    dim_posto = (
        latest_station[
            [
                "_posto_identidade",
                "_posto_chave",
                *posto_cols,
            ]
        ]
        .sort_values(
            "_posto_identidade",
            kind="stable",
        )
        .reset_index(drop=True)
    )
    dim_posto.insert(
        0,
        "posto_id",
        range(
            1,
            len(dim_posto) + 1,
        ),
    )

    posto_lookup = dim_posto[
        [
            "_posto_identidade",
            "posto_id",
        ]
    ].copy()

    dim_posto = (
        dim_posto.drop(
            columns=[
                "_posto_identidade"
            ]
        )
        .rename(
            columns={
                "_posto_chave": (
                    "posto_chave"
                )
            }
        )
    )

    fact = working.merge(
        dim_data,
        on="data_coleta",
        how="left",
        validate="many_to_one",
    )
    fact = fact.merge(
        dim_produto,
        on=[
            "produto",
            "unidade_medida",
        ],
        how="left",
        validate="many_to_one",
    )
    fact = fact.merge(
        posto_lookup,
        on="_posto_identidade",
        how="left",
        validate="many_to_one",
    )

    fact_columns = [
        "data_coleta_id",
        "produto_posto_id",
        "posto_id",
        "preco_revenda",
    ]
    if "preco_compra" in fact.columns:
        fact_columns.append(
            "preco_compra"
        )
    fact_columns.append(
        "fonte_arquivo"
    )

    fact = fact[
        fact_columns
    ].copy()
    fact.insert(
        0,
        "preco_posto_id",
        range(
            1,
            len(fact) + 1,
        ),
    )

    return {
        "dim_data_coleta": dim_data,
        "dim_produto_posto": dim_produto,
        "dim_posto": dim_posto,
        "fato_precos_postos": fact,
    }


def main() -> None:
    frame, audit = (
        consolidate_station_data_with_audit()
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix=".station_bundle_",
        dir=PROCESSED_DIR.parent,
    ) as temporary:
        stage = Path(
            temporary
        )
        staged_output = (
            stage
            / STATION_OUTPUT.name
        )
        staged_audit = (
            stage
            / STATION_INGESTION_AUDIT.name
        )

        frame.to_csv(
            staged_output,
            index=False,
            encoding="utf-8",
        )
        staged_audit.write_text(
            json.dumps(
                audit,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        replace_staged_files(
            [
                (
                    staged_output,
                    STATION_OUTPUT,
                ),
                (
                    staged_audit,
                    STATION_INGESTION_AUDIT,
                ),
            ]
        )

    print(
        "Auditoria de ingestão: "
        f"{STATION_INGESTION_AUDIT.relative_to(PROCESSED_DIR.parent.parent)}"
    )
    print(
        "Base por posto preparada: "
        f"{STATION_OUTPUT.relative_to(PROCESSED_DIR.parent.parent)}"
    )
    print(
        f"Observações elegíveis: "
        f"{len(frame):,}"
    )


if __name__ == "__main__":
    main()
