from __future__ import annotations

from .consolidate import main as consolidate
from .download_history import main as download_history
from .inspect_raw import main as inspect_raw
from .quality import main as quality
from .transform import main as transform


def main() -> None:
    steps = [
        ("1/5 Download da série histórica", download_history),
        ("2/5 Inspeção dos arquivos brutos", inspect_raw),
        ("3/5 Transformação e padronização", transform),
        ("4/5 Consolidação da série 2026", consolidate),
        ("5/5 Validação de qualidade", quality),
    ]

    for title, step in steps:
        print(f"\n=== {title} ===")
        step()

    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
