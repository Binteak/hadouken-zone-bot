"""Ofertas de otras tiendas (MediaMarkt, PcComponentes…): enlace directo y nombre de la tienda."""

from dataclasses import replace

from hadouken_zone import messages
from hadouken_zone.models import Offer
from hadouken_zone.pipeline import Pipeline
from hadouken_zone.sources.chollometro import parse_rss, store_offer_id, store_url_from_redirect
from hadouken_zone.storage import OfferStore

RSS = """<rss><channel>
<item><title>Juego A PS5</title><link>https://www.chollometro.com/ofertas/juego-a-111</link>
<pepper:merchant name="MediaMarkt" /></item>
<item><title>Juego B PS5</title><link>https://www.chollometro.com/ofertas/juego-b-222</link>
<pepper:merchant name="AliExpress" /></item>
<item><title>Juego C PS5</title><link>https://www.chollometro.com/ofertas/juego-c-333</link>
<pepper:merchant name="Amazon" /></item>
</channel></rss>"""


def test_parse_rss_accepts_configured_stores():
    entries = parse_rss(RSS, ("amazon", "mediamarkt"))
    assert [(e["thread_id"], e["store"]) for e in entries] == [("111", "MediaMarkt"), ("333", "Amazon")]
    assert [e["store"] for e in parse_rss(RSS)] == ["Amazon"]          # por defecto, solo Amazon


def test_store_url_from_redirect_cleans_tracking():
    loc = ("https://path.chollometro.com/pepper-es/redirect?url=https%3A%2F%2Fwww.mediamarkt.es%2Fes%2Fproduct%2F"
           "_juego-a-ps5-123.html%3Futm_source%3Dchollometro%26color%3Dazul&product=ppr-es-1")
    assert store_url_from_redirect(loc) == "https://www.mediamarkt.es/es/product/_juego-a-ps5-123.html?color=azul"
    assert store_url_from_redirect("https://www.chollometro.com/ofertas/x-1") is None
    assert store_url_from_redirect("") is None


def test_store_offer_id_is_stable_and_10_chars():
    a = store_offer_id("https://www.mediamarkt.es/p/1")
    assert a == store_offer_id("https://www.mediamarkt.es/p/1") and len(a) == 10 and a.startswith("T")
    assert a != store_offer_id("https://www.mediamarkt.es/p/2")


def test_caption_shows_store_and_direct_link(settings, fake_telegram, tmp_path):
    offer = Offer(asin=store_offer_id("https://www.mediamarkt.es/p/1"), title="Juego A PS5", price=30,
                  previous_price=60, platform="PS5", store="MediaMarkt", url="https://www.mediamarkt.es/p/1")
    pipe = Pipeline(replace(settings, dry_run=False), fake_telegram, [], OfferStore(tmp_path / "o.json"),
                    sleep=lambda s: None)
    url, affiliate = pipe.offer_link(offer)
    assert url == "https://www.mediamarkt.es/p/1" and affiliate is False      # sin afiliado fuera de Amazon
    pipe.publish_offer(offer)
    caption = fake_telegram.sent[-1][2]
    assert "Ver oferta en MediaMarkt" in caption and "mediamarkt.es/p/1" in caption
    assert "🛒 MediaMarkt" in caption and "Enlace de afiliado" not in caption
    assert pipe.store.get(offer.asin)["store"] == "MediaMarkt"


def test_amazon_caption_unchanged(settings):
    offer = Offer(asin="B0AAAAAAA1", title="Juego PS5", price=30, previous_price=60, platform="PS5")
    caption = messages.offer_caption(offer, "https://www.amazon.es/dp/B0AAAAAAA1", affiliate=False)
    assert "Ver oferta en Amazon" in caption and "🛒 Amazon" in caption


def test_store_url_unwraps_affiliate_networks():
    loc = ("https://path.chollometro.com/pepper-es/redirect?url=https%3A%2F%2Fwww.awin1.com%2Fcread.php%3F"
           "awinmid%3D1%26awinaffid%3D2%26ued%3Dhttps%253A%252F%252Fwww.pccomponentes.com%252Fjuego-a-ps5")
    assert store_url_from_redirect(loc) == "https://www.pccomponentes.com/juego-a-ps5"
