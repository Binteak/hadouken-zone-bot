"""Enlaces de producto de Amazon, con el identificador de afiliado si está configurado.

Nunca se inventa un identificador: si AMAZON_PARTNER_TAG está vacío, el enlace
es el normal del producto (https://www.amazon.es/dp/ASIN).
"""

from __future__ import annotations

import re

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


def product_url(asin: str, domain: str = "www.amazon.es", partner_tag: str = "") -> str:
    asin = (asin or "").strip().upper()
    if not ASIN_RE.match(asin):
        raise ValueError(f"ASIN no válido: {asin!r}")
    url = f"https://{domain}/dp/{asin}"
    if partner_tag:
        url += f"?tag={partner_tag}"
    return url


def extract_asin(url: str) -> str | None:
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url or "")
    return match.group(1) if match else None
