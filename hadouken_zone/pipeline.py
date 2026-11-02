"""Ciclo de trabajo: buscar ofertas en Amazon y publicarlas en Telegram."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from . import messages
from .affiliate import product_url
from .amazon import AmazonScraper, CaptchaError
from .cards import generar_tarjeta
from .config import CARDS_DIR, GOOD_MORNING_IMAGE, Settings
from .models import Offer
from .storage import OfferStore
from .telegram import TelegramClient, TelegramError

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, settings: Settings, telegram: TelegramClient, scraper: AmazonScraper | None = None,
                 store: OfferStore | None = None, sleep=time.sleep, still_active=lambda: True):
        self.settings = settings
        self.telegram = telegram
        self.scraper = scraper or AmazonScraper(settings)
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

    def run_scan(self) -> int:
        """Un ciclo completo. Devuelve cuántas ofertas se han publicado."""
        started = datetime.now()
        try:
            offers = self.scraper.find_offers(self.settings.max_offers_per_cycle, self._is_new)
        except CaptchaError as exc:
            log.warning("%s. Se reintentará en el próximo escaneo.", exc)
            return 0
        except requests.RequestException as exc:
            log.warning("No se pudo conectar con Amazon (%s). Se reintentará en el próximo escaneo.",
                        exc.__class__.__name__)
            return 0
        except Exception:
            log.exception("Error buscando ofertas")
            return 0

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
