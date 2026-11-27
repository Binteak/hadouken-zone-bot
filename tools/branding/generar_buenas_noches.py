"""Genera la cabecera de "Buenas noches" (branding/telegram/cabeceras/cabecera_buenas_noches.png).

Parte de la cabeza de la mascota (branding/mascota/mascota_cabeza.png): le cierra los
ojos, relaja las cejas, añade coloretes y la inclina. Fondo nocturno con estrellas,
luna creciente y "Z z z" que no pisan ni la cabeza ni la luna.

    py tools/branding/generar_buenas_noches.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hadouken_zone import cards  # noqa: E402
from hadouken_zone.cards import H, W, _etiqueta_plataforma, _fondo  # noqa: E402

B = ROOT / "branding"
SALIDA = B / "telegram" / "cabeceras" / "cabecera_buenas_noches.png"
F = lambda n, s: ImageFont.truetype(str(B / "fuentes" / n), s)  # noqa: E731
INK = (8, 6, 28)
CYAN = (84, 226, 248)


def cabeza_dormida() -> Image.Image:
    head = Image.open(B / "mascota" / "mascota_cabeza.png").convert("RGBA")
    a = np.array(head).astype(float)
    bg = np.array([52, 40, 90.0])
    dist = np.sqrt(((a[..., :3] - bg) ** 2).sum(-1))
    a[..., 3] = np.clip((dist - 18) / 22, 0, 1) * 255          # fondo fuera, borde suave

    # tapar ojos y cejas con la piel de debajo de los ojos
    mk = Image.new("L", head.size, 0)
    ImageDraw.Draw(mk).polygon([(650, 712), (905, 698), (925, 762), (1000, 748), (1040, 708),
                                (1212, 726), (1220, 902), (654, 906)], fill=255)
    m = np.array(mk.filter(ImageFilter.GaussianBlur(2.5)))[..., None] / 255.0
    piel = a.copy()
    fila = a[945, :, :3]
    for y in range(680, 915):
        piel[y, :, :3] = np.minimum(255, fila + np.array([0, 14, 30]) * (915 - y) / 235)
    a[..., :3] = piel[..., :3] * m + a[..., :3] * (1 - m)
    head = Image.fromarray(a.clip(0, 255).astype("uint8"))

    for box in [(645, 830, 765, 925), (1112, 845, 1212, 925)]:       # coloretes
        capa = Image.new("RGBA", head.size, (0, 0, 0, 0))
        ImageDraw.Draw(capa).ellipse(box, fill=(255, 150, 110, 150))
        head.alpha_composite(capa.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(head)
    d.arc((680, 640, 880, 760), 200, 330, fill=INK, width=22)       # cejas relajadas
    d.arc((1055, 650, 1215, 770), 210, 335, fill=INK, width=22)
    d.arc((690, 760, 880, 860), 20, 160, fill=INK, width=24)        # ojos cerrados
    d.arc((1060, 770, 1210, 860), 20, 160, fill=INK, width=24)
    for x0, y0 in [(702, 812), (737, 832), (1072, 822)]:            # pestañas
        d.line((x0, y0, x0 - 22, y0 + 18), fill=INK, width=12)
    d.ellipse((960, 980, 1010, 1015), fill=(255, 239, 133))         # boca relajada
    d.arc((955, 975, 1015, 1025), 0, 180, fill=INK, width=12)
    head = ImageOps.mirror(head)                                     # mira hacia el texto
    head = head.rotate(8, expand=True, resample=Image.BICUBIC)
    return head.crop(head.getbbox())


def luna(img: Image.Image, cx: int, cy: int, r: int) -> tuple:
    """Luna creciente de verdad (transparente por dentro) con un halo suave."""
    m = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(m)
    md.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    md.ellipse((cx - r + int(r * .55), cy - r - int(r * .2), cx + r + int(r * .55), cy + r - int(r * .2)), fill=0)
    halo = Image.new("RGBA", (W, H), (255, 236, 170, 0))
    halo.putalpha(m.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .45)))
    img.alpha_composite(halo)
    img.paste(Image.new("RGBA", (W, H), (255, 236, 170, 255)), (0, 0), m)
    return (cx - r, cy - r, cx + r, cy + r)


def generar(salida: Path = SALIDA) -> Path:
    img = _fondo(trama=False)
    img.alpha_composite(Image.new("RGBA", (W, H), (6, 4, 26, 135)))
    d = ImageDraw.Draw(img)
    rnd = random.Random(5)
    for _ in range(110):                                             # estrellas
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.choice([1, 1, 2, 2, 3])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randint(80, 220)))
    moon = luna(img, 1190, 95, 58)

    m = ImageOps.contain(cabeza_dormida(), (560, 520), Image.LANCZOS)
    mx, my = W - m.width + 60, H - m.height - 26                   # las cintas salen por la derecha
    img.alpha_composite(m, (mx, my))
    ocupado = Image.new("L", (W, H), 0)
    ocupado.paste(m.split()[3], (mx, my))
    ImageDraw.Draw(ocupado).ellipse(moon, fill=255)
    ocupado = ocupado.filter(ImageFilter.MaxFilter(21))             # margen de seguridad

    # "Z z z": de pequeña a grande, una detrás de otra, sin pisar cabeza ni luna
    x, y = mx + 150, my - 10
    for s in (30, 40, 52):
        while True:
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(capa).text((x, y - s), "Z", font=F("InterDisplay-BlackItalic.otf", s),
                                      fill=(255, 255, 255), stroke_width=4, stroke_fill=INK)
            choque = np.array(capa.split()[3]).astype(bool) & np.array(ocupado).astype(bool)
            if not choque.any():
                break
            y -= 6
        img.alpha_composite(capa)
        x, y = x + int(s * 1.1), y - int(s * 0.95)

    d = ImageDraw.Draw(img)

    def txt(xy, t, f, fill, sw=8):
        d.text(xy, t, font=f, fill=fill, stroke_width=sw, stroke_fill=(22, 16, 40))
    txt((70, 105), "¡A DESCANSAR, JUGADORES!", F("Inter-ExtraBold.otf", 40), CYAN, sw=5)
    txt((60, 165), "BUENAS", F("InterDisplay-BlackItalic.otf", 128), (255, 128, 36))
    txt((60, 300), "NOCHES", F("InterDisplay-BlackItalic.otf", 128), (255, 245, 230))
    d.text((72, 462), "Resumen de las ofertas de hoy", font=F("Inter-Bold.otf", 32), fill=(255, 255, 255))
    P = cards.PLATAFORMAS
    for fila, claves in ((525, ["ps5", "ps4", "xbox"]), (605, ["switch", "switch 2"])):
        x = 72
        for k in claves:
            n, c, t = P[k]
            x += _etiqueta_plataforma(d, x, fila, n, c, t) + 18
    d.rectangle((0, H - 8, W, H), fill=(255, 128, 36))
    salida.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(salida)
    return salida


if __name__ == "__main__":
    print(generar())
