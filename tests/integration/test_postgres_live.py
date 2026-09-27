from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

import src.load_postgres as loader


pytestmark = pytest.mark.postgres


def _write(
    path: Path,
    text: str,
) -> Path:
    path.write_text(
        text,
        encoding="utf-8",
    )
    return path


def _model_bundle(
    root: Path,
) -> list[
    tuple[
        str,
        Path,
    ]
]:
    aggregate = (
        root
        / "aggregate"
    )
    station = (
        root
        / "station"
    )
    aggregate.mkdir()
    station.mkdir()

    return [
        (
            "dim_data",
            _write(
                aggregate / "dim_data.csv",
                (
                    "data_id,data_inicial,data_final,ano,mes,"
                    "semana_iso,trimestre\n"
                    "1,2026-09-20,2026-09-26,2026,9,38,3\n"
                ),
            ),
        ),
        (
            "dim_produto",
            _write(
                aggregate / "dim_produto.csv",
                (
                    "produto_id,produto\n"
                    "1,GASOLINA\n"
                ),
            ),
        ),
        (
            "dim_localidade",
            _write(
                aggregate / "dim_localidade.csv",
                (
                    "localidade_id,nivel_geografico,regiao,"
                    "uf,estado,municipio\n"
                    "1,brasil,,,,\n"
                ),
            ),
        ),
        (
            "fato_precos_semanais",
            _write(
                aggregate
                / "fato_precos_semanais.csv",
                (
                    "preco_fato_id,data_id,produto_id,"
                    "localidade_id,postos_pesquisados,"
                    "unidade_medida,preco_medio_revenda,"
                    "preco_minimo_revenda,preco_maximo_revenda,"
                    "desvio_padrao_revenda,coef_variacao_revenda,"
                    "fonte_arquivo,fonte_planilha\n"
                    "1,1,1,1,10,R$ / litro,6.1000,5.9000,"
                    "6.3000,0.100000,0.016393,"
                    "historico.xlsx,Dados\n"
                ),
            ),
        ),
        (
            "dim_data_coleta",
            _write(
                station
                / "dim_data_coleta.csv",
                (
                    "data_coleta_id,data_coleta,ano,mes,"
                    "semana_iso\n"
                    "1,2026-09-20,2026,9,38\n"
                ),
            ),
        ),
        (
            "dim_produto_posto",
            _write(
                station
                / "dim_produto_posto.csv",
                (
                    "produto_posto_id,produto,unidade_medida\n"
                    "1,GASOLINA,R$ / litro\n"
                ),
            ),
        ),
        (
            "dim_posto",
            _write(
                station
                / "dim_posto.csv",
                (
                    "posto_id,posto_chave,cnpj_revenda,revenda,"
                    "bandeira,regiao,uf,municipio,logradouro,"
                    "numero,complemento,bairro,cep\n"
                    f"1,{'a' * 64},00000001000136,POSTO A,"
                    "BRANCA,NE,CE,FORTALEZA,RUA A,10,,CENTRO,"
                    "60000000\n"
                ),
            ),
        ),
        (
            "fato_precos_postos",
            _write(
                station
                / "fato_precos_postos.csv",
                (
                    "preco_posto_id,data_coleta_id,"
                    "produto_posto_id,posto_id,preco_revenda,"
                    "preco_compra,fonte_arquivo\n"
                    "1,1,1,1,6.1000,,dados.csv\n"
                ),
            ),
        ),
    ]


def test_postgres_loader_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv(
        "DATABASE_URL"
    )
    if not database_url:
        pytest.skip(
            "DATABASE_URL não configurada."
        )

    plan = _model_bundle(
        tmp_path
    )
    monkeypatch.setattr(
        loader,
        "LOAD_PLAN",
        plan,
    )

    loader.main()

    with psycopg.connect(
        database_url
    ) as connection:
        aggregate_count = (
            connection.execute(
                "SELECT COUNT(*) "
                "FROM fato_precos_semanais"
            ).fetchone()[0]
        )
        station_count = (
            connection.execute(
                "SELECT COUNT(*) "
                "FROM fato_precos_postos"
            ).fetchone()[0]
        )
        view_row = (
            connection.execute(
                "SELECT produto, nivel_geografico, "
                "preco_medio_revenda "
                "FROM vw_precos_semanais"
            ).fetchone()
        )

    assert aggregate_count == 1
    assert station_count == 1
    assert view_row[0] == "GASOLINA"
    assert view_row[1] == "brasil"
    assert float(
        view_row[2]
    ) == 6.1
