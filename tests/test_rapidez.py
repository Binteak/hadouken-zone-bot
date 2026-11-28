"""Publicar antes que la competencia: novedad primero, pausa corta, medición del retraso y caché."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from hadouken_zone.models import Offer
from hadouken_zone.pipeline import Pipeline
from hadouken_zone.sources.chollometro import ChollometroSource, parse_pubdate, parse_rss
from hadouken_zone.storage import OfferStore, delay_stats
from test_chollometro import FakeSession

NOW = datetime.now(timezone.utc)


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat()


def offer(asin, price, prev, posted=None):
    return Offer(asin=asin, title=f"Juego {asin} PS5", price=price, previous_price=prev,
                 platform="PS5", posted_at=posted)


class StaticSource:
    name = "estatica"

    def __init__(self, offers):
        self.offers = offers

    def find_offers(self, limit, is_new):
        return [o for o in self.offers if is_new(o)][:limit]


# ------------------------------------------------------------------ fecha del RSS
def test_parse_pubdate_to_utc():
    assert parse_pubdate("Mon, 02 Nov 2026 13:16:42 +0100") == "2026-11-02T12:16:42+00:00"
    assert parse_pubdate("") is None
    assert parse_pubdate("no es una fecha") is None


def test_rss_entries_carry_posted_at(html):
    entries = parse_rss(html("chollometro_rss.xml"))
    assert entries and all(e["posted_at"] == "2026-11-02T12:16:42+00:00" for e in entries)


def test_offer_age_and_freshness():
    o = offer("B0FRESH001", 10, 20, posted=ago(5))
    assert 290 <= o.age_seconds() <= 310
    assert o.is_fresh(30) and not o.is_fresh(4)
    assert offer("B0NODATE01", 10, 20).age_seconds() is None
    assert not offer("B0NODATE01", 10, 20).is_fresh(30)


# ------------------------------------------------------------------ orden y pausas
def test_fresh_offers_go_first_newest_first(settings, fake_telegram, tmp_path):
    offers = [
        offer("B0OLDBIG01", 10, 50, posted=ago(120)),   # 80 %, pero vieja
        offer("B0FRESH010", 40, 50, posted=ago(10)),    # 20 %, recién salida
        offer("B0FRESH002", 30, 50, posted=ago(2)),     # 40 %, la más nueva
        offer("B0NODATE01", 20, 50),                    # 60 %, sin fecha
    ]
    pipe = Pipeline(settings, fake_telegram, [StaticSource(offers)], OfferStore(tmp_path / "o.json"),
                    sleep=lambda s: None)
    assert [o.asin for o in pipe.collect_offers()] == ["B0FRESH002", "B0FRESH010", "B0OLDBIG01", "B0NODATE01"]


def test_short_pause_before_fresh_offers(settings, fake_telegram, tmp_path):
    offers = [offer("B0FRESH002", 30, 50, posted=ago(2)), offer("B0FRESH010", 40, 50, posted=ago(10)),
              offer("B0OLDBIG01", 10, 50, posted=ago(120))]
    sleeps = []
    pipe = Pipeline(settings, fake_telegram, [StaticSource(offers)], OfferStore(tmp_path / "o.json"),
                    sleep=sleeps.append)
    assert pipe.run_scan() == 3
    assert sleeps == [10, 60]        # 10 s antes de la segunda (recién salida), 60 s antes de la vieja


def test_publish_records_delay(settings, fake_telegram, tmp_path):
    store = OfferStore(tmp_path / "o.json")
    pipe = Pipeline(replace(settings, dry_run=False), fake_telegram,
                    [StaticSource([offer("B0FRESH003", 30, 50, posted=ago(3))])], store, sleep=lambda s: None)
    pipe.run_scan()
    record = store.get("B0FRESH003")
    assert record["source_posted_at"]
    assert 170 <= record["publish_delay_seconds"] <= 200


def test_delay_stats():
    records = [{"publish_delay_seconds": s} for s in (60, 120, 600)] + [{"publish_delay_seconds": None}, {}]
    st = delay_stats(records)
    assert st == {"n": 3, "mean": 260, "median": 120, "min": 60, "max": 600}
    assert delay_stats([{}]) is None


# ------------------------------------------------------------------ caché de hilos revisados
def test_seen_threads_are_not_reopened(settings, html, tmp_path):
    seen = tmp_path / "vistos.json"
    first = ChollometroSource(settings, session=FakeSession(html), sleep=lambda x: None, seen_path=seen)
    offers = first.find_offers(10, lambda o: True)
    assert [o.asin for o in offers] == ["B0CHOLL001", "B0CHOLL002"]

    # Segunda pasada (otro proceso): solo vuelve a abrir las válidas aún sin publicar
    session = FakeSession(html)
    second = ChollometroSource(settings, session=session, sleep=lambda x: None, seen_path=seen)
    offers = second.find_offers(10, lambda o: o.asin != "B0CHOLL001")      # GoW ya publicada
    assert [o.asin for o in offers] == ["B0CHOLL002"]
    opened = [u for u in session.urls if "/rss/" not in u and "/visit/" not in u]
    assert len(opened) == 2                       # GoW y Mario Kart; las descartadas ya no

    # Tercera pasada: GoW ya está recordada como publicada
    session = FakeSession(html)
    third = ChollometroSource(settings, session=session, sleep=lambda x: None, seen_path=seen)
    third.find_offers(10, lambda o: True)
    opened = [u for u in session.urls if "/rss/" not in u and "/visit/" not in u]
    assert len(opened) == 1 and "2050002" in opened[0]


def test_seen_threads_expire(settings, html, tmp_path):
    seen = tmp_path / "vistos.json"
    ChollometroSource(settings, session=FakeSession(html), sleep=lambda x: None, seen_path=seen) \
        .find_offers(10, lambda o: False)
    later = lambda: datetime.now(timezone.utc) + timedelta(days=3)
    session = FakeSession(html)
    ChollometroSource(settings, session=session, sleep=lambda x: None, seen_path=seen, clock=later) \
        .find_offers(10, lambda o: True)
    assert any("/visit/" in u for u in session.urls)     # a los 3 días se vuelven a revisar
