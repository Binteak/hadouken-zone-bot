"""
Generador de tarjetas de oferta (imagen 1280x720 con el estilo Hadouken Zone).

Incluye carátula, plataforma, precio anterior tachado, precio actual,
% de descuento y "Te ahorras X €". Solo necesita Pillow.

Uso desde Python:

    from hadouken_zone.cards import generar_tarjeta
    ruta = generar_tarjeta(
        titulo="Nombre del juego",
        plataforma="PS5",               # "PS5", "Nintendo Switch", "Switch 2"...
        precio_actual=29.99,
        precio_anterior=69.99,
        imagen="https://...jpg",        # URL, ruta local o bytes (opcional)
    )                                   # por defecto se guarda en data/tarjetas/

Prueba desde la terminal:

    py -m hadouken_zone.cards --titulo "Mi juego" --plataforma PS5 --actual 29.99 --anterior 69.99
"""
from __future__ import annotations

import io
import math
import os
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .config import CARDS_DIR as CARDS_OUTPUT_DIR, FONTS_DIR as FONTS, MASCOT_DIR

MASCOT_FILE = MASCOT_DIR / "mascota_cabeza.png"

W, H = 1280, 720

# Paleta Hadouken Zone
BG_LIGHT = (92, 76, 150)
BG_DARK = (26, 21, 48)
INK = (22, 16, 40)
CYAN = (82, 222, 245)
ORANGE = (255, 128, 36)
YELLOW = (255, 214, 64)
WHITE = (255, 255, 255)
LILAC = (190, 180, 225)

PLATAFORMAS = {
    "ps5": ("PS5", (0, 112, 224)),
    "playstation 5": ("PS5", (0, 112, 224)),
    "ps4": ("PS4", (0, 82, 180)),
    "switch 2": ("SWITCH 2", (228, 0, 20)),
    "nintendo switch 2": ("SWITCH 2", (228, 0, 20)),
    "switch": ("SWITCH", (228, 0, 20)),
    "nintendo switch": ("SWITCH", (228, 0, 20)),
}


# ---------------------------------------------------------------- utilidades
def _font(nombre: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONTS / nombre), size)
    except OSError:
        # Fallback a fuentes de Windows si falta branding/fuentes/
        for f in ("arialbd.ttf", "seguisb.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                pass
        return ImageFont.load_default()


def F_TITULAR(s):  return _font("InterDisplay-BlackItalic.otf", s)
def F_FUERTE(s):   return _font("Inter-ExtraBold.otf", s)
def F_TEXTO(s):    return _font("Inter-Bold.otf", s)


def precio_es(valor: float) -> str:
    """29.9 -> '29,90 €'"""
    entero, dec = f"{valor:,.2f}".split(".")
    return f"{entero.replace(',', '.')},{dec} €"


def _cargar_imagen(imagen) -> Image.Image | None:
    if imagen is None:
        return None
    try:
        if isinstance(imagen, Image.Image):
            return imagen.convert("RGBA")
        if isinstance(imagen, (bytes, bytearray)):
            return Image.open(io.BytesIO(imagen)).convert("RGBA")
        s = str(imagen)
        if s.startswith(("http://", "https://")):
            req = urllib.request.Request(s, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return Image.open(io.BytesIO(r.read())).convert("RGBA")
        return Image.open(s).convert("RGBA")
    except Exception as e:  # nunca romper la publicación por una imagen
        print(f"[tarjeta] No se pudo cargar la imagen: {e}")
        return None


def _fondo() -> Image.Image:
    """Degradado radial morado + rayos de velocidad + trama de puntos."""
    small = Image.new("RGB", (W // 4, H // 4))
    px = small.load()
    cx, cy, R = 300 / 4, 330 / 4, 1000 / 4
    for y in range(small.height):
        for x in range(small.width):
            t = min(1.0, math.hypot(x - cx, y - cy) / R) ** 1.2
            px[x, y] = tuple(int(BG_LIGHT[i] * (1 - t) + BG_DARK[i] * t) for i in range(3))
    img = small.resize((W, H), Image.BICUBIC).convert("RGBA")

    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    rnd = random.Random(7)
    L = math.hypot(W, H)
    for _ in range(90):
        a = rnd.uniform(0, 2 * math.pi)
        s = rnd.uniform(0.004, 0.016)
        d.polygon([(cx * 4, cy * 4),
                   (cx * 4 + L * math.cos(a - s), cy * 4 + L * math.sin(a - s)),
                   (cx * 4 + L * math.cos(a + s), cy * 4 + L * math.sin(a + s))],
                  fill=(255, 255, 255, rnd.randint(7, 16)))
    for yy in range(0, 260, 20):          # trama arriba a la derecha
        for xx in range(W - 420, W, 20):
            t = ((xx - (W - 420)) / 420 + (1 - yy / 260)) / 2
            r = 5 * t
            if r > 0.5:
                d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 255, 255, 22))
    img.alpha_composite(capa)
    return img


def _glow(img, centro, radio, color, fuerza=140):
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cx, cy = centro
    ImageDraw.Draw(capa).ellipse((cx - radio, cy - radio, cx + radio, cy + radio), fill=color + (fuerza,))
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(radio * 0.45)))


def _texto(img, xy, txt, fnt, fill=WHITE, ink=10, sombra=CYAN, off=(6, 7), anchor="la"):
    """Texto estilo pegatina: trazo oscuro grueso + sombra de color desplazada."""
    d = ImageDraw.Draw(img)
    if sombra:
        d.text((xy[0] + off[0], xy[1] + off[1]), txt, font=fnt, fill=sombra,
               stroke_width=ink, stroke_fill=sombra, anchor=anchor)
    d.text(xy, txt, font=fnt, fill=fill, stroke_width=ink, stroke_fill=INK, anchor=anchor)
    return d.textbbox(xy, txt, font=fnt, stroke_width=ink, anchor=anchor)


def _estrella(size, texto, fill=YELLOW, puntas=14):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2

    def pts(R):
        return [(c + R * (1 if i % 2 == 0 else .84) * math.cos(math.pi * i / puntas - .2),
                 c + R * (1 if i % 2 == 0 else .84) * math.sin(math.pi * i / puntas - .2))
                for i in range(puntas * 2)]
    d.polygon(pts(size / 2 - 2), fill=INK)
    d.polygon(pts(size / 2 - 12), fill=fill)
    fs = 10
    while fs < size and F_TITULAR(fs + 2).getlength(texto) < size * 0.62:
        fs += 2
    d.text((c, c + 2), texto, font=F_TITULAR(fs), fill=INK, anchor="mm")
    return img.rotate(-8, resample=Image.BICUBIC)


def _ajustar_titulo(titulo, ancho, max_lineas=3):
    for size in (60, 54, 48, 44, 40, 36):
        f = F_TITULAR(size)
        palabras, lineas, actual = titulo.split(), [], ""
        for p in palabras:
            prueba = (actual + " " + p).strip()
            if f.getlength(prueba) + 16 <= ancho:
                actual = prueba
            else:
                if actual:
                    lineas.append(actual)
                actual = p
        if actual:
            lineas.append(actual)
        if len(lineas) <= max_lineas and all(f.getlength(l) + 16 <= ancho for l in lineas):
            return f, lineas, size
    # recortar con "…"
    lineas = lineas[:max_lineas]
    while f.getlength(lineas[-1] + "…") + 16 > ancho and " " in lineas[-1]:
        lineas[-1] = lineas[-1].rsplit(" ", 1)[0]
    lineas[-1] += "…"
    return f, lineas, size


# ---------------------------------------------------------------- tarjeta
def generar_tarjeta(titulo: str, plataforma: str, precio_actual: float,
                    precio_anterior: float | None = None, descuento: int | None = None,
                    imagen=None, salida: str | None = None, etiqueta: str | None = None) -> str:
    """Genera la tarjeta y devuelve la ruta del archivo creado.

    Si no se indica salida, se guarda en data/tarjetas/<titulo>.jpg
    """
    if salida is None:
        nombre = "".join(c if c.isalnum() else "_" for c in titulo.lower())[:60].strip("_")
        salida = CARDS_OUTPUT_DIR / f"{nombre or 'tarjeta'}.jpg"
    if descuento is None and precio_anterior and precio_anterior > precio_actual:
        descuento = round((1 - precio_actual / precio_anterior) * 100)

    img = _fondo()
    _glow(img, (300, 340), 260, ORANGE, 110)

    # --- Carátula (izquierda)
    cx0, cy0, cw, ch = 80, 70, 420, 540
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((cx0 + 12, cy0 + 14, cx0 + cw + 12, cy0 + ch + 14), 28, fill=CYAN)
    d.rounded_rectangle((cx0 - 8, cy0 - 8, cx0 + cw + 8, cy0 + ch + 8), 30, fill=INK)
    d.rounded_rectangle((cx0, cy0, cx0 + cw, cy0 + ch), 24, fill=WHITE)
    cover = _cargar_imagen(imagen)
    if cover is not None:
        cover = ImageOps.contain(cover, (cw - 36, ch - 36), Image.LANCZOS)
        img.alpha_composite(cover, (cx0 + (cw - cover.width) // 2, cy0 + (ch - cover.height) // 2))
    else:
        cab = MASCOT_FILE
        if cab.exists():
            h = Image.open(cab).convert("RGBA")
            h = ImageOps.contain(h, (cw - 80, ch - 80), Image.LANCZOS)
            img.alpha_composite(h, (cx0 + (cw - h.width) // 2, cy0 + (ch - h.height) // 2))

    # --- Estrella de descuento
    if descuento:
        st = _estrella(210, f"-{descuento}%")
        img.alpha_composite(st, (cx0 + cw - 165, cy0 - 55))

    # --- Columna derecha
    x = 600
    ancho = W - x - 60
    d = ImageDraw.Draw(img)
    clave = (plataforma or "").strip().lower()
    nombre_plat, color_plat = PLATAFORMAS.get(clave, ((plataforma or "").upper(), (90, 90, 140)))
    y = 82
    if nombre_plat:
        f = F_FUERTE(30)
        wpl = int(f.getlength(nombre_plat)) + 56
        d.rounded_rectangle((x - 5, y - 5, x + wpl + 5, y + 57), 32, fill=INK)
        d.rounded_rectangle((x, y, x + wpl, y + 52), 28, fill=color_plat)
        d.text((x + wpl / 2, y + 27), nombre_plat, font=f, fill=WHITE, anchor="mm")
    if etiqueta:
        f = F_FUERTE(26)
        xe = x + (wpl + 24 if nombre_plat else 0)
        we = int(f.getlength(etiqueta)) + 44
        d.rounded_rectangle((xe - 5, y - 5, xe + we + 5, y + 57), 32, fill=INK)
        d.rounded_rectangle((xe, y, xe + we, y + 52), 28, fill=YELLOW)
        d.text((xe + we / 2, y + 27), etiqueta, font=f, fill=INK, anchor="mm")

    y += 84
    f, lineas, size = _ajustar_titulo(titulo, ancho)
    for linea in lineas:
        _texto(img, (x, y), linea, f, ink=7, sombra=None)
        y += int(size * 1.12)

    # Precios anclados abajo
    yp = 398
    d = ImageDraw.Draw(img)
    if precio_anterior and precio_anterior > precio_actual:
        f = F_TEXTO(34)
        d.text((x, yp), "ANTES", font=F_FUERTE(22), fill=LILAC)
        txt = precio_es(precio_anterior)
        tx = x + 100
        d.text((tx, yp - 8), txt, font=f, fill=LILAC)
        tw = f.getlength(txt)
        d.line((tx - 4, yp + 13, tx + tw + 4, yp + 9), fill=(255, 80, 70), width=5)
    _texto(img, (x - 4, yp + 36), precio_es(precio_actual), F_TITULAR(118),
           fill=YELLOW, ink=11, sombra=ORANGE, off=(7, 8))
    if precio_anterior and precio_anterior > precio_actual:
        ahorro = precio_anterior - precio_actual
        d = ImageDraw.Draw(img)
        d.text((x, yp + 192), f"Te ahorras {precio_es(ahorro)}", font=F_TEXTO(30), fill=CYAN)

    # --- Pie con marca
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 70, W, H), fill=(18, 13, 34))
    d.rectangle((0, H - 74, W, H - 70), fill=CYAN)
    cab = MASCOT_FILE
    if cab.exists():
        h = Image.open(cab).convert("RGBA")
        h = h.resize((int(h.width * 82 / h.height), 82), Image.LANCZOS)
        img.alpha_composite(h, (W - h.width - 28, H - 92))
    d.text((80, H - 35), "HADOUKEN ZONE", font=F_TITULAR(34), fill=WHITE, anchor="lm")
    d.text((80 + F_TITULAR(34).getlength("HADOUKEN ZONE") + 24, H - 35),
           "Ofertas verificadas de PS5 y Switch", font=F_TEXTO(24), fill=LILAC, anchor="lm")

    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    out = img.convert("RGB")
    if str(salida).lower().endswith(".png"):
        out.save(salida)
    else:
        out.save(salida, quality=92, optimize=True)
    return str(salida)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Genera una tarjeta de oferta Hadouken Zone")
    p.add_argument("--titulo", required=True)
    p.add_argument("--plataforma", default="PS5")
    p.add_argument("--actual", type=float, required=True)
    p.add_argument("--anterior", type=float)
    p.add_argument("--descuento", type=int)
    p.add_argument("--imagen")
    p.add_argument("--etiqueta", help='Texto extra, p.ej. "MÍNIMO HISTÓRICO"')
    p.add_argument("--salida", help="Ruta del archivo (por defecto data/tarjetas/)")
    a = p.parse_args()
    print(generar_tarjeta(a.titulo, a.plataforma, a.actual, a.anterior, a.descuento,
                          a.imagen, a.salida, a.etiqueta))
