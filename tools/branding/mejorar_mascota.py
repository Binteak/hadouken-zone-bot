"""Genera la mascota en alta resolución y con fondo transparente a partir de los originales.

    branding/originales/avatar_original_400x400.jpg  -> branding/mascota/mascota_cabeza.png
    branding/originales/banner_original_600x200.jpg  -> branding/mascota/mascota_hadouken.png

Proceso: limpieza de JPEG -> escalado x4 (Lanczos) -> filtro de choque (Osher-Rudin),
que endurece los bordes sin alterar colores ni degradados -> recorte del fondo morado
-> ligero refuerzo de color.

Uso:  python tools/branding/mejorar_mascota.py
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
ORIG = ROOT / "branding" / "originales"
OUT = ROOT / "branding" / "mascota"

BG = np.array([55, 47, 88])  # morado de fondo de los originales


def shock_upscale(src, scale=4, iters=14, dt=0.25, sigma=1.6):
    img = np.array(Image.open(src).convert("RGB"))
    img = cv2.fastNlMeansDenoisingColored(img, None, 4, 4, 5, 15)
    h, w = img.shape[:2]
    I = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    s = sigma * scale / 2

    def minmod(a, b):
        return np.where(a * b > 0, np.sign(a) * np.minimum(np.abs(a), np.abs(b)), 0)

    for _ in range(iters):
        B = cv2.GaussianBlur(I, (0, 0), s)
        lum = cv2.cvtColor(np.clip(B, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        lap_l = cv2.Laplacian(lum, cv2.CV_32F, ksize=3)
        out = np.empty_like(I)
        for c in range(3):
            ch = I[..., c]
            lap_c = cv2.Laplacian(B[..., c], cv2.CV_32F, ksize=3)
            sg = np.where(np.abs(lap_c) > np.abs(lap_l), np.sign(lap_c), np.sign(lap_l))
            dxp = np.roll(ch, -1, 1) - ch
            dxm = ch - np.roll(ch, 1, 1)
            dyp = np.roll(ch, -1, 0) - ch
            dym = ch - np.roll(ch, 1, 0)
            g = np.sqrt(minmod(dxp, dxm) ** 2 + minmod(dyp, dym) ** 2)
            out[..., c] = ch - dt * sg * g
        I = np.clip(out, 0, 255)
    I = cv2.GaussianBlur(I, (0, 0), 0.6)
    return Image.fromarray(I.astype(np.uint8))


def cut_background(im, sc=4, thr=40):
    a = np.array(im).astype(int)
    bgmask = np.sqrt(((a - BG) ** 2).sum(-1)) < thr
    lab, _ = ndimage.label(bgmask)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    lab2, n2 = ndimage.label(bgmask & ~bg)
    if n2:
        sizes = ndimage.sum(np.ones_like(lab2), lab2, range(1, n2 + 1))
        for i, s in enumerate(sizes, 1):
            if s > 60 * sc * sc / 4:
                bg |= lab2 == i
    fg = ndimage.binary_opening(~bg, iterations=2)
    lab3, n3 = ndimage.label(fg)
    sizes = ndimage.sum(np.ones_like(lab3), lab3, range(1, n3 + 1))
    keep = np.isin(lab3, [i for i, s in enumerate(sizes, 1) if s > 200 * sc * sc / 4])
    alpha = Image.fromarray((keep * 255).astype("uint8"))
    alpha = alpha.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.3))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(out.getbbox())


def enhance(im):
    a = im.getchannel("A")
    rgb = ImageEnhance.Color(im.convert("RGB")).enhance(1.12)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
    rgb.putalpha(a)
    return rgb


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    print("Cabeza...")
    head = cut_background(shock_upscale(ORIG / "avatar_original_400x400.jpg"))
    # el original corta la coleta en recto: se difumina hacia la izquierda
    a = np.array(head.getchannel("A")).astype(float)
    a *= (np.clip(np.arange(a.shape[1]) / 340, 0, 1) ** 1.3)[None, :]
    head.putalpha(Image.fromarray(a.astype("uint8")))
    enhance(head).save(OUT / "mascota_cabeza.png")

    print("Pose hadouken...")
    had = cut_background(shock_upscale(ORIG / "banner_original_600x200.jpg", iters=9, sigma=2.2))
    enhance(had).save(OUT / "mascota_hadouken.png")

    print(f"Listo: {OUT}")


if __name__ == "__main__":
    main()
