import pandas as pd

from src.build_model import build_star_schema


def test_star_schema_builds_dimensions_and_fact() -> None:
    frame = pd.DataFrame(
        {
            "data_inicial": [
                "2026-01-04",
                "2026-01-04",
                "2026-01-11",
            ],
            "data_final": [
                "2026-01-10",
                "2026-01-10",
                "2026-01-17",
            ],
            "nivel_geografico": [
                "municipio",
                "municipio",
                "municipio",
            ],
            "regiao": ["NORDESTE", "NORDESTE", "NORDESTE"],
            "uf": ["CE", "CE", "CE"],
            "estado": ["CEARA", "CEARA", "CEARA"],
            "municipio": [
                "FORTALEZA",
                "FORTALEZA",
                "FORTALEZA",
            ],
            "produto": [
                "GASOLINA",
                "ETANOL",
                "GASOLINA",
            ],
            "preco_medio_revenda": [6.0, 4.5, 6.1],
            "unidade_medida": ["R$/L", "R$/L", "R$/L"],
        }
    )

    tables = build_star_schema(frame)

    assert len(tables["dim_data"]) == 2
    assert len(tables["dim_produto"]) == 2
    assert len(tables["dim_localidade"]) == 1
    assert len(tables["fato_precos_semanais"]) == 3

    fact = tables["fato_precos_semanais"]
    assert fact["data_id"].notna().all()
    assert fact["produto_id"].notna().all()
    assert fact["localidade_id"].notna().all()
