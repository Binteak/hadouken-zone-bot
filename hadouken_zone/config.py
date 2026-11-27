"""Configuración central: rutas del proyecto y ajustes leídos del archivo .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------- rutas
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
CARDS_DIR = DATA_DIR / "tarjetas"
DEBUG_DIR = LOGS_DIR / "html_debug"

BRANDING_DIR = ROOT_DIR / "branding"
FONTS_DIR = BRANDING_DIR / "fuentes"
MASCOT_DIR = BRANDING_DIR / "mascota"
GOOD_MORNING_IMAGE = BRANDING_DIR / "telegram" / "cabeceras" / "cabecera_buenos_dias.png"

PLATFORM_PS5 = "PS5"
PLATFORM_SWITCH = "Nintendo Switch"
PLATFORM_XBOX = "Xbox"

# Búsquedas que recorre el scraper (editables). Se piden SCRAPE_PAGES páginas de cada una.
SEARCHES = (
    {"platform": PLATFORM_PS5, "query": "juegos ps5"},
    {"platform": PLATFORM_PS5, "query": "videojuegos playstation 5 oferta"},
    {"platform": PLATFORM_SWITCH, "query": "juegos nintendo switch"},
    {"platform": PLATFORM_SWITCH, "query": "videojuegos nintendo switch oferta"},
    {"platform": PLATFORM_XBOX, "query": "juegos xbox series x"},
)


CHOLLOMETRO_FEEDS = (
    "https://www.chollometro.com/rss/nuevos",
    "https://www.chollometro.com/rss/hot",
)


def _parse_time(value: str) -> time:
    hours, minutes = value.strip().split(":")
    return time(int(hours), int(minutes))


def _bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "si", "sí")


@dataclass(frozen=True)
class Settings:
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    dry_run: bool = True

    # Fuentes de ofertas, en orden de prioridad (ver hadouken_zone/sources/)
    offer_sources: tuple = ("chollometro",)
    chollometro_feeds: tuple = field(default=CHOLLOMETRO_FEEDS)

    # Amazon
    amazon_domain: str = "www.amazon.es"
    amazon_partner_tag: str = ""          # p. ej. hadoukenzone-21 (vacío = enlaces sin afiliado)
    request_delay_seconds: float = 4.0
    scrape_pages: int = 2
    verify_product_page: bool = True

    # Reglas de negocio
    min_discount_percent: int = 15
    max_discount_percent: int = 90        # por encima se considera precio de referencia incoherente
    max_reference_price: float = 300.0    # un juego por encima de esto: referencia sospechosa
    include_switch_2: bool = False
    include_xbox: bool = True             # juegos de Xbox Series X|S y Xbox One
    republish_after_days: int = 7

    # Calendario
    timezone: str = "Europe/Madrid"
    good_morning_time: time = time(9, 0)
    active_until: time = time(23, 30)
    scan_interval_minutes: int = 30
    offer_delay_seconds: int = 60
    max_offers_per_cycle: int = 25

    searches: tuple = field(default=SEARCHES)

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Settings":
        if env is None:
            load_dotenv(ROOT_DIR / ".env")
            env = dict(os.environ)
        g = env.get
        d = cls()
        return cls(
            telegram_bot_token=g("TELEGRAM_BOT_TOKEN", "") or "",
            telegram_chat_id=g("TELEGRAM_CHAT_ID", "") or "",
            dry_run=_bool(g("DRY_RUN", "true")),
            offer_sources=tuple(x.strip().lower() for x in (g("OFFER_SOURCES", "chollometro") or "chollometro").split(",") if x.strip()),
            amazon_domain=g("AMAZON_DOMAIN", d.amazon_domain),
            amazon_partner_tag=(g("AMAZON_PARTNER_TAG", "") or "").strip(),
            request_delay_seconds=float(g("REQUEST_DELAY_SECONDS", d.request_delay_seconds)),
            scrape_pages=int(g("SCRAPE_PAGES", d.scrape_pages)),
            verify_product_page=_bool(g("VERIFY_PRODUCT_PAGE", "true")),
            min_discount_percent=int(g("MIN_DISCOUNT_PERCENT", d.min_discount_percent)),
            include_switch_2=_bool(g("INCLUDE_SWITCH_2", "false")),
            include_xbox=_bool(g("INCLUDE_XBOX", "true")),
            republish_after_days=int(g("REPUBLISH_AFTER_DAYS", d.republish_after_days)),
            timezone=g("TIMEZONE", d.timezone),
            good_morning_time=_parse_time(g("GOOD_MORNING_TIME", "09:00")),
            active_until=_parse_time(g("ACTIVE_UNTIL", "23:30")),
            scan_interval_minutes=int(g("SCAN_INTERVAL_MINUTES", d.scan_interval_minutes)),
            offer_delay_seconds=int(g("OFFER_DELAY_SECONDS", d.offer_delay_seconds)),
            max_offers_per_cycle=int(g("MAX_OFFERS_PER_CYCLE", d.max_offers_per_cycle)),
        )
