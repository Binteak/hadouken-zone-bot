"""Genera todos los diseños del canal de Telegram con el estilo Hadouken Zone.

Salida en branding/telegram/:
    avatar/          avatar_morado_640.png, avatar_naranja_640.png
    publicaciones/   bienvenida_1280x720.png
    cabeceras/       buenos días (la usa el bot cada mañana), chollo del día, oferta flash,
                     top semana, especial PS5 / Switch
    stickers/        4 stickers 512x512 (formato de Telegram)
    tarjetas_ejemplo/ dos tarjetas de oferta de muestra (carátulas inventadas)

Requisito previo: branding/mascota/ (ver mejorar_mascota.py).
Uso:  python tools/branding/generar_disenos.py
"""
import sys

from PIL import ImageOps

from hzlib import *
from hzlib import _dilate

TG = BRANDING / 'telegram'
head = load('mascota_cabeza.png')
had = load('mascota_hadouken.png')


def bienvenida():
    W, H = 1280, 720
    img = radial_bg(W, H, center=(980, 380), inner=(92, 76, 150), outer=BG_DARK, radius=900)
    speed_lines(img, (930, 330), n=90, alpha=16)
    halftone(img, (0, 0, 560, 400), spacing=20, rmax=5, alpha=22, direction='tl')
    glow(img, (760, 360), 210, ORANGE, 150)
    glow(img, (760, 360), 90, YELLOW, 200)

    paste_sticker(img, had, (W - 760, H - 470 + 4), height=470 + 30, shadow=True)

    # Titular
    y = 70
    sticker_text(img, (70, y), 'BIENVENIDO A', font(46), fill=CYAN, ink_w=7, accent=None)
    sticker_text(img, (64, y + 52), 'HADOUKEN', font(124), fill=[WHITE, (255, 236, 190)], ink_w=12,
                 accent=ORANGE, accent_off=(7, 9))
    sticker_text(img, (64, y + 182), 'ZONE', font(124), fill=[YELLOW, ORANGE], ink_w=12,
                 accent=CYAN, accent_off=(7, 9))

    # Plataformas
    f = font(30, 'ExtraBold', italic=False, display=False)
    pill(img, (76, 410, 236, 462), PS_BLUE, 'PS5', f)
    pill(img, (262, 410, 472, 462), SW_RED, 'SWITCH', f)

    # Ventajas
    d = ImageDraw.Draw(img)
    fb = font(30, 'Bold', italic=False, display=False)
    items = ['Descuentos de -15% o más', 'Precios comprobados', 'Enlace directo a la oferta']
    yy = 500
    for t in items:
        bolt(d, 76, yy - 1, 36)
        d.text((118, yy), t, font=fb, fill=WHITE)
        yy += 52

    # Pie
    d.rectangle((0, H - 8, W, H), fill=CYAN)
    save(img, TG / 'publicaciones' / 'bienvenida_1280x720.png')


# ======================================================== avatares y cabeceras
# ---------- AVATAR 640 (Telegram recorta en círculo) ----------
def avatar(path, inner, outer, glowc, ring):
    S = 640
    img = radial_bg(S, S, center=(S * .55, S * .5), inner=inner, outer=outer, radius=420)
    speed_lines(img, (S * .55, S * .48), n=60, alpha=22, seed=9)
    glow(img, (S * .58, S * .5), 200, glowc, 120)
    # cabeza encajada en el círculo
    paste_sticker(img, head, (60, 92), height=470, shadow=True)
    # máscara circular + anillo
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, S - 1, S - 1), fill=255)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(out)
    d.ellipse((6, 6, S - 7, S - 7), outline=INK, width=14)
    d.ellipse((12, 12, S - 13, S - 13), outline=ring, width=7)
    # Se sube la versión cuadrada (Telegram ya la recorta en círculo).
    # La circular con anillo sirve como vista previa / para otras redes.
    save(img, path)


def avatares():
    avatar(TG / 'avatar' / 'avatar_morado_640.png', (96, 80, 160), BG_DARK, ORANGE, CYAN)
    avatar(TG / 'avatar' / 'avatar_naranja_640.png', (255, 176, 72), (214, 66, 40), YELLOW, YELLOW)


# ---------- CABECERAS 1280x720 ----------
def header(path, kicker, l1, l2, c1, c2, accent, sub=None, pose='head', burst=ORANGE, pills=None, bolts=False):
    W, H = 1280, 720
    img = radial_bg(W, H, center=(960, 360), inner=(92, 76, 150), outer=BG_DARK, radius=900)
    speed_lines(img, (960, 360), n=90, alpha=16, seed=len(l1))
    halftone(img, (0, 380, 620, 720), spacing=20, rmax=5, alpha=20, direction='l')
    glow(img, (960, 360), 260, burst, 120)
    if pose == 'head':
        paste_sticker(img, head, (770, 150), height=460, shadow=True)
    else:
        paste_sticker(img, had, (W - 700, H - 470), height=470, shadow=True)
    y = 120
    sticker_text(img, (72, y), kicker, font(44), fill=accent, ink_w=7, accent=None)
    sticker_text(img, (64, y + 52), l1, font(112), fill=c1, ink_w=12, accent=accent, accent_off=(7, 9))
    if l2:
        sticker_text(img, (64, y + 168), l2, font(112), fill=c2, ink_w=12, accent=CYAN if accent != CYAN else ORANGE, accent_off=(7, 9))
    d = ImageDraw.Draw(img)
    yb = y + (318 if l2 else 190)
    if sub:
        fb = font(30, 'Bold', italic=False, display=False)
        x = 72
        if bolts:
            bolt(d, x, yb + 2, 40); x += 48
        d.text((x, yb), sub, font=fb, fill=WHITE)
        yb += 70
    if pills:
        f = font(30, 'ExtraBold', italic=False, display=False)
        x = 76
        for label, col in pills:
            w = 60 + len(label) * 22
            pill(img, (x, yb, x + w, yb + 52), col, label, f)
            x += w + 26
    d.rectangle((0, H - 8, W, H), fill=accent)
    save(img, path)

def cabeceras():
    O = TG / 'cabeceras'
    header(O / 'cabecera_buenos_dias.png', '¡ARRIBA, JUGADORES!', 'BUENOS', 'DÍAS', [YELLOW, ORANGE], [WHITE, (255, 236, 190)],
           ORANGE, sub='Empieza la caza de ofertas', pose='hadouken', burst=YELLOW,
           pills=[('PS5', PS_BLUE), ('SWITCH', SW_RED)])
    header(O / 'cabecera_chollo_del_dia.png', 'HADOUKEN ZONE', 'CHOLLO', 'DEL DÍA', [WHITE, (255, 236, 190)], [YELLOW, ORANGE],
           ORANGE, sub='La mejor oferta de hoy, verificada', pose='hadouken')
    header(O / 'cabecera_oferta_flash.png', '¡SOLO UNAS HORAS!', 'OFERTA', 'FLASH', [WHITE, (255, 236, 190)], [YELLOW, ORANGE],
           YELLOW, sub='Corre, que vuela', bolts=True, burst=YELLOW)
    header(O / 'cabecera_top_semana.png', 'RESUMEN SEMANAL', 'TOP 5', 'OFERTAS', [YELLOW, ORANGE], [WHITE, (255, 236, 190)],
           CYAN, sub='Lo más gordo de los últimos 7 días', pose='hadouken', burst=CYAN)
    header(O / 'cabecera_especial_ps5.png', 'ESPECIAL', 'PS5', 'OFERTAS', [WHITE, (200, 225, 255)], [WHITE, (200, 225, 255)],
           CYAN, sub='Juegos de PlayStation 5 rebajados', burst=PS_BLUE, pills=[('PS5', PS_BLUE)])
    header(O / 'cabecera_especial_switch.png', 'ESPECIAL', 'SWITCH', 'OFERTAS', [WHITE, (255, 215, 215)], [WHITE, (255, 215, 215)],
           RED, sub='Juegos de Nintendo Switch rebajados', burst=SW_RED, pills=[('SWITCH', SW_RED)])


# ======================================================== stickers
S = 512


def finish(c0, path):
    c = Image.new('RGBA', (1100, 1100), (0, 0, 0, 0)); c.alpha_composite(c0, (100, 100))
    """Borde blanco grueso + sombra suave alrededor de todo el sticker."""
    a = c.getchannel('A').point(lambda v: 255 if v > 200 else 0)
    white = _dilate(a, 9)
    out = Image.new('RGBA', c.size, (0, 0, 0, 0))
    sh = Image.new('RGBA', c.size, (10, 5, 25, 0))
    sh.putalpha(ImageChops.offset(white, 3, 5).filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * .45)))
    out.alpha_composite(sh)
    out.paste(Image.new('RGBA', c.size, WHITE + (255,)), (0, 0), white)
    out.alpha_composite(c)
    bb = out.getbbox()
    out = out.crop(bb)
    # encajar en 512 (lado mayor = 512), con margen transparente
    out = ImageOps.contain(out, (S - 8, S - 8), Image.LANCZOS)
    final = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    final.alpha_composite(out, ((S - out.width) // 2, (S - out.height) // 2))
    save(final, path)


def canvas():
    return Image.new('RGBA', (900, 900), (0, 0, 0, 0))

def stickers():
    # 1) ¡CHOLLAZO! con la pose del hadouken
    c = canvas()
    s = ImageOps.contain(had, (660, 420), Image.LANCZOS)
    c.alpha_composite(s, (20, 60))
    sticker_text(c, (350, 560), '¡CHOLLAZO!', font(110), fill=[YELLOW, ORANGE], ink_w=12, accent=CYAN,
                 accent_off=(6, 8), anchor='mm')
    finish(c, TG / 'stickers' / 'sticker_chollazo.png')

    # 2) ¡CORRE! con rayos
    c = canvas()
    s = ImageOps.contain(head, (560, 480), Image.LANCZOS)
    c.alpha_composite(s, (120, 20))
    d = ImageDraw.Draw(c)
    bolt(d, 40, 70, 150, ink_w=6)
    sticker_text(c, (350, 590), '¡CORRE!', font(150), fill=[WHITE, (255, 236, 190)], ink_w=13, accent=ORANGE,
                 accent_off=(7, 9), anchor='mm')
    finish(c, TG / 'stickers' / 'sticker_corre.png')

    # 3) AGOTADO (sello rojo cruzado)
    c = canvas()
    s = ImageOps.contain(head, (600, 520), Image.LANCZOS)
    c.alpha_composite(s, (60, 40))
    stamp = Image.new('RGBA', (700, 700), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.rounded_rectangle((70, 290, 630, 430), 22, fill=INK)
    sd.rounded_rectangle((80, 300, 620, 420), 16, fill=RED)
    sd.text((350, 362), 'AGOTADO', font=font(104), fill=WHITE, anchor='mm')
    stamp = stamp.rotate(14, resample=Image.BICUBIC, center=(350, 360))
    c.alpha_composite(stamp, (0, 110))
    finish(c, TG / 'stickers' / 'sticker_agotado.png')

    # 4) MÍNIMO HISTÓRICO con estrella
    c = canvas()
    st = starburst(330, points=14, fill=YELLOW, ink_w=10, rot=8)
    c.alpha_composite(st, (360, 0))
    s = ImageOps.contain(head, (520, 450), Image.LANCZOS)
    c.alpha_composite(s, (20, 120))
    d = ImageDraw.Draw(c)
    d.text((525, 165), 'TOP', font=font(70), fill=INK, anchor='mm')
    sticker_text(c, (350, 560), 'MÍNIMO', font(118), fill=[WHITE, (255, 236, 190)], ink_w=12, accent=CYAN,
                 accent_off=(6, 8), anchor='mm')
    sticker_text(c, (350, 660), 'HISTÓRICO', font(84), fill=[YELLOW, ORANGE], ink_w=11, accent=None, anchor='mm')
    finish(c, TG / 'stickers' / 'sticker_minimo_historico.png')


# ======================================================== tarjetas de ejemplo
def _caratula_ficticia(path, title, c0, c1, shape):
    """Carátula inventada solo para las tarjetas de muestra."""
    w, h = 600, 750
    im = vgrad((w, h), c0, c1)
    speed_lines(im, (w / 2, h * 0.45), n=50, alpha=30, seed=2)
    d = ImageDraw.Draw(im)
    if shape == 'sun':
        d.ellipse((150, 170, 450, 470), fill=(255, 190, 90))
        for i in range(8):
            d.rectangle((150, 300 + i * 22, 450, 306 + i * 22), fill=c0)
    else:
        d.polygon([(300, 150), (480, 480), (120, 480)], fill=(120, 255, 200))
    d.rectangle((0, 560, w, h), fill=(15, 10, 30))
    d.text((w / 2, 620), title, font=font(64), fill=WHITE, anchor='mm')
    d.text((w / 2, 690), 'CARÁTULA DE EJEMPLO', font=font(22, 'Bold', False, False), fill=(170, 170, 200), anchor='mm')
    return im.convert('RGB')


def tarjetas_ejemplo():
    sys.path.insert(0, str(ROOT))
    from hadouken_zone.cards import generar_tarjeta
    out = TG / 'tarjetas_ejemplo'
    a = _caratula_ficticia(None, 'NEON RONIN', (40, 10, 80), (230, 60, 120), 'sun')
    b = _caratula_ficticia(None, 'PIXEL PEAKS', (10, 60, 90), (40, 160, 140), 'tri')
    for ruta in (
        generar_tarjeta('Neon Ronin: Edición Deluxe', 'PS5', 29.99, 69.99,
                        imagen=a, salida=out / 'tarjeta_ejemplo_ps5.jpg'),
        generar_tarjeta('Pixel Peaks Adventure Collection with an Extremely Long Subtitle Edition',
                        'Nintendo Switch', 9.95, 149.99, imagen=b, etiqueta='MÍNIMO HISTÓRICO',
                        salida=out / 'tarjeta_ejemplo_switch.jpg'),
    ):
        print('  ->', Path(ruta).relative_to(ROOT))


def main():
    print('Bienvenida'); bienvenida()
    print('Avatares'); avatares()
    print('Cabeceras'); cabeceras()
    print('Stickers'); stickers()
    print('Tarjetas de ejemplo'); tarjetas_ejemplo()
    print('Listo.')


if __name__ == '__main__':
    main()
