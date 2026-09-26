from __future__ import annotations

from .analytics import main as analytics
from .build_model import main as build_model
from .consolidate import main as consolidate
from .download_history import main as download_history
from .download_open_data import main as download_open_data
from .inspect_raw import main as inspect_raw
from .quality import main as quality
from .reporting import main as reporting
from .station_analytics import main as station_analytics
from .station_data import main as station_data
from .station_quality import main as station_quality
from .transform import main as transform


def main() -> None:
    steps = [
        ("1/12 Download da série agregada", download_history),
        ("2/12 Download dos dados abertos por posto", download_open_data),
        ("3/12 Inspeção dos arquivos brutos agregados", inspect_raw),
        ("4/12 Transformação da série agregada", transform),
        ("5/12 Consolidação da série agregada 2026", consolidate),
        ("6/12 Validação de qualidade agregada", quality),
        ("7/12 Construção do modelo estrela agregado", build_model),
        ("8/12 Construção da camada por posto", station_data),
        ("9/12 Validação de qualidade por posto", station_quality),
        ("10/12 Geração de tabelas analíticas agregadas", analytics),
        ("11/12 Geração de análises por posto", station_analytics),
        ("12/12 Relatório e gráficos", reporting),
    ]

    for title, step in steps:
        print(f"\n=== {title} ===")
        step()

    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
