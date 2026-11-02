"""Reglas de negocio: plataforma, productos excluidos y validez del descuento."""

from __future__ import annotations

import re

from .config import PLATFORM_PS5, PLATFORM_SWITCH, Settings
from .models import Offer

PLATFORM_PATTERNS = {
    PLATFORM_PS5: [r"\bps\s?5\b", r"\bplaystation\s?5\b"],
    PLATFORM_SWITCH: [r"\bnintendo\s+switch\b", r"\bswitch\s+(?:oled|lite)\b", r"\bswitch\b"],
}
SWITCH_2_PATTERN = r"\b(?:nintendo\s+)?switch\s?2\b"

# No son videojuegos (accesorios, hardware, tarjetas…)
EXCLUDED_WORDS = (
    "mando", "controller", "dualsense", "joy-con", "joycon", "auriculares", "headset",
    "cargador", "estación de carga", "base de carga", "funda", "carcasa",
    "volante", "figura", "amiibo", "tarjeta regalo", "gift card", "tarjeta prepago",
    "suscripción", "suscripcion", "membership", "protector de pantalla",
    "disco duro", "ssd", "tarjeta de memoria", "cámara", "camara", "playstation portal",
    "batería", "bateria", "grip", "adaptador", "nintendo switch online", "playstation plus",
    "ps plus",
)
# Palabras que solo excluyen si el título no dice que es un juego ("Juego para consola PS5")
SOFT_EXCLUDED_WORDS = ("consola", "memoria", "soporte", "cable")
GAME_HINTS = ("juego", "videojuego", "edición", "edicion", "edition")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _has_word(text: str, word: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text) is not None


def detect_platform(text: str, include_switch_2: bool = False) -> str | None:
    """Devuelve 'PS5', 'Nintendo Switch' o None."""
    t = normalize(text)
    if re.search(SWITCH_2_PATTERN, t):
        return PLATFORM_SWITCH if include_switch_2 else None
    found = [p for p, pats in PLATFORM_PATTERNS.items() if any(re.search(x, t) for x in pats)]
    # Si menciona las dos (p. ej. "Hogwarts Legacy PS5/Switch") no es fiable
    return found[0] if len(found) == 1 else None


def is_excluded(title: str) -> bool:
    t = normalize(title)
    if any(_has_word(t, w) for w in EXCLUDED_WORDS):
        return True
    looks_like_game = any(_has_word(t, h) for h in GAME_HINTS)
    return not looks_like_game and any(_has_word(t, w) for w in SOFT_EXCLUDED_WORDS)


def rejection_reason(offer: Offer, settings: Settings) -> str | None:
    """None si la oferta es publicable; si no, el motivo del descarte."""
    if not offer.asin or not offer.title:
        return "sin ASIN o título"
    if is_excluded(offer.title):
        return "no es un videojuego (accesorio/hardware)"

    platform = detect_platform(offer.title, settings.include_switch_2)
    if platform is None and offer.platform_text:
        platform = detect_platform(offer.platform_text, settings.include_switch_2)
    if platform is None:
        return "plataforma no reconocida o no objetivo"
    offer.platform = platform

    if not offer.available:
        return "no disponible"
    if not isinstance(offer.price, (int, float)) or offer.price <= 0:
        return "precio actual no válido"
    if not isinstance(offer.previous_price, (int, float)) or offer.previous_price <= offer.price:
        return "sin precio anterior válido"
    if offer.previous_price > settings.max_reference_price:
        return "precio de referencia incoherente"

    discount = offer.discount_percent
    if discount is None or discount < settings.min_discount_percent:
        return f"descuento insuficiente ({discount}%)"
    if discount > settings.max_discount_percent:
        return f"descuento incoherente ({discount}%)"
    return None
