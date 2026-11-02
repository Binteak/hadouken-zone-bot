"""Fuente de ofertas: Amazon.es (búsqueda + verificación en la ficha de producto)."""

from .client import AmazonClient, CaptchaError
from .scraper import AmazonScraper

__all__ = ["AmazonClient", "AmazonScraper", "CaptchaError"]
