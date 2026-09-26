import pandas as pd

from src.reporting import (
    _select_common_gasoline,
    build_insights_markdown,
)


def test_select_common_gasoline_excludes_additive() -> None:
    products = pd.Series(
        [
            "GASOLINA ADITIVADA",
            "GASOLINA COMUM",
            "ETANOL HIDRATADO",
        ]
    )

    assert _select_common_gasoline(products) == "GASOLINA COMUM"


def test_insights_use_data_values() -> None:
    kpis = pd.DataFrame(
        {
            "produto": ["GASOLINA COMUM"],
            "preco_atual": [6.25],
            "variacao_semanal_pct": [1.5],
            "variacao_desde_inicio_ano_pct": [2.0],
            "menor_preco_2026": [5.90],
            "maior_preco_2026": [6.40],
        }
    )
    ranking = pd.DataFrame(
        {
            "produto": ["GASOLINA COMUM", "GASOLINA COMUM"],
            "uf": ["CE", "SP"],
            "preco_medio_revenda": [6.30, 6.10],
        }
    )

    text = build_insights_markdown(
        kpis,
        ranking,
        {"status": "passed"},
        {
            "status": "passed",
            "postos_distintos_cnpj": 100,
            "municipios": 20,
        },
    )

    assert "R$ 6,25" in text
    assert "+1,50%" in text
    assert "CE: R$ 6,30" in text
    assert "Postos distintos por CNPJ: **100**" in text
