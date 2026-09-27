import pytest

from src.download_anp import (
    _discover_latest_links,
    _sha256,
    main,
)


def test_discovers_first_matching_links() -> None:
    html = """
    <html><body>
      <a href="/arquivo/medias-2026.xlsx">Preços médios semanais: Brasil, regiões, estados e municípios</a>
      <a href="/arquivo/postos-2026.xlsx">Preços por posto revendedor (combustíveis automotivos e GLP P13)</a>
      <a href="/arquivo/medias-antigas.xlsx">Preços médios semanais: Brasil, regiões, estados e municípios</a>
      <a href="/arquivo/postos-antigos.xlsx">Preços por posto revendedor</a>
    </body></html>
    """

    links = _discover_latest_links(html)

    assert links["precos_medios_semanais"].endswith("/arquivo/medias-2026.xlsx")
    assert links["precos_por_posto"].endswith("/arquivo/postos-2026.xlsx")


def test_sha256_is_deterministic() -> None:
    assert _sha256(b"anp") == _sha256(b"anp")
    assert _sha256(b"anp") != _sha256(b"ANP")



def test_legacy_downloader_is_blocked() -> None:
    with pytest.raises(
        SystemExit,
        match="downloader legado",
    ):
        main()
