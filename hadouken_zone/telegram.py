"""Cliente mínimo de la API de bots de Telegram (texto y foto con pie, en HTML)."""

from __future__ import annotations

import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str, chat_id: str, dry_run: bool = True, session=None):
        self.token = token
        self.chat_id = chat_id
        self.dry_run = dry_run
        self.session = session or requests.Session()

    def _call(self, method: str, data: dict, files: dict | None = None) -> dict:
        if not self.token or not self.chat_id:
            raise TelegramError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en .env")
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        resp = self.session.post(url, data=data, files=files, timeout=30)
        try:
            payload = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise TelegramError(f"Respuesta no válida de Telegram ({resp.status_code})")
        if not payload.get("ok"):
            raise TelegramError(f"Telegram devolvió un error: {payload.get('description', payload)}")
        return payload

    def send_message(self, text: str, preview: bool = False) -> bool:
        if self.dry_run:
            log.info("[DRY RUN] Mensaje:\n%s", text)
            return True
        self._call("sendMessage", {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false" if preview else "true",
        })
        return True

    def send_photo(self, photo: Path, caption: str) -> bool:
        if self.dry_run:
            log.info("[DRY RUN] Foto %s con pie:\n%s", Path(photo).name, caption)
            return True
        with open(photo, "rb") as fh:
            self._call(
                "sendPhoto",
                {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"photo": (Path(photo).name, fh, "image/jpeg")},
            )
        return True
