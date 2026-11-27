"""Textos del canal (HTML de Telegram)."""

from __future__ import annotations

from datetime import date
from html import escape

from .models import Offer

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

PLATFORM_TAGS = {"PS5": "#PS5", "PS4": "#PS4", "Nintendo Switch": "#NintendoSwitch",
                 "Nintendo Switch 2": "#NintendoSwitch2", "Xbox": "#Xbox"}

AFFILIATE_NOTICE = "Como afiliado de Amazon, obtengo ingresos por las compras adscritas que cumplen los requisitos aplicables."

GOOD_MORNING_OPENINGS = [
    "☀️ <b>¡Buenos días, jugadores!</b>",
    "☀️ <b>¡Buenos días! Arriba, que hay ofertas que cazar.</b>",
    "☕ <b>¡Buenos días, Hadouken Zone!</b>",
    "🎮 <b>¡Buenos días! Mandos listos.</b>",
    "💥 <b>¡Buenos días, cazadores de chollos!</b>",
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
        f"Hoy es {fecha_larga(d)} y arrancamos la caza de ofertas de <b>PS5</b>, <b>PS4</b>, <b>Switch</b>, <b>Switch 2</b> y <b>Xbox</b>. 🕹️",
        "",
        f"🔎 Revisamos Amazon cada <b>{scan_minutes} minutos</b>",
        f"🏷️ Solo descuentos de <b>-{min_discount}% o más</b>, con precio comprobado",
        "🔔 Activa las notificaciones para no perderte nada",
        "",
        "¡Vamos con las ofertas! 👇",
        "",
        "#HadoukenZone #PS5 #PS4 #NintendoSwitch #NintendoSwitch2 #Xbox",
    ]
    if affiliate:
        lines += ["", f"<i>{AFFILIATE_NOTICE}</i>"]
    return "\n".join(lines)


GOOD_NIGHT_OPENINGS = [
    "🌙 <b>¡Buenas noches, jugadores!</b>",
    "😴 <b>Fin de la jornada en Hadouken Zone</b>",
    "🌙 <b>Mandos a cargar, que se acaba el día</b>",
    "💤 <b>¡A descansar, cazadores de chollos!</b>",
    "🌌 <b>Cerramos el día de ofertas</b>",
    "🛌 <b>Hora de guardar la partida</b>",
    "🌙 <b>¡Buenas noches, comunidad!</b>",
]
GOOD_NIGHT_CLOSINGS = [
    "Mañana a las 9:00 volvemos a la caza. 🎯",
    "Mañana más y mejor. ¡Que descanses! 💤",
    "Mañana seguimos buscando chollos. 🔎",
    "Deja las notificaciones activas: mañana hay más. 🔔",
    "Recarga energía, que mañana hay ofertas. ⚡",
]
SHORT_NAMES = {"Nintendo Switch": "Switch", "Nintendo Switch 2": "Switch 2"}
MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


def good_night_message(d: date, records: list[dict], top: int = 3) -> str:
    """Pie de la cabecera de buenas noches: resumen del día y aviso del hilo."""
    opening = GOOD_NIGHT_OPENINGS[d.toordinal() % len(GOOD_NIGHT_OPENINGS)]
    closing = GOOD_NIGHT_CLOSINGS[d.toordinal() % len(GOOD_NIGHT_CLOSINGS)]
    n = len(records)
    lines = [opening, ""]
    if n == 0:
        lines += ["Hoy no ha aparecido ninguna oferta que pase nuestro filtro. 🧐",
                  "Preferimos no publicar nada antes que publicar algo flojo."]
    else:
        best = max(records, key=lambda r: r.get("last_discount_percent") or 0)
        por_plat: dict[str, int] = {}
        for r in records:
            por_plat[r.get("platform") or "Otros"] = por_plat.get(r.get("platform") or "Otros", 0) + 1
        resumen = " · ".join(f"{SHORT_NAMES.get(p, p)} {c}" for p, c in
                             sorted(por_plat.items(), key=lambda x: -x[1]))
        lines += [f"📊 Hoy: <b>{n} oferta{'s' if n != 1 else ''}</b> ({resumen})",
                  f"💥 La mejor: <b>-{best.get('last_discount_percent')}%</b> en {escape(best.get('title') or '')}"]
        lines += ["", f"👇 Las {min(top, n)} mejores del día, aquí debajo" if min(top, n) > 1 else "👇 La mejor del día, aquí debajo"]
    lines += ["", closing, "", "#HadoukenZone #ResumenDelDía"]
    return "\n".join(lines)


def good_night_item(rank: int, offer: Offer, url: str, affiliate: bool = True) -> str:
    """Pie de cada oferta del hilo de buenas noches."""
    medal = MEDALS[rank - 1] if rank - 1 < len(MEDALS) else f"{rank}."
    lines = [
        f"{medal} <b>-{offer.discount_percent}%</b> · <b>{escape(offer.title)}</b>",
        f"🎮 {escape(offer.platform or '')} · 💶 <b>{precio(offer.price)}</b>  <s>{precio(offer.previous_price)}</s>",
        f'👉 <a href="{escape(url, quote=True)}">Ver oferta en Amazon</a>',
    ]
    if affiliate:
        lines.append("<i>Enlace de afiliado</i>")
    return "\n".join(lines)


def offer_caption(offer: Offer, url: str, affiliate: bool = True) -> str:
    tag = PLATFORM_TAGS.get(offer.platform, "#Videojuegos")
    lines = [
        f"💥 <b>-{offer.discount_percent}%</b> · <b>{escape(offer.title)}</b>",
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
        "<b>PS5</b>, <b>PS4</b>, <b>Nintendo Switch</b>, <b>Switch 2</b> y <b>Xbox</b> en Amazon.\n\n"
        "🔎 Revisamos precios durante todo el día\n"
        f"🏷️ Solo descuentos de -{min_discount}% o más, comprobados\n"
        "🔔 Activa las notificaciones\n\n"
        "#HadoukenZone #PS5 #PS4 #NintendoSwitch #NintendoSwitch2 #Xbox"
    )
