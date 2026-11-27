"""Textos del canal (HTML de Telegram)."""

from __future__ import annotations

from datetime import date
from html import escape

from .models import Offer

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

PLATFORM_TAGS = {"PS5": "#PS5", "Nintendo Switch": "#NintendoSwitch", "Xbox": "#Xbox"}

AFFILIATE_NOTICE = "Como afiliado de Amazon, obtengo ingresos por las compras adscritas que cumplen los requisitos aplicables."

GOOD_MORNING_OPENINGS = [
    "☀️ <b>¡Buenos días, jugadores!</b>",
    "☀️ <b>¡Buenos días! Arriba, que hay ofertas que cazar.</b>",
    "☕ <b>¡Buenos días, Hadouken Zone!</b>",
    "🎮 <b>¡Buenos días! Mandos listos.</b>",
    "🔥 <b>¡Buenos días, cazadores de chollos!</b>",
    "⚡ <b>¡Buenos días! Empieza la jornada de ofertas.</b>",
    "🌅 <b>¡Buenos días, comunidad!</b>",
]


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def precio(value: float) -> str:
    entero, dec = f"{value:,.2f}".split(".")
    return f"{entero.replace(',', '.')},{dec} €"


def good_morning_message(d: date, scan_minutes: int = 30, min_discount: int = 20, affiliate: bool = True) -> str:
    opening = GOOD_MORNING_OPENINGS[d.toordinal() % len(GOOD_MORNING_OPENINGS)]
    lines = [
        opening,
        "",
        f"Hoy es {fecha_larga(d)} y arrancamos la caza de ofertas de <b>PS5</b>, <b>Nintendo Switch</b> y <b>Xbox</b>. 🕹️",
        "",
        f"🔎 Revisamos Amazon cada <b>{scan_minutes} minutos</b>",
        f"🏷️ Solo descuentos de <b>-{min_discount}% o más</b>, con precio comprobado",
        "🔔 Activa las notificaciones para no perderte nada",
        "",
        "¡Vamos con las ofertas! 👇",
        "",
        "#HadoukenZone #PS5 #NintendoSwitch #Xbox",
    ]
    if affiliate:
        lines += ["", f"<i>{AFFILIATE_NOTICE}</i>"]
    return "\n".join(lines)


def offer_caption(offer: Offer, url: str, affiliate: bool = True) -> str:
    tag = PLATFORM_TAGS.get(offer.platform, "#Videojuegos")
    lines = [
        f"🔥 <b>-{offer.discount_percent}%</b> · <b>{escape(offer.title)}</b>",
        "",
        f"🎮 {escape(offer.platform or '')}",
        f"💶 <b>{precio(offer.price)}</b>  <s>{precio(offer.previous_price)}</s>",
        f"💰 Te ahorras {precio(offer.savings)}",
        "",
        f'👉 <a href="{escape(url, quote=True)}">Ver oferta en Amazon</a>',
        "",
        f"{tag} #Oferta #HadoukenZone",
    ]
    if affiliate:
        lines.append("<i>Enlace de afiliado</i>")
    caption = "\n".join(lines)
    if len(caption) > 1024:                       # límite de pie de foto de Telegram
        short = escape(offer.title[:120] + "…")
        caption = caption.replace(f"<b>{escape(offer.title)}</b>", f"<b>{short}</b>")
    return caption


def test_message(min_discount: int = 15) -> str:
    return (
        "🎮 <b>¡Bienvenidos a HADOUKEN ZONE!</b>\n\n"
        "Aquí encontrarás las mejores ofertas de videojuegos para "
        "<b>PlayStation 5</b>, <b>Nintendo Switch</b> y <b>Xbox</b> en Amazon.\n\n"
        "🔎 Revisamos precios durante todo el día\n"
        f"🏷️ Solo descuentos de -{min_discount}% o más, comprobados\n"
        "🔔 Activa las notificaciones\n\n"
        "#HadoukenZone #PS5 #NintendoSwitch #Xbox"
    )
