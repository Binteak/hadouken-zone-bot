from datetime import datetime, timedelta, timezone

from hadouken_zone.models import Offer
from hadouken_zone.storage import OfferStore, StateStore


def offer(price=30.0):
    return Offer(asin="B0TSTPS501", title="Astro Bot", price=price, previous_price=60.0, platform="PS5")


def test_new_offer_is_publishable(tmp_path):
    store = OfferStore(tmp_path / "offers.json")
    assert store.should_publish(offer(), republish_after_days=7)


def test_published_offer_is_not_repeated(tmp_path):
    path = tmp_path / "offers.json"
    OfferStore(path).mark_published(offer(), "https://www.amazon.es/dp/B0TSTPS501")
    store = OfferStore(path)                      # se recarga del disco
    assert not store.should_publish(offer(), 7)
    assert store.get("B0TSTPS501")["times_published"] == 1


def test_republish_after_days(tmp_path):
    store = OfferStore(tmp_path / "offers.json")
    store.mark_published(offer(), "u")
    later = datetime.now(timezone.utc) + timedelta(days=8)
    assert store.should_publish(offer(), 7, now=later)


def test_republish_if_price_drops(tmp_path):
    store = OfferStore(tmp_path / "offers.json")
    store.mark_published(offer(30.0), "u")
    assert not store.should_publish(offer(29.5), 7)     # bajada pequeña
    assert store.should_publish(offer(27.0), 7)         # bajada >= 5 %


def test_corrupt_file_does_not_crash(tmp_path):
    path = tmp_path / "offers.json"
    path.write_text("{roto", encoding="utf-8")
    assert OfferStore(path).should_publish(offer(), 7)


def test_state_store_persists(tmp_path):
    path = tmp_path / "state.json"
    StateStore(path).set("last_good_morning", "2026-11-02")
    assert StateStore(path)["last_good_morning"] == "2026-11-02"
    assert not (tmp_path / "state.tmp").exists()
