from dataclasses import replace

import pytest

from hadouken_zone.models import Offer
from hadouken_zone.pipeline import Pipeline
from hadouken_zone.sources import REGISTRY, SourceBlocked, build_sources
from hadouken_zone.sources.chollometro import (
    ChollometroSource,
    asin_from_redirect,
    big_image,
    clean_title,
    parse_rss,
    parse_thread,
)
from hadouken_zone.storage import OfferStore

ASINS = {
    "2050001": "B0CHOLL001",
    "2050002": "B0CHOLL002",
    "2050005": "B0CHOLL005",
    "2050006": "B0CHOLL006",
    "2050007": "B0CHOLL007",
    "2050008": "B0CHOLL008",
}


class FakeResponse:
    def __init__(self, text="", status=200, headers=None):
        self.text = text
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    """Chollometro simulado: RSS, páginas de oferta y redirecciones /visit."""

    def __init__(self, html, blocked=False):
        self.html = html
        self.blocked = blocked
        self.headers = {}
        self.urls = []

    def get(self, url, timeout=None, allow_redirects=True):
        self.urls.append(url)
        if self.blocked:
            return FakeResponse(status=403)
        if "/rss/" in url:
            return FakeResponse(self.html("chollometro_rss.xml"))
        if "/visit/threadmain/" in url:
            tid = url.rsplit("/", 1)[1]
            asin = ASINS.get(tid)
            target = f"https%3A%2F%2Fwww.amazon.es%2Fdp%2F{asin}%3Fsmid%3DA1AT7YVPFBWXBL" if asin else "https%3A%2F%2Fwww.amazon.es%2Fs%3Fk%3Dps5"
            return FakeResponse(status=302, headers={
                "Location": f"https://path.chollometro.com/pepper-es/redirect?url={target}&product=ppr-es-1&tag=ugc"})
        tid = url.rsplit("-", 1)[1]
        try:
            return FakeResponse(self.html(f"chollometro_oferta_{tid}.html"))
        except FileNotFoundError:
            return FakeResponse(status=404)


@pytest.fixture
def source(settings, html):
    s = replace(settings, chollometro_feeds=("https://www.chollometro.com/rss/nuevos",))
    return ChollometroSource(s, session=FakeSession(html), sleep=lambda x: None)


# ------------------------------------------------------------------ parsers
def test_parse_rss_keeps_only_amazon(html):
    entries = parse_rss(html("chollometro_rss.xml"))
    ids = [e["thread_id"] for e in entries]
    assert "2050003" not in ids                      # AliExpress
    assert ids[0] == "2050001" and len(ids) == 7
    assert entries[0]["title"] == "God of War Ragnarök PS5 (Precio mínimo)"
    assert "/re/1024x1024/" in entries[0]["image_url"]


def test_parse_thread_picks_main_deal_not_related(html):
    data = parse_thread(html("chollometro_oferta_2050001.html"), "2050001")
    assert data["price"] == 32.99
    assert data["nextBestPrice"] == 59.99
    assert data["linkHost"] == "www.amazon.es"
    assert data["title"].startswith("God of War")


def test_parse_thread_fallback_when_json_is_broken(html):
    page = html("chollometro_oferta_2050001.html").replace('"commentCount": 3', '"commentCount": 3,,,')
    data = parse_thread(page, "2050001")
    assert data["price"] == 32.99 and data["nextBestPrice"] == 59.99


def test_parse_thread_unknown_id():
    assert parse_thread("<html></html>", "123") is None


@pytest.mark.parametrize("location, asin", [
    ("https://path.chollometro.com/pepper-es/redirect?url=https%3A%2F%2Fwww.amazon.es%2Fdp%2FB0DT9Y8RWH%3Fsmid%3DX&tag=ugc", "B0DT9Y8RWH"),
    ("https://www.amazon.es/Juego-PS5/dp/B0CHOLL001/ref=x", "B0CHOLL001"),
    ("https://www.amazon.es/gp/product/B0CHOLL002", "B0CHOLL002"),
    ("https://www.amazon.es/s?k=ps5", None),
    ("", None),
])
def test_asin_from_redirect(location, asin):
    assert asin_from_redirect(location) == asin


@pytest.mark.parametrize("raw, clean", [
    ("God of War Ragnarök PS5 (Precio mínimo)", "God of War Ragnarök PS5"),
    ("Mario Kart 8 Deluxe Nintendo Switch - 34,99€", "Mario Kart 8 Deluxe Nintendo Switch"),
    ("Red Dead Redemption PS5 (VENTAJAS + Cupón, o ESD1103 por 19€)", "Red Dead Redemption PS5"),
    ("Astro Bot PS5 por 39,99€", "Astro Bot PS5"),
    ("Zelda Echoes of Wisdom", "Zelda Echoes of Wisdom"),
])
def test_clean_title(raw, clean):
    assert clean_title(raw) == clean


def test_big_image():
    assert big_image("https://static.chollometro.com/threads/raw/X/1_1/re/150x150/qt/55/1_1.jpg").endswith(
        "/re/1024x1024/qt/55/1_1.jpg")


# ------------------------------------------------------------------ fuente completa
def test_find_offers_end_to_end(source):
    offers = source.find_offers(limit=10, is_new=lambda o: True)
    by_asin = {o.asin: o for o in offers}
    # Válidas: GoW (-45 %) y Mario Kart (-30 %).
    # Fuera: AliExpress, aspiradora, mando, sin precio anterior, caducada y Zelda (-10 %).
    assert list(by_asin) == ["B0CHOLL001", "B0CHOLL002"]
    gow = by_asin["B0CHOLL001"]
    assert gow.title == "God of War Ragnarök PS5"
    assert (gow.price, gow.previous_price, gow.discount_percent) == (32.99, 59.99, 45)
    assert gow.platform == "PS5" and gow.verified
    assert by_asin["B0CHOLL002"].platform == "Nintendo Switch"


def test_find_offers_does_not_open_non_game_pages(source):
    source.find_offers(limit=10, is_new=lambda o: True)
    opened = " ".join(source.session.urls)
    assert "2050004" not in opened          # aspiradora: descartada por el título del RSS
    assert "2050003" not in opened          # AliExpress: descartada por la tienda


def test_find_offers_respects_dedup_and_limit(source):
    offers = source.find_offers(limit=1, is_new=lambda o: o.asin != "B0CHOLL001")
    assert [o.asin for o in offers] == ["B0CHOLL002"]


def test_blocked_source_raises(settings, html):
    src = ChollometroSource(settings, session=FakeSession(html, blocked=True), sleep=lambda x: None)
    with pytest.raises(SourceBlocked):
        src.find_offers(10, lambda o: True)


# ------------------------------------------------------------------ varias fuentes
class StaticSource:
    def __init__(self, name, offers=None, error=None):
        self.name = name
        self.offers = offers or []
        self.error = error

    def find_offers(self, limit, is_new):
        if self.error:
            raise self.error
        return [o for o in self.offers if is_new(o)][:limit]


def offer(asin, price, prev):
    return Offer(asin=asin, title=f"Juego {asin} PS5", price=price, previous_price=prev, platform="PS5")


def test_pipeline_merges_sources_dedups_and_survives_blocked_source(settings, fake_telegram, tmp_path):
    sources = [
        StaticSource("bloqueada", error=SourceBlocked("503")),
        StaticSource("a", [offer("B0AAAAAAA1", 30, 60), offer("B0AAAAAAA2", 40, 50)]),
        StaticSource("b", [offer("B0AAAAAAA1", 30, 60), offer("B0AAAAAAA3", 10, 40)]),
    ]
    pipe = Pipeline(settings, fake_telegram, sources, OfferStore(tmp_path / "o.json"), sleep=lambda s: None)
    offers = pipe.collect_offers()
    assert [o.asin for o in offers] == ["B0AAAAAAA3", "B0AAAAAAA1", "B0AAAAAAA2"]   # 75 %, 50 %, 20 %
    assert pipe.run_scan() == 3


def test_build_sources_default_and_unknown(settings):
    assert [s.name for s in build_sources(settings)] == ["chollometro"]
    assert set(REGISTRY) == {"chollometro", "amazon"}
    with pytest.raises(ValueError):
        build_sources(replace(settings, offer_sources=("inventada",)))


# ------------------------------------------------------------ revisión posterior (1.8.0)
def test_recheck_lee_la_oferta_aunque_ya_este_revisada(source):
    source._remember("2050001")
    data = source.recheck("2050001", "https://www.chollometro.com/ofertas/juego-2050001")
    assert data["price"] and data["threadId"] == "2050001"
    assert source.session.urls[-1] == "https://www.chollometro.com/ofertas/juego-2050001"


def test_recheck_sin_url_usa_el_numero_de_hilo(source):
    source.recheck("2050001")
    assert source.session.urls[-1].endswith("/ofertas/oferta-2050001")


def test_recheck_oferta_borrada(source):
    assert source.recheck("2999999") == {"gone": True}


def test_las_ofertas_guardan_su_pagina_de_origen(source):
    offers = source.find_offers(limit=10, is_new=lambda o: True)
    assert offers and all(o.source_url and o.source_url.startswith("https://www.chollometro.com/") for o in offers)
