"""Utilidades de diseño Hadouken Zone: paleta, fondos, texto con contorno, pegatinas."""
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BRANDING = ROOT / 'branding'
MASCOTA = BRANDING / 'mascota'
FUENTES = BRANDING / 'fuentes'

# Paleta sacada de los originales
BG = (55, 47, 88)
BG_DARK = (26, 21, 48)
BG_LIGHT = (78, 66, 128)
INK = (22, 16, 40)          # contorno oscuro (como el trazo de la mascota)
CYAN = (82, 222, 245)
ORANGE = (255, 128, 36)
RED = (232, 54, 46)
YELLOW = (255, 214, 64)
WHITE = (255, 255, 255)
PS_BLUE = (0, 112, 224)
SW_RED = (228, 0, 20)

def font(size, w='Black', italic=True, display=True):
    name = ('InterDisplay-' if display else 'Inter-') + w + ('Italic' if italic else '') + '.otf'
    return ImageFont.truetype(str(FUENTES / name), size)


def radial_bg(w, h, center=None, inner=BG_LIGHT, outer=BG_DARK, radius=None):
    cx, cy = center or (w / 2, h / 2)
    radius = radius or math.hypot(w, h) * 0.6
    y, x = np.mgrid[0:h, 0:w]
    t = np.clip(np.hypot(x - cx, y - cy) / radius, 0, 1) ** 1.2
    a = np.array(inner)[None, None] * (1 - t[..., None]) + np.array(outer)[None, None] * t[..., None]
    return Image.fromarray(a.astype('uint8'), 'RGB').convert('RGBA')


def speed_lines(img, center, n=70, color=(255, 255, 255), alpha=18, seed=3, inner=0.0):
    """Rayos radiales tipo manga desde un punto."""
    w, h = img.size
    rnd = random.Random(seed)
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    R = math.hypot(w, h)
    for i in range(n):
        ang = rnd.uniform(0, 2 * math.pi)
        spread = rnd.uniform(0.004, 0.018)
        r0 = R * inner
        pts = [(center[0] + r0 * math.cos(ang), center[1] + r0 * math.sin(ang)),
               (center[0] + R * math.cos(ang - spread), center[1] + R * math.sin(ang - spread)),
               (center[0] + R * math.cos(ang + spread), center[1] + R * math.sin(ang + spread))]
        d.polygon(pts, fill=color + (rnd.randint(alpha // 2, alpha),))
    img.alpha_composite(layer)


def halftone(img, box, spacing=18, rmax=4, color=(255, 255, 255), alpha=28, direction='tl'):
    """Trama de puntos que se desvanece."""
    x0, y0, x1, y1 = box
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for yy in range(y0, y1, spacing):
        for xx in range(x0, x1, spacing):
            if direction == 'tl':
                t = 1 - ((xx - x0) / (x1 - x0) + (yy - y0) / (y1 - y0)) / 2
            elif direction == 'br':
                t = ((xx - x0) / (x1 - x0) + (yy - y0) / (y1 - y0)) / 2
            elif direction == 'r':
                t = (xx - x0) / (x1 - x0)
            else:
                t = 1 - (xx - x0) / (x1 - x0)
            r = rmax * max(0, t)
            if r > 0.4:
                d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=color + (alpha,))
    img.alpha_composite(layer)


def glow(img, center, radius, color, strength=200):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color + (strength,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.45))
    img.alpha_composite(layer)


def outline_alpha(alpha, px):
    return alpha.filter(ImageFilter.MaxFilter(px * 2 + 1)) if px < 8 else _dilate(alpha, px)


def _dilate(alpha, px):
    a = np.array(alpha) > 40
    from scipy import ndimage
    yy, xx = np.ogrid[-px:px + 1, -px:px + 1]
    k = xx ** 2 + yy ** 2 <= px ** 2
    out = ndimage.binary_dilation(a, structure=k)
    return Image.fromarray((out * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1))


def sticker_text(img, xy, text, fnt, fill=WHITE, ink=INK, ink_w=10, accent=CYAN, accent_off=(6, 7),
                 anchor='la', glow_color=None):
    """Texto con trazo oscuro grueso + sombra de color desplazada (estilo de la mascota)."""
    w, h = img.size
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).text(xy, text, font=fnt, fill=255, anchor=anchor)
    outer = _dilate(m, ink_w)
    if glow_color:
        g = Image.new('RGBA', img.size, glow_color + (0,))
        g.putalpha(_dilate(m, ink_w + 6).filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.8)))
        img.alpha_composite(g)
    if accent:
        acc = Image.new('RGBA', img.size, accent + (255,))
        sh = ImageChops.offset(outer, *accent_off)
        layer.paste(acc, (0, 0), sh)
    layer.paste(Image.new('RGBA', img.size, ink + (255,)), (0, 0), outer)
    if isinstance(fill, tuple):
        layer.paste(Image.new('RGBA', img.size, fill + (255,)), (0, 0), m)
    else:  # gradiente vertical (lista de 2 colores)
        bbox = m.getbbox()
        grad = vgrad(img.size, fill[0], fill[1], bbox[1], bbox[3])
        layer.paste(grad, (0, 0), m)
    img.alpha_composite(layer)
    return ImageDraw.Draw(m).textbbox(xy, text, font=fnt, anchor=anchor)


def vgrad(size, c0, c1, y0=0, y1=None):
    w, h = size
    y1 = y1 or h
    t = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    a = np.array(c0)[None, None] * (1 - t) + np.array(c1)[None, None] * t
    a = np.broadcast_to(a, (h, w, 3))
    return Image.fromarray(a.astype('uint8'), 'RGB').convert('RGBA')


def paste_sticker(img, src, xy, height=None, ink_w=0, white_w=0, shadow=True, rotate=0):
    """Pega un PNG con alfa; opcionalmente con borde blanco tipo pegatina y sombra."""
    s = src
    if height:
        s = s.resize((round(s.width * height / s.height), height), Image.LANCZOS)
    if rotate:
        s = s.rotate(rotate, resample=Image.BICUBIC, expand=True)
    pad = max(ink_w, white_w) + 20
    canvas = Image.new('RGBA', (s.width + pad * 2, s.height + pad * 2), (0, 0, 0, 0))
    a = Image.new('L', canvas.size, 0)
    a.paste(s.getchannel('A'), (pad, pad))
    if shadow:
        sh = Image.new('RGBA', canvas.size, (8, 4, 20, 0))
        sh.putalpha(_dilate(a, max(white_w, 2)).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .55)))
        img.alpha_composite(sh, (xy[0] - pad + 8, xy[1] - pad + 12))
    if white_w:
        canvas.paste(Image.new('RGBA', canvas.size, WHITE + (255,)), (0, 0), _dilate(a, white_w))
    canvas.alpha_composite(s, (pad, pad))
    img.alpha_composite(canvas, (xy[0] - pad, xy[1] - pad))
    return s.size


BOLT = [(0.62, 0), (0.08, 0.6), (0.44, 0.6), (0.30, 1), (0.92, 0.36), (0.56, 0.36), (0.80, 0)]
def bolt(d, x, y, s, fill=YELLOW, ink=INK, ink_w=3):
    P = [(x + px * s * 0.75, y + py * s) for px, py in BOLT]
    d.polygon(P, fill=fill)
    d.line(P + [P[0]], fill=ink, width=ink_w, joint='curve')


def starburst(size, points=16, r_out=1.0, r_in=0.82, fill=YELLOW, ink=INK, ink_w=8, rot=0):
    w = h = size
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2
    R = size / 2 - ink_w - 2
    pts = []
    for i in range(points * 2):
        r = R * (r_out if i % 2 == 0 else r_in)
        a = math.pi * i / points + math.radians(rot)
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=ink)
    # interior
    pts2 = []
    for i in range(points * 2):
        r = (R - ink_w) * (r_out if i % 2 == 0 else r_in)
        a = math.pi * i / points + math.radians(rot)
        pts2.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts2, fill=fill)
    return img


def pill(img, box, fill, text, fnt, txt=WHITE, ink=INK, ink_w=5, radius=None):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    radius = radius or (y1 - y0) // 2
    d.rounded_rectangle((x0 - ink_w, y0 - ink_w, x1 + ink_w, y1 + ink_w), radius + ink_w, fill=ink)
    d.rounded_rectangle(box, radius, fill=fill)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 1), text, font=fnt, fill=txt, anchor='mm')


# Etiquetas de plataforma de la cabecera: las mismas que las tarjetas (hadouken_zone/cards.py)
PLATAFORMAS_FILAS = (("ps5", "ps4", "xbox"), ("switch", "switch 2"))


def etiquetas_plataforma(img, x, y, filas=PLATAFORMAS_FILAS, sep=18, salto=80):
    """Dibuja las etiquetas de plataforma en filas y devuelve el borde derecho más lejano."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from hadouken_zone.cards import PLATAFORMAS, _etiqueta_plataforma
    d = ImageDraw.Draw(img)
    derecha = x
    for i, fila in enumerate(filas):
        xx = x
        for clave in fila:
            nombre, color, tinta = PLATAFORMAS[clave]
            xx += _etiqueta_plataforma(d, xx, y + i * salto, nombre, color, tinta) + sep
        derecha = max(derecha, xx - sep)
    return derecha


def load(name):
    return Image.open(MASCOTA / name).convert('RGBA')


def save(img, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert('RGB').save(path, quality=95) if path.suffix == '.jpg' else img.save(path)
    print('  ->', path.relative_to(ROOT), img.size)
