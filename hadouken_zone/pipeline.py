"""Ciclo de trabajo: buscar ofertas en Amazon y publicarlas en Telegram."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import requests

from . import messages
from .affiliate import product_url
from .cards import generar_tarjeta
from .config import CARDS_DIR, GOOD_MORNING_IMAGE, GOOD_NIGHT_IMAGE, Settings
from .models import Offer
from .sources import OfferSource, SourceBlocked, build_sources
from .storage import OfferStore
from .telegram import TelegramClient, TelegramError

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, settings: Settings, telegram: TelegramClient, sources: list[OfferSource] | None = None,
                 store: OfferStore | None = None, sleep=time.sleep, still_active=lambda: True):
        self.settings = settings
        self.telegram = telegram
        self.sources = sources if sources is not None else build_sources(settings)
        self.store = store or OfferStore()
        self.sleep = sleep
        self.still_active = still_active     # el planificador indica si seguimos en horario

    # ------------------------------------------------------------ buenos días
    def send_good_morning(self, today) -> None:
        text = messages.good_morning_message(
            today, self.settings.scan_interval_minutes, self.settings.min_discount_percent,
            affiliate=bool(self.settings.amazon_partner_tag),
        )
        if GOOD_MORNING_IMAGE.exists():
            self.telegram.send_photo(GOOD_MORNING_IMAGE, text)
        else:
            self.telegram.send_message(text)
        log.info("Mensaje de buenos días enviado")

    # ------------------------------------------------------------ buenas noches
    def send_good_night(self, today, tz) -> int:
        """Hilo de buenas noches: cabecera con el resumen del día y, como respuestas
        silenciosas, las mejores ofertas publicadas hoy. Devuelve cuántas destaca."""
        s = self.settings
        records = self.store.published_on(today, tz)
        records.sort(key=lambda r: r.get("last_discount_percent") or 0, reverse=True)
        text = messages.good_night_message(today, records, s.good_night_top)
        if GOOD_NIGHT_IMAGE.exists():
            head_id = self.telegram.send_photo(GOOD_NIGHT_IMAGE, text)
        else:
            head_id = self.telegram.send_message(text)
        log.info("Buenas noches enviado (%s ofertas hoy)", len(records))

        sent = 0
        for rank, r in enumerate(records[: s.good_night_top], start=1):
            offer = Offer(asin=r["asin"], title=r.get("title") or "", price=r.get("last_published_price"),
                          previous_price=r.get("last_previous_price"), platform=r.get("platform"),
                          image_url=r.get("image_url"), store=r.get("store") or "Amazon",
                          url=r.get("url") if (r.get("store") or "Amazon").lower() != "amazon" else None)
            if not offer.discount_percent:
                continue
            url, affiliate = self.offer_link(offer)
            caption = messages.good_night_item(rank, offer, url, affiliate=affiliate)
            self.sleep(3)
            try:
                card = generar_tarjeta(
                    titulo=offer.title, plataforma=offer.platform, precio_actual=offer.price,
                    precio_anterior=offer.previous_price, imagen=offer.image_url,
                    salida=CARDS_DIR / f"{offer.asin}.jpg",
                )
                self.telegram.send_photo(card, caption, reply_to=head_id, silent=True)
                sent += 1
            except Exception:
                log.exception("Error enviando %s en el hilo de buenas noches", offer.asin)
        return sent

    # ------------------------------------------------------------ ofertas
    def _is_new(self, offer: Offer) -> bool:
        return self.store.should_publish(offer, self.settings.republish_after_days)

    def offer_link(self, offer: Offer) -> tuple[str, bool]:
        """Enlace de la oferta y si es de afiliado (solo Amazon con ID de afiliado)."""
        s = self.settings
        if offer.url and not offer.is_amazon:
            return offer.url, False
        return product_url(offer.asin, s.amazon_domain, s.amazon_partner_tag), bool(s.amazon_partner_tag)

    def publish_offer(self, offer: Offer) -> None:
        s = self.settings
        url, affiliate = self.offer_link(offer)
        caption = messages.offer_caption(offer, url, affiliate=affiliate)
        try:
            card = generar_tarjeta(
                titulo=offer.title, plataforma=offer.platform, precio_actual=offer.price,
                precio_anterior=offer.previous_price, imagen=offer.image_url,
                salida=CARDS_DIR / f"{offer.asin}.jpg",
            )
            self.telegram.send_photo(card, caption)
        except TelegramError:
            raise
        except Exception as exc:                 # si falla la imagen, al menos el texto
            log.warning("Tarjeta no disponible para %s (%s); se envía solo texto", offer.asin, exc)
            self.telegram.send_message(caption, preview=True)
        age = offer.age_seconds()
        if age is not None:
            log.info("Retraso respecto a la fuente: %s min %02d s (%s)", int(age // 60), int(age % 60), offer.asin)
        if not s.dry_run:
            self.store.mark_published(offer, url)

    def collect_offers(self) -> list[Offer]:
        """Ofertas nuevas de todas las fuentes, sin repetir ASIN.

        Primero las recién salidas (de la más nueva a la más antigua), porque ahí se compite
        con otros canales por ser el primero. Después el resto, de mayor a menor descuento.
        """
        limit = self.settings.max_offers_per_cycle
        found: dict[str, Offer] = {}
        for source in self.sources:
            try:
                offers = source.find_offers(limit, self._is_new)
            except SourceBlocked as exc:
                log.warning("Fuente %s bloqueada: %s. Se reintentará en el próximo escaneo.", source.name, exc)
                continue
            except requests.RequestException as exc:
                log.warning("No se pudo conectar con la fuente %s (%s). Se reintentará en el próximo escaneo.",
                            source.name, exc.__class__.__name__)
                continue
            except Exception:
                log.exception("Error en la fuente %s", source.name)
                continue
            log.info("Fuente %s: %s ofertas válidas", source.name, len(offers))
            for offer in offers:
                found.setdefault(offer.asin, offer)
        now = datetime.now(timezone.utc)
        fresh_minutes = self.settings.fresh_minutes
        fresh = [o for o in found.values() if o.is_fresh(fresh_minutes, now)]
        rest = [o for o in found.values() if not o.is_fresh(fresh_minutes, now)]
        fresh.sort(key=lambda o: o.age_seconds(now))
        rest.sort(key=lambda o: o.discount_percent or 0, reverse=True)
        return (fresh + rest)[:limit]

    def _delay_before(self, offer: Offer) -> int:
        if offer.is_fresh(self.settings.fresh_minutes):
            return self.settings.fresh_offer_delay_seconds
        return self.settings.offer_delay_seconds

    def run_scan(self) -> int:
        """Un ciclo completo. Devuelve cuántas ofertas se han publicado."""
        started = datetime.now()
        offers = self.collect_offers()

        log.info("Ofertas nuevas para publicar: %s", len(offers))
        published = 0
        for index, offer in enumerate(offers):
            if not self.still_active():
                log.info("Fuera del horario activo: se detiene la publicación")
                break
            try:
                self.publish_offer(offer)
                published += 1
                log.info("Publicada %s (-%s%%) %s", offer.asin, offer.discount_percent, offer.title[:60])
            except Exception:
                log.exception("Error publicando %s", offer.asin)
            if index < len(offers) - 1:
                self.sleep(self._delay_before(offers[index + 1]))

        log.info("Ciclo terminado en %ss: %s publicadas", int((datetime.now() - started).total_seconds()), published)
        return published
