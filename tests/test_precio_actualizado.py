"""Precio actualizado y oferta terminada: edición de mensajes ya publicados (1.8.0)."""
from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from hadouken_zone.models import Offer
from hadouken_zone.pipeline import Pipeline
from hadouken_zone.scheduler import Scheduler
from hadouken_zone.storage import OfferStore, StateStore
from hadouken_zone.telegram import MessageGone, TelegramClient, TelegramError
from hadouken_zone.updates import PriceUpdater

TZ = ZoneInfo("Europe/Madrid")


class FakeTelegram:
    def __init__(self, gone=False):
        self.calls = []
        self.gone = gone
        self.next_id = 100

    def send_photo(self, photo, caption, reply_to=None, silent=False):
        self.next_id += 1
        self.calls.append(("send_photo", self.next_id, caption))
        return self.next_id

    def send_message(self, text, preview=False):
        self.next_id += 1
        self.calls.append(("send_message", self.next_id, text))
        return self.next_id

    def _check(self):
        if self.gone:
            raise MessageGone("Bad Request: message to edit not found")

    def edit_caption(self, message_id, caption):
        self._check()
        self.calls.append(("edit_caption", message_id, caption))

    def edit_text(self, message_id, text):
        self._check()
        self.calls.append(("edit_text", message_id, text))

    def edit_photo(self, message_id, photo, caption):
        self._check()
        self.calls.append(("edit_photo", message_id, caption))


class FakeSource:
    name = "chollometro"
    delay = 0

    def __init__(self, data):
        self.data = data
        self.checked = []

    def recheck(self, thread_id, url=None):
        self.checked.append((thread_id, url))
        return self.data

    def find_offers(self, limit, is_new):
        return []


def oferta(**kw):
    base = dict(asin="B08XRNCFZX", title="Final Fantasy VII Remake Intergrade", price=29.90,
                previous_price=38.48, platform="PS5", source_query="chollometro:2094751",
                source_url="https://www.chollometro.com/ofertas/ff7-2094751")
    base.update(kw)
    return Offer(**base)


@pytest.fixture
def real(settings):
    return replace(settings, dry_run=False)


def publicar(settings, tmp_path, data, offer=None, telegram=None):
    tg = telegram or FakeTelegram()
    store = OfferStore(tmp_path / "offers.json")
    src = FakeSource(data)
    pipe = Pipeline(settings, tg, sources=[src], store=store, sleep=lambda s: None)
    pipe.publish_offer(offer or oferta())
    return pipe, tg, store, src


def hoy():
    return datetime.now(TZ).date()


# ------------------------------------------------------------ guardar el mensaje
def test_al_publicar_se_guarda_message_id_y_origen(real, tmp_path):
    _, tg, store, _ = publicar(real, tmp_path, {})
    r = store.get("B08XRNCFZX")
    assert r["message_id"] == 101 and r["with_photo"] is True
    assert r["source"] == "chollometro:2094751"
    assert r["source_url"].endswith("2094751") and r["ended"] is False


def test_message_id_true_no_se_guarda(tmp_path):
    store = OfferStore(tmp_path / "o.json")
    store.mark_published(oferta(), "u", message_id=True)
    assert store.get("B08XRNCFZX")["message_id"] is None


# ------------------------------------------------------------ precio actualizado
def test_precio_nuevo_edita_tarjeta_y_texto(real, tmp_path):
    pipe, tg, store, src = publicar(real, tmp_path, {"price": 18.99, "nextBestPrice": 38.48})
    stats = pipe.check_prices(hoy(), TZ)
    assert stats == {"revisadas": 1, "actualizadas": 1, "terminadas": 0}
    kind, mid, caption = tg.calls[-1]
    assert kind == "edit_photo" and mid == 101
    assert caption.startswith("🔄 <b>Precio actualizado</b> (antes 29,90 €)")
    assert "18,99 €" in caption and "-51%" in caption
    r = store.get("B08XRNCFZX")
    assert r["last_published_price"] == 18.99 and r["last_discount_percent"] == 51 and r["times_updated"] == 1
    assert src.checked == [("2094751", "https://www.chollometro.com/ofertas/ff7-2094751")]


def test_mismo_precio_no_edita(real, tmp_path):
    pipe, tg, store, _ = publicar(real, tmp_path, {"price": 29.90, "nextBestPrice": 38.48})
    assert pipe.check_prices(hoy(), TZ)["actualizadas"] == 0
    assert [c[0] for c in tg.calls] == ["send_photo"]


def test_sin_precio_anterior_en_la_fuente_mantiene_el_de_antes(real, tmp_path):
    pipe, tg, store, _ = publicar(real, tmp_path, {"price": 25.00, "nextBestPrice": None})
    pipe.check_prices(hoy(), TZ)
    assert store.get("B08XRNCFZX")["last_previous_price"] == 38.48


def test_sube_sin_descuento_avisa_que_ya_no_esta_en_oferta(real, tmp_path):
    pipe, tg, store, _ = publicar(real, tmp_path, {"price": 45.00, "nextBestPrice": None})
    assert pipe.check_prices(hoy(), TZ)["terminadas"] == 1
    kind, _, caption = tg.calls[-1]
    assert kind == "edit_caption" and caption.startswith("❌ <b>Ya no está en oferta</b> (ahora 45,00 €)")
    assert store.get("B08XRNCFZX")["ended"] is True


# ------------------------------------------------------------ oferta terminada
@pytest.mark.parametrize("data", [{"isExpired": True}, {"isMaybeExpired": True}, {"status": "expired"},
                                  {"gone": True}])
def test_oferta_terminada_marca_el_mensaje(real, tmp_path, data):
    pipe, tg, store, _ = publicar(real, tmp_path, data)
    assert pipe.check_prices(hoy(), TZ)["terminadas"] == 1
    kind, mid, caption = tg.calls[-1]
    assert kind == "edit_caption" and mid == 101 and caption.startswith("❌ <b>Oferta terminada</b>")
    assert store.get("B08XRNCFZX")["ended"] is True
    # ya no se vuelve a revisar
    assert pipe.check_prices(hoy(), TZ)["revisadas"] == 0


def test_mensaje_de_solo_texto_se_edita_como_texto(real, tmp_path):
    tg = FakeTelegram()
    store = OfferStore(tmp_path / "offers.json")
    store.mark_published(oferta(), "u", message_id=7, with_photo=False)
    pipe = Pipeline(real, tg, sources=[FakeSource({"isExpired": True})], store=store, sleep=lambda s: None)
    pipe.check_prices(hoy(), TZ)
    assert tg.calls[-1][0] == "edit_text"


def test_mensaje_borrado_del_canal_se_deja_de_revisar(real, tmp_path):
    pipe, tg, store, _ = publicar(real, tmp_path, {"price": 18.99}, telegram=FakeTelegram(gone=True))
    pipe.check_prices(hoy(), TZ)
    assert store.get("B08XRNCFZX")["message_id"] is None
    assert pipe.check_prices(hoy(), TZ)["revisadas"] == 0


def test_ofertas_antiguas_sin_message_id_no_se_tocan(real, tmp_path):
    store = OfferStore(tmp_path / "offers.json")
    store.mark_published(oferta(), "u")                      # como las publicadas antes de 1.8.0
    tg = FakeTelegram()
    pipe = Pipeline(real, tg, sources=[FakeSource({"price": 1.0})], store=store, sleep=lambda s: None)
    assert pipe.check_prices(hoy(), TZ)["revisadas"] == 0 and tg.calls == []


def test_dry_run_no_cambia_el_historial(settings, tmp_path):
    store = OfferStore(tmp_path / "offers.json")
    store.mark_published(oferta(), "u", message_id=5)
    tg = FakeTelegram()
    pipe = Pipeline(settings, tg, sources=[FakeSource({"price": 18.99})], store=store, sleep=lambda s: None)
    pipe.check_prices(hoy(), TZ)
    assert store.get("B08XRNCFZX")["last_published_price"] == 29.90


def test_buenas_noches_no_destaca_ofertas_terminadas(real, tmp_path):
    pipe, tg, store, _ = publicar(real, tmp_path, {"isExpired": True})
    pipe.check_prices(hoy(), TZ)
    pipe.send_good_night(hoy(), TZ)
    assert all(c[0] != "send_photo" or "Final Fantasy" not in c[2] for c in tg.calls[2:])


# ------------------------------------------------------------ planificador
class FakePipeline:
    def __init__(self):
        self.calls = []
        self.still_active = None

    def send_good_morning(self, day):
        self.calls.append("good_morning")

    def send_good_night(self, day, tz):
        self.calls.append("good_night")

    def run_scan(self):
        self.calls.append("scan")

    def check_prices(self, day, tz):
        self.calls.append("price_check")


def test_planificador_revisa_cada_hora(settings, tmp_path):
    clock = type("C", (), {"now": datetime(2026, 11, 28, 10, 0, tzinfo=TZ), "__call__": lambda self: self.now})()
    pipe = FakePipeline()
    sched = Scheduler(settings, pipe, StateStore(tmp_path / "state.json"), clock=clock, sleep=lambda s: None)
    sched.state.set("last_good_morning", "2026-11-28")
    assert sched.tick(ignore_interval=True) == ["scan", "price_check"]
    clock.now += timedelta(minutes=30)
    assert sched.tick(ignore_interval=True) == ["scan"]
    clock.now += timedelta(minutes=31)
    assert sched.tick(ignore_interval=True) == ["scan", "price_check"]


def test_planificador_sin_revision_si_esta_desactivada(settings, tmp_path):
    clock = lambda: datetime(2026, 11, 28, 10, 0, tzinfo=TZ)
    pipe = FakePipeline()
    sched = Scheduler(replace(settings, price_check_minutes=0), pipe, StateStore(tmp_path / "s.json"),
                      clock=clock, sleep=lambda s: None)
    sched.state.set("last_good_morning", "2026-11-28")
    assert sched.tick(ignore_interval=True) == ["scan"]


def test_planificador_no_revisa_tras_buenas_noches(settings, tmp_path):
    clock = lambda: datetime(2026, 11, 28, 23, 10, tzinfo=TZ)
    pipe = FakePipeline()
    sched = Scheduler(settings, pipe, StateStore(tmp_path / "s.json"), clock=clock, sleep=lambda s: None)
    sched.state.set("last_good_morning", "2026-11-28")
    sched.state.set("last_good_night", "2026-11-28")
    assert "price_check" not in sched.tick(ignore_interval=True)


# ------------------------------------------------------------ Telegram
class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.posts = []

    def post(self, url, data=None, files=None, timeout=None):
        self.posts.append((url.rsplit("/", 1)[-1], data, files))
        payload = self.payload
        return type("R", (), {"json": lambda self: payload, "status_code": 200})()


def test_telegram_edit_photo_usa_editMessageMedia(tmp_path):
    foto = tmp_path / "t.jpg"
    foto.write_bytes(b"x")
    s = FakeSession({"ok": True, "result": {}})
    TelegramClient("t", "@c", dry_run=False, session=s).edit_photo(9, foto, "pie")
    method, data, files = s.posts[0]
    assert method == "editMessageMedia" and data["message_id"] == 9
    assert '"media": "attach://tarjeta"' in data["media"] and "tarjeta" in files


def test_telegram_no_modificado_no_es_error():
    s = FakeSession({"ok": False, "description": "Bad Request: message is not modified"})
    TelegramClient("t", "@c", dry_run=False, session=s).edit_caption(9, "pie")


def test_telegram_mensaje_borrado_lanza_message_gone():
    s = FakeSession({"ok": False, "description": "Bad Request: message to edit not found"})
    with pytest.raises(MessageGone):
        TelegramClient("t", "@c", dry_run=False, session=s).edit_caption(9, "pie")


def test_telegram_otro_error_se_propaga():
    s = FakeSession({"ok": False, "description": "Too Many Requests: retry after 5"})
    with pytest.raises(TelegramError):
        TelegramClient("t", "@c", dry_run=False, session=s).edit_text(9, "x")


def test_send_message_devuelve_message_id():
    s = FakeSession({"ok": True, "result": {"message_id": 55}})
    assert TelegramClient("t", "@c", dry_run=False, session=s).send_message("hola") == 55
