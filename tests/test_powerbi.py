from src.config import PROJECT_ROOT


MEASURES = (
    PROJECT_ROOT
    / "powerbi"
    / "medidas.dax"
)


def _dax() -> str:
    return MEASURES.read_text(
        encoding="utf-8",
    )


def test_aggregate_measures_require_single_product_unit_series() -> None:
    dax = _dax()

    assert (
        "HASONEVALUE ( dim_produto[produto] )"
        in dax
    )
    assert (
        "HASONEVALUE ( fato_precos_semanais[unidade_medida] )"
        in dax
    )
    assert (
        "HASONEVALUE ( dim_localidade[nivel_geografico] )"
        in dax
    )
    assert (
        "HASONEVALUE ( dim_localidade[localidade_id] )"
        in dax
    )
    assert (
        "REMOVEFILTERS ( dim_localidade )"
        in dax
    )
    assert (
        "TREATAS ("
        in dax
    )
    assert (
        "Preço Última Semana ="
        in dax
    )
    assert (
        "Postos Pesquisados Última Semana ="
        in dax
    )


def test_station_measures_require_single_product_unit_series() -> None:
    dax = _dax()

    assert (
        "Série por Posto Única ="
        in dax
    )
    assert (
        "HASONEVALUE ( dim_produto_posto[produto_posto_id] )"
        in dax
    )
    assert (
        "REMOVEFILTERS ( dim_posto )"
        in dax
    )
    assert (
        "Última Data de Coleta ="
        in dax
    )
