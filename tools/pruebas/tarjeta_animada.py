"""Prueba de tarjeta animada (no forma parte del bot en producción).

Genera la tarjeta de siempre como vídeo corto en bucle: todo queda igual que la
tarjeta fija de cards.py salvo la estrella de descuento y el precio actual, que
laten suavemente. El primer fotograma es la tarjeta fija.

Con --enviar la manda con sendAnimation al último chat privado que haya escrito
al bot (hay que mandarle /start antes). No toca el canal ni el historial.

    py tools/pruebas/tarjeta_animada.py --salida prueba.mp4
    py tools/pruebas/tarjeta_animada.py --salida prueba.mp4 --enviar   # requiere TELEGRAM_BOT_TOKEN
"""
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from hadouken_zone import cards as C  # noqa: E402
from hadouken_zone import messages  # noqa: E402
from hadouken_zone.affiliate import product_url  # noqa: E402
from hadouken_zone.models import Offer  # noqa: E402

FPS, SEG = 30, 6
CX0, CY0, CW, CH = 80, 70, 420, 540            # carátula, igual que cards.py
PX, PY = 600 - 4, 398 + 36                     # precio actual, igual que cards.py

# Oferta real del historial (2026-11-27)
OFERTA = Offer(
    asin="B0G26ZHPS8", title="ChromaGun 2: Dye Hard - Switch 2", price=14.90, previous_price=49.99,
    platform="Nintendo Switch 2",
    image_url="https://static.chollometro.com/threads/raw/N0nXy/2094209_1/re/1024x1024/qt/55/2094209_1.jpg",
)


def base(titulo, plataforma, actual, anterior, imagen) -> Image.Image:
    """La tarjeta de cards.generar_tarjeta sin la estrella ni el precio actual (mismo código)."""
    img = C._fondo(trama=False)
    C._glow(img, (300, 340), 260, C.ORANGE, 110)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((CX0 + 12, CY0 + 14, CX0 + CW + 12, CY0 + CH + 14), 28, fill=C.CYAN)
    d.rounded_rectangle((CX0 - 8, CY0 - 8, CX0 + CW + 8, CY0 + CH + 8), 30, fill=C.INK)
    d.rounded_rectangle((CX0, CY0, CX0 + CW, CY0 + CH), 24, fill=C.WHITE)
    cover = C._cargar_imagen(imagen)
    if cover is not None:
        cover = ImageOps.contain(cover, (CW - 36, CH - 36), Image.LANCZOS)
        img.alpha_composite(cover, (CX0 + (CW - cover.width) // 2, CY0 + (CH - cover.height) // 2))
    else:
        h = C._mascota()
        if h is not None:
            h = ImageOps.contain(h, (CW - 80, CH - 80), Image.LANCZOS)
            img.alpha_composite(h, (CX0 + (CW - h.width) // 2, CY0 + (CH - h.height) // 2))

    x = 600
    d = ImageDraw.Draw(img)
    nombre, color, tinta = C.PLATAFORMAS.get((plataforma or "").strip().lower(),
                                             ((plataforma or "").upper(), (90, 90, 140), C.WHITE))
    C._etiqueta_plataforma(d, x, 82, nombre, color, tinta)
    y = 166
    f, lineas, size = C._ajustar_titulo(titulo, C.W - x - 60)
    for linea in lineas:
        C._texto(img, (x, y), linea, f, ink=7, sombra=None)
        y += int(size * 1.12)
    yp = 398
    d = ImageDraw.Draw(img)
    if anterior and anterior > actual:
        f = C.F_TEXTO(34)
        d.text((x, yp), "ANTES", font=C.F_FUERTE(22), fill=C.LILAC)
        txt = C.precio_es(anterior)
        tx = x + 100
        d.text((tx, yp - 8), txt, font=f, fill=C.LILAC)
        tw = f.getlength(txt)
        d.line((tx - 4, yp + 13, tx + tw + 4, yp + 9), fill=(255, 80, 70), width=5)
        d.text((x, yp + 192), f"Te ahorras {C.precio_es(anterior - actual)}", font=C.F_TEXTO(30), fill=C.CYAN)

    d = ImageDraw.Draw(img)
    d.rectangle((0, C.H - 70, C.W, C.H), fill=(18, 13, 34))
    d.rectangle((0, C.H - 74, C.W, C.H - 70), fill=C.CYAN)
    h = C._mascota()
    if h is not None:
        h = h.resize((int(h.width * 82 / h.height), 82), Image.LANCZOS)
        img.alpha_composite(h, (C.W - h.width - 28, C.H - 92))
    d.text((80, C.H - 35), "HADOUKEN ZONE", font=C.F_TITULAR(34), fill=C.WHITE, anchor="lm")
    d.text((80 + C.F_TITULAR(34).getlength("HADOUKEN ZONE") + 24, C.H - 35),
           "Ofertas verificadas de PlayStation, Switch y Xbox", font=C.F_TEXTO(24), fill=C.LILAC, anchor="lm")
    return img


def capa_precio(actual) -> tuple[Image.Image, int]:
    """Precio actual en su propia capa transparente; devuelve (capa, margen)."""
    m = 20
    lienzo = Image.new("RGBA", (760, 220), (0, 0, 0, 0))
    bb = C._texto(lienzo, (m, m), C.precio_es(actual), C.F_TITULAR(118),
                  fill=C.YELLOW, ink=11, sombra=C.ORANGE, off=(7, 8))
    return lienzo.crop((0, 0, bb[2] + 30, bb[3] + 30)), m


def generar(salida: Path, offer: Offer = OFERTA) -> Path:
    t0 = time.perf_counter()
    imagen = C._cargar_imagen(offer.image_url)
    fondo = base(offer.title, offer.platform, offer.price, offer.previous_price, imagen)
    estrella = C._estrella(210, f"-{offer.discount_percent}%")
    precio, m = capa_precio(offer.price)
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{C.W}x{C.H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(salida)],
        stdin=subprocess.PIPE)
    n = FPS * SEG
    for i in range(n):
        t = i / n
        frame = fondo.copy()
        lat = 0.5 - 0.5 * math.cos(2 * math.pi * t * 2)       # estrella: 2 latidos por ciclo (cada 3 s)
        e = 1 + 0.035 * lat
        st = estrella if i == 0 else estrella.resize((round(210 * e), round(210 * e)), Image.LANCZOS)
        frame.alpha_composite(st, (round(CX0 + CW - 165 + 105 - st.width / 2),
                                   round(CY0 - 55 + 105 - st.height / 2)))
        resp = 0.5 - 0.5 * math.cos(2 * math.pi * t)          # precio: respira una vez por ciclo (6 s)
        ep = 1 + 0.035 * resp
        pr = precio if i == 0 else precio.resize((round(precio.width * ep), round(precio.height * ep)), Image.LANCZOS)
        frame.alpha_composite(pr, (PX - m, round(PY - m - (pr.height - precio.height) / 2)))
        rgb = frame.convert("RGB")
        if i == 0:
            primero = rgb
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close()
    proc.wait()

    # El primer fotograma tiene que ser la tarjeta fija de siempre
    fija = Path(salida).with_suffix(".fija.png")
    C.generar_tarjeta(offer.title, offer.platform, offer.price, offer.previous_price, imagen=imagen, salida=str(fija))
    dif = np.abs(np.array(Image.open(fija).convert("RGB"), int) - np.array(primero, int)).max(-1)
    print(f"Vídeo: {salida} · {Path(salida).stat().st_size / 1024:.0f} KB · {time.perf_counter() - t0:.1f} s")
    print(f"Primer fotograma frente a la tarjeta fija: {int((dif > 8).sum())} píxeles distintos de {dif.size}")
    return Path(salida)


def enviar(video: Path, offer: Offer = OFERTA) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    api = f"https://api.telegram.org/bot{token}"
    updates = requests.get(f"{api}/getUpdates", params={"limit": 100}, timeout=30).json().get("result", [])
    privados = [u["message"]["chat"]["id"] for u in updates
                if u.get("message", {}).get("chat", {}).get("type") == "private"]
    if not privados:
        sys.exit("No hay ningún chat privado con el bot: abre el bot en Telegram, mándale /start y vuelve a lanzarlo.")
    caption = messages.offer_caption(offer, product_url(offer.asin), affiliate=False)
    caption = "🧪 <i>Prueba de tarjeta animada (no publicada en el canal)</i>\n\n" + caption
    with open(video, "rb") as fh:
        r = requests.post(f"{api}/sendAnimation", data={
            "chat_id": privados[-1], "caption": caption, "parse_mode": "HTML", "width": C.W, "height": C.H,
        }, files={"animation": (video.name, fh, "video/mp4")}, timeout=60).json()
    if not r.get("ok"):
        sys.exit(f"Telegram devolvió un error: {r.get('description')}")
    print("Enviada al chat privado con el bot.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", default="tarjeta_animada.mp4")
    p.add_argument("--enviar", action="store_true")
    a = p.parse_args()
    v = generar(Path(a.salida))
    if a.enviar:
        enviar(v)
