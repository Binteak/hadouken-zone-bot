"""Precio actualizado y oferta terminada.

Cada PRICE_CHECK_MINUTES (60) se vuelven a abrir en la fuente las ofertas publicadas hoy
y, si algo ha cambiado, se edita su mensaje en el canal:

- Precio distinto  -> tarjeta y texto nuevos, con «🔄 Precio actualizado (antes X)».
- Oferta terminada -> «❌ Oferta terminada» encima del texto (la tarjeta se queda).

Solo se pueden editar los mensajes de los que se guardó el message_id (publicados desde la
versión 1.8.0). Los mensajes borrados a mano del canal se dejan de revisar.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from html import escape

from . import messages
from .cards import generar_tarjeta
from .config import CARDS_DIR, Settings
from .models import Offer
from .sources import SourceBlocked
from .storage import OfferStore
from .telegram import MessageGone, TelegramClient

log = logging.getLogger(__name__)

MAX_CHECKS = 40          # ofertas revisadas como mucho en cada revisión
EDIT_PAUSE = 3           # segundos entre ediciones (límites de la API de Telegram)


def _money(v) -> float | None:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def offer_from_record(record: dict) -> Offer:
    store = record.get("store") or "Amazon"
    return Offer(asin=record["asin"], title=record.get("title") or "", price=record.get("last_published_price"),
                 previous_price=record.get("last_previous_price"), platform=record.get("platform"),
                 image_url=record.get("image_url"), store=store,
                 url=record.get("url") if store.lower() != "amazon" else None)


def ended_caption(caption: str) -> str:
    return "❌ <b>Oferta terminada</b>\n\n" + caption


def updated_caption(caption: str, old_price: float | None) -> str:
    antes = f" (antes {escape(messages.precio(old_price))})" if old_price else ""
    return f"🔄 <b>Precio actualizado</b>{antes}\n\n" + caption


class PriceUpdater:
    def __init__(self, settings: Settings, telegram: TelegramClient, store: OfferStore, sources: list,
                 link_for, sleep=time.sleep):
        self.settings = settings
        self.telegram = telegram
        self.store = store
        self.sources = {getattr(s, "name", ""): s for s in sources}
        self.link_for = link_for          # Pipeline.offer_link: (url, afiliado)
        self.sleep = sleep

    def pending(self, today: date, tz) -> list[dict]:
        out = []
        for r in self.store.published_on(today, tz):
            source = (r.get("source") or "")
            if r.get("ended") or not r.get("message_id") or ":" not in source:
                continue
            if source.split(":", 1)[0] in self.sources:
                out.append(r)
        return out[:MAX_CHECKS]

    def run(self, today: date, tz) -> dict:
        """Revisa las ofertas de hoy. Devuelve un resumen {'revisadas', 'actualizadas', 'terminadas'}."""
        stats = {"revisadas": 0, "actualizadas": 0, "terminadas": 0}
        for record in self.pending(today, tz):
            name, thread_id = record["source"].split(":", 1)
            source = self.sources[name]
            try:
                data = source.recheck(thread_id, record.get("source_url"))
            except SourceBlocked as exc:
                log.warning("Revisión de precios detenida: %s", exc)
                break
            except Exception as exc:
                log.warning("No se pudo revisar %s (%s)", record["asin"], exc.__class__.__name__)
                continue
            stats["revisadas"] += 1
            if not data:
                continue
            try:
                result = self.apply(record, data)
            except MessageGone:
                log.info("El mensaje de %s ya no está en el canal: no se revisa más", record["asin"])
                self.store.mark_updated(record["asin"], message_gone=True)
                continue
            except Exception:
                log.exception("Error editando el mensaje de %s", record["asin"])
                continue
            if result:
                stats[result] += 1
                self.sleep(EDIT_PAUSE)
            if hasattr(source, "delay"):
                self.sleep(source.delay)
        log.info("Revisión de precios: %(revisadas)s revisadas, %(actualizadas)s con precio nuevo, "
                 "%(terminadas)s terminadas", stats)
        return stats

    def apply(self, record: dict, data: dict) -> str | None:
        """Edita el mensaje si hace falta. Devuelve 'actualizadas', 'terminadas' o None."""
        offer = offer_from_record(record)
        message_id = record["message_id"]
        url, affiliate = self.link_for(offer)

        expired = (data.get("gone") or data.get("isExpired") or data.get("isMaybeExpired")
                   or str(data.get("status", "")).lower() == "expired")
        if expired:
            caption = ended_caption(messages.offer_caption(offer, url, affiliate=affiliate))
            if record.get("with_photo", True):
                self.telegram.edit_caption(message_id, caption)
            else:
                self.telegram.edit_text(message_id, caption)
            if not self.settings.dry_run:
                self.store.mark_updated(offer.asin, ended=True)
            log.info("Oferta terminada: %s %s", offer.asin, offer.title[:50])
            return "terminadas"

        new_price = _money(data.get("price"))
        if new_price is None or offer.price is None or abs(new_price - offer.price) < 0.01:
            return None
        old_price = offer.price
        new_previous = _money(data.get("nextBestPrice")) or offer.previous_price
        if not new_previous or new_previous <= new_price:
            # ha subido tanto que ya no hay descuento: se avisa de que ya no está en oferta
            caption = (f"❌ <b>Ya no está en oferta</b> (ahora {escape(messages.precio(new_price))})\n\n"
                       + messages.offer_caption(offer, url, affiliate=affiliate))
            if record.get("with_photo", True):
                self.telegram.edit_caption(message_id, caption)
            else:
                self.telegram.edit_text(message_id, caption)
            if not self.settings.dry_run:
                self.store.mark_updated(offer.asin, ended=True)
            log.info("Ya no está en oferta: %s ahora %s", offer.asin, messages.precio(new_price))
            return "terminadas"
        updated = Offer(**{**offer.__dict__, "price": new_price, "previous_price": new_previous})
        caption = updated_caption(messages.offer_caption(updated, url, affiliate=affiliate), old_price)
        if record.get("with_photo", True):
            card = generar_tarjeta(titulo=updated.title, plataforma=updated.platform, precio_actual=updated.price,
                                   precio_anterior=updated.previous_price, imagen=updated.image_url,
                                   salida=CARDS_DIR / f"{updated.asin}.jpg")
            self.telegram.edit_photo(message_id, card, caption)
        else:
            self.telegram.edit_text(message_id, caption)
        if not self.settings.dry_run:
            self.store.mark_updated(offer.asin, offer=updated)
        log.info("Precio actualizado: %s %s -> %s (%s)", offer.asin, messages.precio(old_price),
                 messages.precio(new_price), offer.title[:50])
        return "actualizadas"
