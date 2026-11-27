from datetime import date

import pytest

from hadouken_zone import messages
from hadouken_zone.affiliate import extract_asin, product_url
from hadouken_zone.models import Offer


def test_product_url_with_tag():
    assert product_url("B0TSTPS501", partner_tag="hadouken-21") == "https://www.amazon.es/dp/B0TSTPS501?tag=hadouken-21"


def test_product_url_without_tag_is_plain():
    assert product_url("b0tstps501") == "https://www.amazon.es/dp/B0TSTPS501"


def test_product_url_rejects_bad_asin():
    with pytest.raises(ValueError):
        product_url("123")


def test_extract_asin():
    assert extract_asin("https://www.amazon.es/God-War/dp/B0TSTPS501/ref=sr_1_1?k=x") == "B0TSTPS501"
    assert extract_asin("https://example.com") is None


def test_precio_formato_espanol():
    assert messages.precio(1299.5) == "1.299,50 €"
    assert messages.precio(9.9) == "9,90 €"


def test_good_morning_message():
    text = messages.good_morning_message(date(2026, 11, 2), 30, 20, affiliate=True)
    assert "lunes 2 de noviembre" in text
    assert "30 minutos" in text and "-20%" in text
    assert "afiliado de Amazon" in text


def test_good_morning_varies_by_day():
    a = messages.good_morning_message(date(2026, 11, 2)).splitlines()[0]
    b = messages.good_morning_message(date(2026, 11, 3)).splitlines()[0]
    assert a != b


def test_offer_caption_escapes_html_and_shows_prices():
    offer = Offer(asin="B0TSTPS501", title="Ratchet & Clank <Rift Apart>", price=29.99,
                  previous_price=79.99, platform="PS5")
    caption = messages.offer_caption(offer, "https://www.amazon.es/dp/B0TSTPS501?tag=x-21")
    assert "Ratchet &amp; Clank &lt;Rift Apart&gt;" in caption
    assert "<b>-63%</b>" in caption
    assert "<s>79,99 €</s>" in caption
    assert "Te ahorras 50,00 €" in caption
    assert "#PS5" in caption and "Enlace de afiliado" in caption


def test_offer_caption_without_affiliate_has_no_notice():
    offer = Offer(asin="B0TSTSW001", title="Mario Kart", price=30, previous_price=50, platform="Nintendo Switch")
    caption = messages.offer_caption(offer, "https://www.amazon.es/dp/B0TSTSW001", affiliate=False)
    assert "afiliado" not in caption
    assert "#NintendoSwitch" in caption


def test_offer_caption_xbox_hashtag():
    offer = Offer(asin="B0TSTXB001", title="Halo Infinite", price=20, previous_price=40, platform="Xbox")
    assert "#Xbox" in messages.offer_caption(offer, "https://www.amazon.es/dp/B0TSTXB001")


def test_caption_stays_under_telegram_limit():
    offer = Offer(asin="B0TSTSW001", title="X" * 2000, price=30, previous_price=50, platform="PS5")
    assert len(messages.offer_caption(offer, "https://a.es")) <= 1024


def test_every_good_morning_variant_says_buenos_dias():
    for offset in range(7):
        text = messages.good_morning_message(date(2026, 11, 2 + offset))
        assert "Buenos días" in text.splitlines()[0]
