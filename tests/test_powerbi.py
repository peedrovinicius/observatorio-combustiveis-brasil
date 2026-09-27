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
        "Última Data Comparável do Nível ="
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


def test_aggregate_local_date_scan_preserves_current_locality() -> None:
    dax = _dax()

    local_measure = dax.split(
        "Última Data Disponível =",
        1,
    )[1].split(
        "Última Data Comparável do Nível =",
        1,
    )[0]

    assert (
        "REMOVEFILTERS ( dim_localidade )"
        not in local_measure
    )
    assert "TREATAS (" not in local_measure


def test_aggregate_comparable_date_scan_reapplies_level_and_unit() -> None:
    dax = _dax()

    comparable_measure = dax.split(
        "Última Data Comparável do Nível =",
        1,
    )[1].split(
        "Preço Última Semana =",
        1,
    )[0]

    assert (
        "REMOVEFILTERS ( dim_localidade )"
        in comparable_measure
    )
    assert (
        "VAR Unidade =\n    SELECTEDVALUE ( fato_precos_semanais[unidade_medida] )"
        in comparable_measure
    )
    assert (
        "TREATAS (\n                        { Unidade },\n                        fato_precos_semanais[unidade_medida]\n                    )"
        in comparable_measure
    )


def test_previous_week_preserves_current_locality() -> None:
    dax = _dax()

    measure = dax.split(
        "Preço Semana Anterior =",
        1,
    )[1].split(
        "Variação Semanal % =",
        1,
    )[0]

    assert (
        "REMOVEFILTERS ( dim_localidade )"
        not in measure
    )
    assert "TREATAS (" not in measure
