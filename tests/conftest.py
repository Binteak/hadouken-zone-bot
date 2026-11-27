from pathlib import Path

import pytest

from hadouken_zone.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def html():
    def load(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")
    return load


@pytest.fixture
def settings():
    return Settings.from_env({
        "DRY_RUN": "true",
        "TELEGRAM_BOT_TOKEN": "123:abc",
        "TELEGRAM_CHAT_ID": "@prueba",
        "AMAZON_PARTNER_TAG": "hadouken-21",
        "REQUEST_DELAY_SECONDS": "0",
    })


class FakeTelegram:
    """Sustituye a TelegramClient y guarda lo que se 'envía'."""

    def __init__(self):
        self.sent = []
        self.dry_run = False

    def send_message(self, text, preview=False):
        self.sent.append(("text", text))
        return True

    def send_photo(self, photo, caption, reply_to=None, silent=False):
        self.sent.append(("photo", Path(photo).name, caption))
        self.replies = getattr(self, "replies", []) + [(reply_to, silent)]
        return len(self.sent)          # hace de message_id


@pytest.fixture
def fake_telegram():
    return FakeTelegram()


@pytest.fixture(autouse=True)
def _no_writes_in_project(tmp_path, monkeypatch):
    """Los tests nunca escriben en data/ del proyecto."""
    monkeypatch.setattr("hadouken_zone.pipeline.CARDS_DIR", tmp_path / "tarjetas")
