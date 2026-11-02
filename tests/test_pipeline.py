from dataclasses import replace
from datetime import date

import pytest

from hadouken_zone.sources.amazon import AmazonScraper, CaptchaError
from hadouken_zone.models import Offer
from hadouken_zone.pipeline import Pipeline
from hadouken_zone.storage import OfferStore


class FakeClient:
    """Cliente de Amazon que devuelve las fixtures en lugar de ir a internet."""

    def __init__(self, html, captcha=False):
        self.html = html
        self.captcha = captcha
        self.requests = []

    def search_url(self, query, page=1):
        return f"search:{query}:{page}"

    def product_url(self, asin):
        return f"product:{asin}"

    def get(self, url):
        self.requests.append(url)
        if self.captcha:
            raise CaptchaError("captcha")
        if url.startswith("search:"):
            return self.html("amazon_busqueda.html")
        asin = url.split(":")[1]
        return self.html("amazon_ficha.html").replace("God of War Ragnarök - Edición Estándar",
                                                      f"Juego {asin} PS5")

    def save_debug(self, html, label):
        pass


@pytest.fixture
def one_search(settings):
    return replace(settings, searches=({"platform": "PS5", "query": "juegos ps5"},), scrape_pages=1)


def test_scraper_finds_only_valid_offers(one_search, html):
    scraper = AmazonScraper(one_search, FakeClient(html))
    offers = scraper.find_offers(limit=10, is_new=lambda o: True)
    asins = {o.asin for o in offers}
    # Válidas: GoW (-45 %), Mario Kart (-30 %), Astro Bot (-43 %).
    # Fuera: Switch 2, mando DualSense, FC 26 (-10 %), sin precio.
    assert asins == {"B0TSTPS501", "B0TSTSW001", "B0TSTPS503"}
    assert all(o.verified for o in offers)
    # ordenadas de mayor a menor descuento tras la búsqueda
    assert offers[0].asin == "B0TSTPS501"


def test_scraper_respects_limit_and_dedup(one_search, html):
    scraper = AmazonScraper(one_search, FakeClient(html))
    offers = scraper.find_offers(limit=1, is_new=lambda o: o.asin != "B0TSTPS501")
    assert len(offers) == 1 and offers[0].asin != "B0TSTPS501"


def test_run_scan_publishes_with_delay_between_offers(one_search, html, fake_telegram, tmp_path):
    settings = replace(one_search, dry_run=False)
    sleeps = []
    pipe = Pipeline(settings, fake_telegram, [AmazonScraper(settings, FakeClient(html))],
                    OfferStore(tmp_path / "offers.json"), sleep=sleeps.append)
    published = pipe.run_scan()

    assert published == 3
    assert [s[0] for s in fake_telegram.sent] == ["photo"] * 3
    assert sleeps == [60, 60]                      # 1 minuto entre ofertas, no tras la última
    assert "tag=hadouken-21" in fake_telegram.sent[0][2]

    # segunda pasada: ya publicadas, no se repiten
    fake_telegram.sent.clear()
    assert pipe.run_scan() == 0


def test_dry_run_does_not_mark_published(one_search, html, fake_telegram, tmp_path):
    store = OfferStore(tmp_path / "offers.json")
    pipe = Pipeline(one_search, fake_telegram, [AmazonScraper(one_search, FakeClient(html))], store,
                    sleep=lambda s: None)
    pipe.run_scan()
    assert store.data["offers"] == {}


def test_captcha_stops_cycle_without_crashing(one_search, html, fake_telegram, tmp_path):
    pipe = Pipeline(one_search, fake_telegram, [AmazonScraper(one_search, FakeClient(html, captcha=True))],
                    OfferStore(tmp_path / "offers.json"), sleep=lambda s: None)
    assert pipe.run_scan() == 0
    assert fake_telegram.sent == []


def test_stops_publishing_outside_active_hours(one_search, html, fake_telegram, tmp_path):
    calls = {"n": 0}

    def still_active():
        calls["n"] += 1
        return calls["n"] <= 1                     # solo deja publicar la primera

    pipe = Pipeline(one_search, fake_telegram, [AmazonScraper(one_search, FakeClient(html))],
                    OfferStore(tmp_path / "offers.json"), sleep=lambda s: None, still_active=still_active)
    assert pipe.run_scan() == 1


def test_good_morning_sends_image(one_search, fake_telegram, tmp_path):
    pipe = Pipeline(one_search, fake_telegram, sources=[], store=OfferStore(tmp_path / "o.json"))
    pipe.send_good_morning(date(2026, 11, 2))
    kind, name, caption = fake_telegram.sent[0]
    assert kind == "photo" and name == "cabecera_buenos_dias.png"
    assert "Buenos días" in caption or "buenos días" in caption.lower()
