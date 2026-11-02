"""Parser HTML de Amazon (resultados de búsqueda y ficha de producto).

Funciones puras: reciben HTML y devuelven datos. Amazon cambia su maquetación
con frecuencia; por eso cada dato se intenta con varios selectores y los tests
(tests/fixtures) documentan la estructura esperada.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ...models import Offer

CAPTCHA_MARKERS = ("validatecaptcha", "captcha", "robot check", "introduce los caracteres")


def parse_price(text: str | None) -> float | None:
    """'1.299,99 €' -> 1299.99 · '32,99€' -> 32.99 · '€32.99' -> 32.99"""
    if not text:
        return None
    t = text.replace("\xa0", " ").replace("€", "").replace("EUR", "").strip()
    m = re.search(r"\d[\d.,]*", t)
    if not m:
        return None
    num = m.group(0).rstrip(".,")
    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):          # 1.299,99
            num = num.replace(".", "").replace(",", ".")
        else:                                        # 1,299.99
            num = num.replace(",", "")
    elif "," in num:
        whole, _, dec = num.rpartition(",")
        num = f"{whole.replace(',', '')}.{dec}" if len(dec) <= 2 else num.replace(",", "")
    elif num.count(".") == 1 and len(num.split(".")[1]) == 3:  # 1.299 (miles)
        num = num.replace(".", "")
    try:
        value = float(num)
    except ValueError:
        return None
    return value if value > 0 else None


def is_captcha(html: str) -> bool:
    low = (html or "")[:20000].lower()
    return any(m in low for m in CAPTCHA_MARKERS) and "s-search-result" not in low and "producttitle" not in low


def _text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""


def _price_from(container) -> float | None:
    """Precio de un nodo .a-price: primero .a-offscreen, si no whole + fraction."""
    if container is None:
        return None
    off = container.select_one(".a-offscreen")
    value = parse_price(off.get_text()) if off else None
    if value:
        return value
    whole = container.select_one(".a-price-whole")
    frac = container.select_one(".a-price-fraction")
    if whole:
        w = re.sub(r"[^\d]", "", whole.get_text())
        f = re.sub(r"[^\d]", "", frac.get_text()) if frac else "00"
        return parse_price(f"{w},{f or '00'}")
    return None


# ------------------------------------------------------------------ búsqueda
def parse_search_results(html: str, source_query: str = "") -> list[Offer]:
    soup = BeautifulSoup(html, "html.parser")
    offers: list[Offer] = []
    seen: set[str] = set()

    for item in soup.select('div[data-component-type="s-search-result"][data-asin]'):
        asin = (item.get("data-asin") or "").strip().upper()
        if not asin or asin in seen:
            continue
        title = _text(item.select_one("h2"))
        if not title:
            continue

        current = None
        for p in item.select("span.a-price"):
            if "a-text-price" in (p.get("class") or []) or p.get("data-a-strike") == "true":
                continue
            current = _price_from(p)
            if current:
                break

        previous = None
        for p in item.select('span.a-price.a-text-price, span.a-price[data-a-strike="true"]'):
            previous = _price_from(p)
            if previous:
                break

        img = item.select_one("img.s-image")
        # Texto de formato/plataforma que Amazon muestra bajo el título
        platform_text = " ".join(_text(a) for a in item.select("a.a-text-bold, span.a-text-bold, a.a-link-normal.a-text-bold"))

        seen.add(asin)
        offers.append(Offer(
            asin=asin,
            title=title,
            price=current,
            previous_price=previous,
            image_url=img.get("src") if img else None,
            platform_text=platform_text,
            source_query=source_query,
        ))
    return offers


# ------------------------------------------------------------------ ficha de producto
CURRENT_PRICE_SELECTORS = (
    "#corePriceDisplay_desktop_feature_div .priceToPay",
    "#corePriceDisplay_desktop_feature_div .a-price:not(.a-text-price)",
    "#corePrice_feature_div .a-price:not(.a-text-price)",
    "#corePrice_desktop .a-price:not(.a-text-price)",
    "#apex_desktop .a-price:not(.a-text-price)",
)
REFERENCE_PRICE_SELECTORS = (
    "#corePriceDisplay_desktop_feature_div .basisPrice .a-price",
    "#corePriceDisplay_desktop_feature_div .a-price.a-text-price",
    "#corePrice_feature_div .a-price.a-text-price",
    "#corePrice_desktop .a-price.a-text-price",
    "#apex_desktop .a-price.a-text-price",
)
UNAVAILABLE_MARKERS = ("no disponible", "currently unavailable", "no está disponible")


def parse_product_page(html: str, asin: str) -> Offer | None:
    soup = BeautifulSoup(html, "html.parser")
    title = _text(soup.select_one("#productTitle"))
    if not title:
        return None

    price = next((v for s in CURRENT_PRICE_SELECTORS if (v := _price_from(soup.select_one(s)))), None)
    reference = next((v for s in REFERENCE_PRICE_SELECTORS if (v := _price_from(soup.select_one(s)))), None)

    image = None
    img = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
    if img:
        image = img.get("data-old-hires") or img.get("src")

    availability = _text(soup.select_one("#availability")).lower()
    available = not any(m in availability for m in UNAVAILABLE_MARKERS)

    platform_text = " ".join(_text(soup.select_one(s)) for s in (
        "#platformInformation_feature_div", "#productOverview_feature_div", "#bylineInfo",
    ))

    return Offer(
        asin=asin.upper(),
        title=title,
        price=price,
        previous_price=reference,
        image_url=image,
        platform_text=platform_text,
        available=available,
        verified=bool(price and reference),
    )
