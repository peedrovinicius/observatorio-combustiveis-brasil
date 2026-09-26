from __future__ import annotations

from .analytics import main as analytics
from .build_model import main as build_model
from .consolidate import main as consolidate
from .download_history import main as download_history
from .download_open_data import main as download_open_data
from .inspect_raw import main as inspect_raw
from .quality import main as quality
from .station_data import main as station_data
from .station_quality import main as station_quality
from .transform import main as transform


def main() -> None:
    steps = [
        ("1/10 Download da série agregada", download_history),
        ("2/10 Download dos dados abertos por posto", download_open_data),
        ("3/10 Inspeção dos arquivos brutos agregados", inspect_raw),
        ("4/10 Transformação da série agregada", transform),
        ("5/10 Consolidação da série agregada 2026", consolidate),
        ("6/10 Validação de qualidade agregada", quality),
        ("7/10 Construção do modelo estrela agregado", build_model),
        ("8/10 Construção da camada por posto", station_data),
        ("9/10 Validação de qualidade por posto", station_quality),
        ("10/10 Geração de tabelas analíticas", analytics),
    ]

    for title, step in steps:
        print(f"\n=== {title} ===")
        step()

    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
