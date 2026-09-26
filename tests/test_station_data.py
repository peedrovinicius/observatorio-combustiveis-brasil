from pathlib import Path

import pandas as pd

from src.download_open_data import (
    _discover_2026_links,
)
from src.station_data import (
    audit_prepared_station_frame,
    build_station_star_schema,
    consolidate_station_data,
    consolidate_station_data_with_audit,
    deduplicate_station_rows,
    prepare_station_file,
    source_priority,
    source_reference,
    station_identity,
    transform_station_file,
)


def test_discovers_relevant_2026_open_data_links() -> None:
    html = """
    <h3>Combustíveis automotivos</h3>
    <a href="s1.zip">1º semestre de 2026</a>
    <a href="2025.zip">2º semestre de 2025</a>
    <h3>Óleo Diesel (S-500 e S-10) + GNV</h3>
    <a href="jun.csv">Junho de 2026</a>
    <a href="jul.csv">Julho de 2026</a>
    <a href="ago.csv">Agosto de 2026</a>
    <h3>Etanol Hidratado + Gasolina C</h3>
    <a href="jul-eg.csv">Julho de 2026</a>
    <a href="ago-eg.csv">Agosto de 2026</a>
    <h3>Quatro últimas semanas</h3>
    <a href="latest-d.csv">Óleo Diesel (S-500 e S-10) + GNV</a>
    <a href="latest-eg.csv">Etanol Hidratado + Gasolina C</a>
    <a href="latest-glp.csv">GLP P13</a>
    """

    links = _discover_2026_links(html)
    datasets = {
        item["dataset"]
        for item in links
    }

    assert "automotivos_2026_s1" in datasets
    assert "diesel_gnv_julho_2026" in datasets
    assert "diesel_gnv_junho_2026" not in datasets
    assert "etanol_gasolina_agosto_2026" in datasets
    assert "diesel_gnv_ultimas_4_semanas" in datasets
    assert "etanol_gasolina_ultimas_4_semanas" in datasets
    assert all(
        "glp" not in dataset
        for dataset in datasets
    )


def _write_sample(
    path: Path,
    rows: list[list[str]],
) -> None:
    header = [
        "Regiao - Sigla",
        "Estado - Sigla",
        "Municipio",
        "Revenda",
        "CNPJ da Revenda",
        "Nome da Rua",
        "Numero Rua",
        "Complemento",
        "Bairro",
        "Cep",
        "Produto",
        "Data da Coleta",
        "Valor de Venda",
        "Valor de Compra",
        "Unidade de Medida",
        "Bandeira",
    ]
    pd.DataFrame(
        rows,
        columns=header,
    ).to_csv(
        path,
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )


def test_transform_station_file_uses_official_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sample.csv"
    _write_sample(
        path,
        [[
            "NE",
            "CE",
            "FORTALEZA",
            "POSTO TESTE",
            "00.000.000/0001-00",
            "RUA A",
            "1",
            "",
            "CENTRO",
            "60000-000",
            "GASOLINA",
            "20/09/2026",
            "6,129",
            "",
            "R$ / litro",
            "BRANCA",
        ]],
    )

    result = transform_station_file(path)

    assert result.loc[0, "uf"] == "CE"
    assert result.loc[0, "municipio"] == "FORTALEZA"
    assert result.loc[0, "preco_revenda"] == 6.129
    assert result.loc[0, "data_coleta"].year == 2026


def test_station_identity_prefers_cnpj() -> None:
    frame = pd.DataFrame(
        {
            "cnpj_revenda": [
                "00.000.000/0001-00"
            ],
            "uf": ["CE"],
            "municipio": ["FORTALEZA"],
            "revenda": ["POSTO A"],
        }
    )

    assert (
        station_identity(frame).iloc[0]
        == "cnpj:00000000000100"
    )


def test_source_priority_prefers_latest_window() -> None:
    assert (
        source_priority(
            "etanol_gasolina_ultimas_4_semanas.csv"
        )
        > source_priority(
            "etanol_gasolina_agosto_2026.csv"
        )
    )


def test_deduplication_keeps_different_stations_without_cnpj() -> None:
    frame = pd.DataFrame(
        {
            "data_coleta": pd.to_datetime(
                [
                    "2026-09-20",
                    "2026-09-20",
                ]
            ),
            "cnpj_revenda": [
                pd.NA,
                pd.NA,
            ],
            "uf": ["CE", "CE"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
            ],
            "revenda": [
                "POSTO A",
                "POSTO B",
            ],
            "produto": [
                "GASOLINA",
                "GASOLINA",
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
            ],
            "preco_revenda": [
                6.10,
                6.10,
            ],
        }
    )

    result = deduplicate_station_rows(frame)

    assert len(result) == 2


def test_deduplication_prefers_newer_source_when_price_changes() -> None:
    frame = pd.DataFrame(
        {
            "data_coleta": pd.to_datetime(
                [
                    "2026-08-31",
                    "2026-08-31",
                ]
            ),
            "cnpj_revenda": [
                "00.000.000/0001-00",
                "00.000.000/0001-00",
            ],
            "uf": ["CE", "CE"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
            ],
            "revenda": [
                "POSTO A",
                "POSTO A",
            ],
            "produto": [
                "GASOLINA",
                "GASOLINA",
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
            ],
            "preco_revenda": [
                6.10,
                6.20,
            ],
            "fonte_arquivo": [
                "etanol_gasolina_agosto_2026.csv",
                "etanol_gasolina_ultimas_4_semanas.csv",
            ],
        }
    )

    result = deduplicate_station_rows(frame)

    assert len(result) == 1
    assert result.iloc[0]["preco_revenda"] == 6.20


def test_consolidation_removes_overlap(
    tmp_path: Path,
) -> None:
    row = [
        "NE",
        "CE",
        "FORTALEZA",
        "POSTO TESTE",
        "00.000.000/0001-00",
        "RUA A",
        "1",
        "",
        "CENTRO",
        "60000-000",
        "GASOLINA",
        "31/08/2026",
        "6,10",
        "",
        "R$ / litro",
        "BRANCA",
    ]

    _write_sample(
        tmp_path / "aug.csv",
        [row],
    )
    _write_sample(
        tmp_path / "latest.csv",
        [row],
    )

    result = consolidate_station_data(
        tmp_path
    )
    assert len(result) == 1


def test_ingestion_audit_counts_rejected_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audit.csv"
    _write_sample(
        path,
        [
            [
                "NE", "CE", "FORTALEZA", "POSTO A",
                "00.000.000/0001-00", "RUA A", "1", "",
                "CENTRO", "60000-000", "GASOLINA",
                "20/09/2026", "6,10", "", "R$ / litro", "BRANCA",
            ],
            [
                "NE", "CE", "FORTALEZA", "POSTO B",
                "00.000.000/0002-00", "RUA B", "2", "",
                "CENTRO", "60000-000", "GASOLINA",
                "data-invalida", "6,20", "", "R$ / litro", "BRANCA",
            ],
            [
                "NE", "CE", "FORTALEZA", "POSTO C",
                "00.000.000/0003-00", "RUA C", "3", "",
                "CENTRO", "60000-000", "GASOLINA",
                "20/09/2025", "6,30", "", "R$ / litro", "BRANCA",
            ],
            [
                "NE", "CE", "FORTALEZA", "POSTO D",
                "00.000.000/0004-00", "RUA D", "4", "",
                "CENTRO", "60000-000", "GASOLINA",
                "20/09/2026", "0", "", "R$ / litro", "BRANCA",
            ],
        ],
    )

    prepared = prepare_station_file(path)
    audit = audit_prepared_station_frame(
        prepared,
        path.name,
    )

    assert audit["linhas_origem"] == 4
    assert audit["datas_invalidas"] == 1
    assert audit["linhas_fora_2026"] == 1
    assert audit["precos_nao_positivos"] == 1
    assert (
        audit[
            "linhas_elegiveis_antes_deduplicacao"
        ]
        == 1
    )
    assert (
        audit[
            "linhas_excluidas_antes_deduplicacao"
        ]
        == 3
    )


def test_consolidation_audit_measures_overlap(
    tmp_path: Path,
) -> None:
    older = [
        "NE", "CE", "FORTALEZA", "POSTO TESTE",
        "00.000.000/0001-00", "RUA A", "1", "",
        "CENTRO", "60000-000", "GASOLINA",
        "31/08/2026", "6,10", "", "R$ / litro", "BRANCA",
    ]
    newer = older.copy()
    newer[12] = "6,20"

    _write_sample(
        tmp_path / "etanol_gasolina_agosto_2026.csv",
        [older],
    )
    _write_sample(
        tmp_path / "etanol_gasolina_ultimas_4_semanas.csv",
        [newer],
    )

    frame, audit = (
        consolidate_station_data_with_audit(
            tmp_path
        )
    )

    assert len(frame) == 1
    assert (
        frame.iloc[0]["preco_revenda"]
        == 6.20
    )
    assert audit["grupos_sobrepostos"] == 1
    assert (
        audit[
            "grupos_com_preco_divergente"
        ]
        == 1
    )
    assert (
        audit[
            "linhas_removidas_por_sobreposicao"
        ]
        == 1
    )


def test_station_star_schema_keeps_fact_grain() -> None:
    frame = pd.DataFrame(
        {
            "regiao": [
                "NE",
                "NE",
            ],
            "uf": ["CE", "CE"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
            ],
            "revenda": [
                "POSTO A",
                "POSTO A",
            ],
            "cnpj_revenda": [
                "00.000.000/0001-00",
                "00.000.000/0001-00",
            ],
            "produto": [
                "GASOLINA",
                "ETANOL",
            ],
            "data_coleta": pd.to_datetime(
                [
                    "2026-09-20",
                    "2026-09-20",
                ]
            ),
            "preco_revenda": [
                6.10,
                4.50,
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
            ],
            "bandeira": [
                "BRANCA",
                "BRANCA",
            ],
            "fonte_arquivo": [
                "x.csv",
                "x.csv",
            ],
        }
    )

    tables = build_station_star_schema(
        frame
    )

    assert len(tables["dim_posto"]) == 1
    assert (
        len(
            tables[
                "dim_produto_posto"
            ]
        )
        == 2
    )
    assert (
        len(
            tables[
                "fato_precos_postos"
            ]
        )
        == 2
    )



def test_source_reference_preserves_dataset_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "open_data"
    source_dir = (
        root
        / "etanol_gasolina_ultimas_4_semanas"
    )
    source_dir.mkdir(parents=True)
    path = source_dir / "dados.csv"
    path.write_text(
        "x",
        encoding="utf-8",
    )

    assert (
        source_reference(
            path,
            root,
        )
        == "etanol_gasolina_ultimas_4_semanas/dados.csv"
    )


def test_consolidation_uses_parent_dataset_for_priority(
    tmp_path: Path,
) -> None:
    monthly_dir = (
        tmp_path
        / "etanol_gasolina_agosto_2026"
    )
    latest_dir = (
        tmp_path
        / "etanol_gasolina_ultimas_4_semanas"
    )
    monthly_dir.mkdir()
    latest_dir.mkdir()

    older = [
        "NE",
        "CE",
        "FORTALEZA",
        "POSTO TESTE",
        "00.000.000/0001-00",
        "RUA A",
        "1",
        "",
        "CENTRO",
        "60000-000",
        "GASOLINA",
        "31/08/2026",
        "6,10",
        "",
        "R$ / litro",
        "BRANCA",
    ]
    newer = older.copy()
    newer[12] = "6,25"

    _write_sample(
        monthly_dir / "dados.csv",
        [older],
    )
    _write_sample(
        latest_dir / "dados.csv",
        [newer],
    )

    frame, audit = (
        consolidate_station_data_with_audit(
            tmp_path
        )
    )

    assert len(frame) == 1
    assert (
        frame.iloc[0]["preco_revenda"]
        == 6.25
    )
    assert (
        frame.iloc[0]["fonte_arquivo"]
        == "etanol_gasolina_ultimas_4_semanas/dados.csv"
    )
    assert (
        audit[
            "grupos_com_preco_divergente"
        ]
        == 1
    )



def test_station_dimension_is_stable_by_identity() -> None:
    frame = pd.DataFrame(
        {
            "regiao": [
                "NE",
                "NE",
            ],
            "uf": [
                "CE",
                "CE",
            ],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
            ],
            "revenda": [
                "POSTO ANTIGO",
                "POSTO NOVO",
            ],
            "cnpj_revenda": [
                "00.000.000/0001-00",
                "00.000.000/0001-00",
            ],
            "produto": [
                "GASOLINA",
                "GASOLINA",
            ],
            "data_coleta": pd.to_datetime(
                [
                    "2026-01-10",
                    "2026-09-20",
                ]
            ),
            "preco_revenda": [
                6.00,
                6.30,
            ],
            "unidade_medida": [
                "R$ / litro",
                "R$ / litro",
            ],
            "bandeira": [
                "BANDEIRA ANTIGA",
                "BANDEIRA NOVA",
            ],
            "logradouro": [
                "RUA ANTIGA",
                "RUA NOVA",
            ],
            "numero": [
                "10",
                "20",
            ],
            "fonte_arquivo": [
                "automotivos_2026_s1/dados.csv",
                "etanol_gasolina_ultimas_4_semanas/dados.csv",
            ],
        }
    )

    tables = build_station_star_schema(
        frame
    )

    dim_posto = tables[
        "dim_posto"
    ]
    fact = tables[
        "fato_precos_postos"
    ]

    assert len(dim_posto) == 1
    assert (
        dim_posto.iloc[0]["revenda"]
        == "POSTO NOVO"
    )
    assert (
        dim_posto.iloc[0]["bandeira"]
        == "BANDEIRA NOVA"
    )
    assert (
        dim_posto.iloc[0]["logradouro"]
        == "RUA NOVA"
    )
    assert (
        fact["posto_id"].nunique()
        == 1
    )
    assert len(fact) == 2
