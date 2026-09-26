from __future__ import annotations

from .analytics import main as analytics
from .build_model import main as build_model
from .consolidate import main as consolidate
from .download_history import main as download_history
from .inspect_raw import main as inspect_raw
from .quality import main as quality
from .transform import main as transform


def main() -> None:
    steps = [
        ("1/7 Download da série histórica", download_history),
        ("2/7 Inspeção dos arquivos brutos", inspect_raw),
        ("3/7 Transformação e padronização", transform),
        ("4/7 Consolidação da série 2026", consolidate),
        ("5/7 Validação de qualidade", quality),
        ("6/7 Construção do modelo estrela", build_model),
        ("7/7 Geração de tabelas analíticas", analytics),
    ]

    for title, step in steps:
        print(f"\n=== {title} ===")
        step()

    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
