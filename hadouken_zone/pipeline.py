"""Ciclo de trabajo: buscar ofertas en Amazon y publicarlas en Telegram."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from . import messages
from .affiliate import product_url
from .cards import generar_tarjeta
from .config import CARDS_DIR, GOOD_MORNING_IMAGE, Settings
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

    # ------------------------------------------------------------ ofertas
    def _is_new(self, offer: Offer) -> bool:
        return self.store.should_publish(offer, self.settings.republish_after_days)

    def publish_offer(self, offer: Offer) -> None:
        s = self.settings
        url = product_url(offer.asin, s.amazon_domain, s.amazon_partner_tag)
        caption = messages.offer_caption(offer, url, affiliate=bool(s.amazon_partner_tag))
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
        if not s.dry_run:
            self.store.mark_published(offer, url)

    def collect_offers(self) -> list[Offer]:
        """Ofertas nuevas de todas las fuentes, sin repetir ASIN, de mayor a menor descuento."""
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
        offers = sorted(found.values(), key=lambda o: o.discount_percent or 0, reverse=True)
        return offers[:limit]

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
                self.sleep(self.settings.offer_delay_seconds)

        log.info("Ciclo terminado en %ss: %s publicadas", int((datetime.now() - started).total_seconds()), published)
        return published
