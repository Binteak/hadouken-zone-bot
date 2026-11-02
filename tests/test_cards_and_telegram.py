from PIL import Image

from hadouken_zone.cards import generar_tarjeta, precio_es
from hadouken_zone.telegram import TelegramClient, TelegramError


def test_card_is_generated(tmp_path):
    out = generar_tarjeta("Astro Bot", "PS5", 39.99, 69.99, salida=tmp_path / "card.jpg")
    img = Image.open(out)
    assert img.size == (1280, 720)


def test_card_with_unreachable_image_still_works(tmp_path):
    out = generar_tarjeta("Juego", "Nintendo Switch", 20, 40, imagen=tmp_path / "no-existe.jpg",
                          salida=tmp_path / "c.jpg")
    assert Image.open(out).size == (1280, 720)


def test_precio_es():
    assert precio_es(1234.5) == "1.234,50 €"


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, data=None, files=None, timeout=None):
        self.calls.append((url, data, files))
        return FakeResponse(self.payload)


def test_dry_run_sends_nothing():
    session = FakeSession({"ok": True})
    client = TelegramClient("t", "@c", dry_run=True, session=session)
    assert client.send_message("hola")
    assert session.calls == []


def test_send_message_uses_html():
    session = FakeSession({"ok": True})
    TelegramClient("t", "@c", dry_run=False, session=session).send_message("<b>hola</b>")
    url, data, _ = session.calls[0]
    assert url.endswith("/sendMessage") and data["parse_mode"] == "HTML" and data["chat_id"] == "@c"


def test_send_photo_uploads_file(tmp_path):
    photo = tmp_path / "p.jpg"
    Image.new("RGB", (10, 10)).save(photo)
    session = FakeSession({"ok": True})
    TelegramClient("t", "@c", dry_run=False, session=session).send_photo(photo, "pie")
    url, data, files = session.calls[0]
    assert url.endswith("/sendPhoto") and data["caption"] == "pie" and "photo" in files


def test_telegram_error_is_raised():
    session = FakeSession({"ok": False, "description": "chat not found"})
    client = TelegramClient("t", "@c", dry_run=False, session=session)
    try:
        client.send_message("x")
    except TelegramError as exc:
        assert "chat not found" in str(exc)
    else:
        raise AssertionError("debería fallar")


def test_missing_credentials():
    client = TelegramClient("", "", dry_run=False, session=FakeSession({"ok": True}))
    try:
        client.send_message("x")
    except TelegramError as exc:
        assert "TELEGRAM_BOT_TOKEN" in str(exc)
