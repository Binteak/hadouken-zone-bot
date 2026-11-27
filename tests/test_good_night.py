"""Hilo de buenas noches: planificador, pipeline, textos, Telegram y historial."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from PIL import Image

from hadouken_zone import messages
from hadouken_zone.models import Offer
from hadouken_zone.pipeline import Pipeline
from hadouken_zone.scheduler import Scheduler
from hadouken_zone.storage import OfferStore, StateStore
from hadouken_zone.telegram import TelegramClient

TZ = ZoneInfo("Europe/Madrid")


# ------------------------------------------------------------ planificador
class FakePipeline:
    def __init__(self):
        self.calls = []
        self.still_active = None

    def send_good_morning(self, day):
        self.calls.append("good_morning")

    def send_good_night(self, day, tz):
        self.calls.append("good_night")
        return 0

    def run_scan(self):
        self.calls.append("scan")
        return 0


def build(settings, tmp_path, start):
    clock = type("C", (), {"now": start, "__call__": lambda self: self.now})()
    pipe = FakePipeline()
    sched = Scheduler(settings, pipe, StateStore(tmp_path / "state.json"), clock=clock, sleep=lambda s: None)
    sched.state.set("last_good_morning", start.date().isoformat())
    return sched, pipe, clock


def test_good_night_at_23_once_and_no_more_scans(settings, tmp_path):
    sched, pipe, clock = build(settings, tmp_path, datetime(2026, 11, 27, 22, 55, tzinfo=TZ))
    assert sched.tick(ignore_interval=True) == ["scan"]
    clock.now = datetime(2026, 11, 27, 23, 2, tzinfo=TZ)
    assert sched.tick(ignore_interval=True) == ["good_night"]
    clock.now += timedelta(minutes=5)
    assert sched.tick(ignore_interval=True) == []          # ni otra vez ni más ofertas
    assert pipe.calls.count("good_night") == 1


def test_good_night_can_be_disabled(settings, tmp_path):
    sched, pipe, _ = build(replace(settings, good_night_time=None), tmp_path,
                           datetime(2026, 11, 27, 23, 5, tzinfo=TZ))
    assert sched.tick(ignore_interval=True) == ["scan"]


def test_good_night_not_after_active_hours(settings, tmp_path):
    sched, pipe, _ = build(settings, tmp_path, datetime(2026, 11, 27, 23, 40, tzinfo=TZ))
    assert sched.tick(ignore_interval=True) == []


# ------------------------------------------------------------ pipeline
def _store_with_today(tmp_path):
    store = OfferStore(tmp_path / "offers.json")
    for asin, title, plat, price, prev in [
        ("B0TSTPS501", "Astro Bot", "PS5", 39.99, 79.99),
        ("B0TSTXB001", "Forza Horizon 5", "Xbox", 24.99, 39.99),
        ("B0TSTSW201", "Mario Kart World", "Nintendo Switch 2", 59.99, 89.99),
        ("B0TSTPS401", "The Last of Us Parte II", "PS4", 19.99, 29.99),
    ]:
        store.mark_published(Offer(asin=asin, title=title, platform=plat, price=price, previous_price=prev),
                             f"https://www.amazon.es/dp/{asin}")
    return store


def test_good_night_thread_top3_as_silent_replies(settings, fake_telegram, tmp_path):
    pipe = Pipeline(settings, fake_telegram, sources=[], store=_store_with_today(tmp_path), sleep=lambda s: None)
    sent = pipe.send_good_night(datetime.now(TZ).date(), TZ)
    assert sent == 3
    kinds = [m[1] for m in fake_telegram.sent]
    assert kinds[0] == "cabecera_buenas_noches.png" and len(kinds) == 4
    assert "4 ofertas" in fake_telegram.sent[0][2]
    # las tres respuestas cuelgan de la cabecera (message_id 1) y van sin sonido
    assert fake_telegram.replies[1:] == [(1, True)] * 3
    # de mayor a menor descuento: Astro Bot (-50 %) primero
    assert "Astro Bot" in fake_telegram.sent[1][2] and "🥇" in fake_telegram.sent[1][2]


def test_good_night_without_offers_sends_only_header(settings, fake_telegram, tmp_path):
    pipe = Pipeline(settings, fake_telegram, sources=[], store=OfferStore(tmp_path / "o.json"), sleep=lambda s: None)
    assert pipe.send_good_night(date(2026, 11, 27), TZ) == 0
    assert len(fake_telegram.sent) == 1
    assert "ninguna oferta" in fake_telegram.sent[0][2]


# ------------------------------------------------------------ textos e historial
def test_good_night_texts_change_by_day():
    a = messages.good_night_message(date(2026, 11, 27), [])
    b = messages.good_night_message(date(2026, 11, 28), [])
    assert a.splitlines()[0] != b.splitlines()[0]


def test_published_on_uses_local_day(tmp_path):
    store = OfferStore(tmp_path / "o.json")
    store.data["offers"]["X"] = {"asin": "X", "last_published_at":
                                 datetime(2026, 11, 27, 23, 30, tzinfo=timezone.utc).isoformat()}
    # 23:30 UTC del 27 son las 00:30 del 28 en Madrid
    assert store.published_on(date(2026, 11, 28), TZ) and not store.published_on(date(2026, 11, 27), TZ)


# ------------------------------------------------------------ Telegram
class Session:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None, files=None, timeout=None):
        self.calls.append(data)
        return type("R", (), {"status_code": 200, "json": lambda self: {"ok": True, "result": {"message_id": 77}}})()


def test_send_photo_reply_and_silent(tmp_path):
    photo = tmp_path / "p.jpg"
    Image.new("RGB", (4, 4)).save(photo)
    session = Session()
    client = TelegramClient("t", "@c", dry_run=False, session=session)
    assert client.send_photo(photo, "cabecera") == 77
    client.send_photo(photo, "oferta", reply_to=77, silent=True)
    data = session.calls[1]
    assert '"message_id": 77' in data["reply_parameters"] and data["disable_notification"] == "true"
