import pytest

from hadouken_zone.sources.amazon.parser import (
    is_captcha,
    parse_price,
    parse_product_page,
    parse_search_results,
)


@pytest.mark.parametrize("text, expected", [
    ("32,99 €", 32.99),
    ("32,99\xa0€", 32.99),
    ("1.299,99 €", 1299.99),
    ("€32.99", 32.99),
    ("1,299.99", 1299.99),
    ("70", 70.0),
    ("", None),
    (None, None),
    ("gratis", None),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_search_results_extracts_products(html):
    offers = parse_search_results(html("amazon_busqueda.html"), "juegos ps5")
    by_asin = {o.asin: o for o in offers}

    # 7 productos únicos con ASIN (el duplicado y el patrocinado vacío no cuentan)
    assert len(offers) == 7
    gow = by_asin["B0TSTPS501"]
    assert gow.title == "God of War Ragnarök - Edición Estándar"
    assert gow.price == 32.99
    assert gow.previous_price == 59.99
    assert gow.discount_percent == 45
    assert gow.image_url.endswith(".jpg")
    assert "PlayStation 5" in gow.platform_text
    assert gow.source_query == "juegos ps5"


def test_search_price_without_offscreen_uses_whole_and_fraction(html):
    offers = {o.asin: o for o in parse_search_results(html("amazon_busqueda.html"))}
    assert offers["B0TSTPS503"].price == 39.99
    assert offers["B0TSTPS503"].previous_price == 69.99


def test_search_item_without_price(html):
    offers = {o.asin: o for o in parse_search_results(html("amazon_busqueda.html"))}
    assert offers["B0TSTNOP01"].price is None


def test_product_page(html):
    offer = parse_product_page(html("amazon_ficha.html"), "b0tstps501")
    assert offer.asin == "B0TSTPS501"
    assert offer.title == "God of War Ragnarök - Edición Estándar"
    assert offer.price == 30.99
    assert offer.previous_price == 59.99
    assert offer.verified is True
    assert offer.available is True
    assert offer.image_url.endswith("_AC_SL1500_.jpg")
    assert "PlayStation 5" in offer.platform_text


def test_product_page_unavailable(html):
    offer = parse_product_page(html("amazon_ficha_no_disponible.html"), "B0TSTPS501")
    assert offer.available is False


def test_product_page_without_title_returns_none():
    assert parse_product_page("<html><body>nada</body></html>", "B0TSTPS501") is None


def test_captcha_detection(html):
    assert is_captcha(html("amazon_captcha.html"))
    assert not is_captcha(html("amazon_busqueda.html"))
    assert not is_captcha(html("amazon_ficha.html"))
