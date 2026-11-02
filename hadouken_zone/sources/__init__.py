"""Fuentes de ofertas enchufables.

    chollometro  Ofertas de Amazon publicadas en Chollometro (funciona desde GitHub Actions).
    amazon       Scraper directo de Amazon.es (necesita conexión doméstica).

Se eligen con OFFER_SOURCES en el .env (separadas por comas, en orden de prioridad).
"""

from __future__ import annotations

from ..config import Settings
from .amazon import AmazonScraper, CaptchaError
from .base import OfferSource, SourceBlocked
from .chollometro import ChollometroSource

REGISTRY = {
    "chollometro": ChollometroSource,
    "amazon": AmazonScraper,
}


def build_sources(settings: Settings) -> list[OfferSource]:
    unknown = [n for n in settings.offer_sources if n not in REGISTRY]
    if unknown:
        raise ValueError(f"Fuentes desconocidas en OFFER_SOURCES: {', '.join(unknown)}. "
                         f"Disponibles: {', '.join(REGISTRY)}")
    return [REGISTRY[name](settings) for name in settings.offer_sources]


__all__ = ["AmazonScraper", "CaptchaError", "ChollometroSource", "OfferSource", "SourceBlocked",
           "build_sources", "REGISTRY"]
