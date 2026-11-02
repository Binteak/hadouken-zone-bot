"""Fuente "amazon": busca en Amazon.es y verifica cada oferta en su ficha.

Necesita una conexión doméstica (Amazon bloquea las IP de centros de datos, como GitHub Actions).
"""

from __future__ import annotations

import logging

from ...config import Settings
from ...models import Offer
from ...rules import rejection_reason
from .client import AmazonClient
from .parser import parse_product_page, parse_search_results

log = logging.getLogger(__name__)


class AmazonScraper:
    name = "amazon"

    def __init__(self, settings: Settings, client: AmazonClient | None = None):
        self.settings = settings
        self.client = client or AmazonClient(settings.amazon_domain, settings.request_delay_seconds)

    def search(self) -> list[Offer]:
        """Resultados de todas las búsquedas, sin duplicados por ASIN."""
        found: dict[str, Offer] = {}
        for search in self.settings.searches:
            for page in range(1, self.settings.scrape_pages + 1):
                url = self.client.search_url(search["query"], page)
                html = self.client.get(url)          # CaptchaError se propaga al pipeline
                results = parse_search_results(html, search["query"])
                if not results:
                    log.warning("0 resultados en '%s' p.%s (¿cambió el HTML?)", search["query"], page)
                    self.client.save_debug(html, "busqueda_vacia")
                    break
                for offer in results:
                    found.setdefault(offer.asin, offer)
                log.info("Búsqueda '%s' p.%s: %s productos", search["query"], page, len(results))
        return list(found.values())

    def verify(self, offer: Offer) -> Offer | None:
        """Confirma precio y precio de referencia en la ficha del producto."""
        if not self.settings.verify_product_page:
            offer.verified = bool(offer.price and offer.previous_price)
            return offer
        html = self.client.get(self.client.product_url(offer.asin))
        page = parse_product_page(html, offer.asin)
        if page is None:
            log.warning("No se pudo leer la ficha de %s", offer.asin)
            self.client.save_debug(html, f"ficha_{offer.asin}")
            return None
        # La ficha manda (es más reciente); se completa con lo que traía la búsqueda
        page.image_url = page.image_url or offer.image_url
        page.platform_text = f"{page.platform_text} {offer.platform_text}".strip()
        page.source_query = offer.source_query
        return page

    def find_offers(self, limit: int, is_new) -> list[Offer]:
        """Ofertas verificadas y publicables, de mayor a menor descuento.

        is_new(offer) -> bool decide si ya se publicó (deduplicación).
        """
        candidates = []
        for offer in self.search():
            reason = rejection_reason(offer, self.settings)
            if reason:
                log.debug("Descartada %s: %s", offer.asin, reason)
                continue
            if is_new(offer):
                candidates.append(offer)

        candidates.sort(key=lambda o: o.discount_percent or 0, reverse=True)
        log.info("Candidatas tras filtrar la búsqueda: %s", len(candidates))

        verified = []
        for offer in candidates:
            if len(verified) >= limit:
                break
            checked = self.verify(offer)
            if checked is None or not checked.verified:
                continue
            reason = rejection_reason(checked, self.settings)
            if reason:
                log.info("Descartada tras verificar %s: %s", offer.asin, reason)
                continue
            if is_new(checked):
                verified.append(checked)
        return verified
