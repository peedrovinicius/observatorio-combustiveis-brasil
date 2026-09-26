from __future__ import annotations

from .build_model import main as build_model
from .consolidate import main as consolidate
from .download_history import main as download_history
from .inspect_raw import main as inspect_raw
from .quality import main as quality
from .transform import main as transform


def main() -> None:
    steps = [
        ("1/6 Download da série histórica", download_history),
        ("2/6 Inspeção dos arquivos brutos", inspect_raw),
        ("3/6 Transformação e padronização", transform),
        ("4/6 Consolidação da série 2026", consolidate),
        ("5/6 Validação de qualidade", quality),
        ("6/6 Construção do modelo estrela", build_model),
    ]

    for title, step in steps:
        print(f"\n=== {title} ===")
        step()

    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
