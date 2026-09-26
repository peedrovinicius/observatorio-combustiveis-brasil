from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_OPEN_DATA_DIR = RAW_DIR / "open_data"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

ANP_WEEKLY_PAGE = (
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/"
    "precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas"
)

ANP_HISTORICAL_PAGE = (
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/"
    "precos/precos-revenda-e-de-distribuicao-combustiveis/"
    "serie-historica-do-levantamento-de-precos"
)

ANP_OPEN_DATA_PAGE = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
    "serie-historica-de-precos-de-combustiveis"
)

ANP_RESELLERS_PAGE = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
    "dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos"
)
