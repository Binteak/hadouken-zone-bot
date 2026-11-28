"""Cliente mínimo de la API de bots de Telegram (texto y foto con pie, en HTML)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)


class TelegramError(RuntimeError):
    pass


class MessageGone(TelegramError):
    """El mensaje que se quería editar ya no existe (lo han borrado del canal)."""


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

    def check(self) -> tuple[str, str]:
        """Comprueba token y canal sin publicar nada. Devuelve (bot, canal)."""
        bot = self._call("getMe", {})["result"]
        chat = self._call("getChat", {"chat_id": self.chat_id})["result"]
        return "@" + bot.get("username", "?"), chat.get("title") or chat.get("username") or str(chat.get("id"))

    def send_message(self, text: str, preview: bool = False):
        """Envía un texto. Devuelve el message_id (o True si no lo hay / DRY_RUN)."""
        if self.dry_run:
            log.info("[DRY RUN] Mensaje:\n%s", text)
            return True
        payload = self._call("sendMessage", {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false" if preview else "true",
        })
        return (payload.get("result") or {}).get("message_id") or True

    # ------------------------------------------------------------ edición de mensajes ya publicados
    def edit_caption(self, message_id: int, caption: str) -> None:
        if self.dry_run:
            log.info("[DRY RUN] Editar pie del mensaje %s:\n%s", message_id, caption)
            return
        self._edit("editMessageCaption", {"chat_id": self.chat_id, "message_id": message_id,
                                          "caption": caption, "parse_mode": "HTML"})

    def edit_text(self, message_id: int, text: str) -> None:
        if self.dry_run:
            log.info("[DRY RUN] Editar texto del mensaje %s:\n%s", message_id, text)
            return
        self._edit("editMessageText", {"chat_id": self.chat_id, "message_id": message_id, "text": text,
                                       "parse_mode": "HTML", "disable_web_page_preview": "true"})

    def edit_photo(self, message_id: int, photo: Path, caption: str) -> None:
        """Cambia la foto (tarjeta) y el pie de un mensaje ya publicado."""
        if self.dry_run:
            log.info("[DRY RUN] Editar foto del mensaje %s (%s) con pie:\n%s", message_id, Path(photo).name, caption)
            return
        media = {"type": "photo", "media": "attach://tarjeta", "caption": caption, "parse_mode": "HTML"}
        with open(photo, "rb") as fh:
            self._edit("editMessageMedia", {"chat_id": self.chat_id, "message_id": message_id,
                                            "media": json.dumps(media)},
                       files={"tarjeta": (Path(photo).name, fh, "image/jpeg")})

    def _edit(self, method: str, data: dict, files: dict | None = None) -> None:
        try:
            self._call(method, data, files)
        except TelegramError as exc:
            text = str(exc).lower()
            if "message is not modified" in text:
                return                      # ya tenía ese contenido
            if "message to edit not found" in text or "message_id_invalid" in text:
                raise MessageGone(str(exc)) from exc
            raise

    def send_photo(self, photo: Path, caption: str, reply_to: int | None = None, silent: bool = False):
        """Envía una foto con pie. Devuelve el message_id (o True si no lo hay / DRY_RUN).

        reply_to: id del mensaje al que responde (para encadenar un "hilo" en el canal).
        silent: sin sonido de notificación.
        """
        if self.dry_run:
            extra = f" (respuesta a {reply_to})" if reply_to else ""
            log.info("[DRY RUN] Foto %s%s con pie:\n%s", Path(photo).name, extra, caption)
            return True
        data = {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"}
        if reply_to and reply_to is not True:
            data["reply_parameters"] = json.dumps({"message_id": reply_to, "allow_sending_without_reply": True})
        if silent:
            data["disable_notification"] = "true"
        with open(photo, "rb") as fh:
            payload = self._call("sendPhoto", data, files={"photo": (Path(photo).name, fh, "image/jpeg")})
        return (payload.get("result") or {}).get("message_id") or True
