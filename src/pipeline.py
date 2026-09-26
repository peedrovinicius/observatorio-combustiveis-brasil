from __future__ import annotations

from .analytics import main as analytics
from .build_model import main as build_model
from .consolidate import main as consolidate
from .download_history import main as download_history
from .download_open_data import main as download_open_data
from .inspect_raw import main as inspect_raw
from .quality import main as quality
from .station_data import main as station_data
from .transform import main as transform


def main() -> None:
    steps = [
        ("1/9 Download da série agregada", download_history),
        ("2/9 Download dos dados abertos por posto", download_open_data),
        ("3/9 Inspeção dos arquivos brutos agregados", inspect_raw),
        ("4/9 Transformação da série agregada", transform),
        ("5/9 Consolidação da série agregada 2026", consolidate),
        ("6/9 Validação de qualidade agregada", quality),
        ("7/9 Construção do modelo estrela agregado", build_model),
        ("8/9 Construção da camada por posto", station_data),
        ("9/9 Geração de tabelas analíticas", analytics),
    ]

    for title, step in steps:
        print(f"\n=== {title} ===")
        step()

    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
