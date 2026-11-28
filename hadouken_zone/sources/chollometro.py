"""Fuente "chollometro": ofertas de Amazon publicadas por la comunidad de Chollometro.

Funciona desde GitHub Actions (Chollometro no bloquea las IP de centros de datos) y
no necesita entrar en Amazon:

1. Lee los RSS de Chollometro (nuevos y populares) y se queda con las ofertas cuya
   tienda es Amazon.
2. Abre la página de cada oferta y lee sus datos: precio, precio anterior
   (nextBestPrice), dominio del enlace, estado y si ha caducado.
3. Obtiene el ASIN de la redirección de la oferta (/visit/threadmain/<id>), sin
   seguirla hasta Amazon.
4. Aplica las reglas de negocio de rules.py (plataforma, exclusiones, descuento mínimo…).

El enlace que se publica es siempre el limpio de Amazon (https://www.amazon.es/dp/ASIN),
generado en affiliate.py; nunca el de Chollometro.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import hashlib
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlencode, urlsplit, urlunsplit

import requests

from ..config import Settings
from ..models import Offer
from ..rules import rejection_reason
from ..storage import _read, _write
from .base import SourceBlocked

log = logging.getLogger(__name__)

BASE = "https://www.chollometro.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}
ASIN_RE = re.compile(r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})")
THREAD_ID_RE = re.compile(r"-(\d+)/?$")
SEEN_TTL = timedelta(days=2)     # cuánto se recuerda un hilo ya revisado (y descartado o publicado)


# ------------------------------------------------------------------ parsers (funciones puras)
def parse_rss(xml: str, stores=("amazon",)) -> list[dict]:
    """Entradas del RSS de las tiendas aceptadas: id, tienda, título, enlace, fecha e imagen."""
    entries = []
    accepted = {s.lower() for s in stores}
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        merchant = re.search(r'<pepper:merchant\b[^>]*\bname="([^"]*)"', item)
        store = html_lib.unescape(merchant.group(1)).strip() if merchant else ""
        if not store or store.lower() not in accepted:
            continue
        link = _tag(item, "link")
        match = THREAD_ID_RE.search(link)
        if not match:
            continue
        image = re.search(r'<media:content\b[^>]*\burl="([^"]+)"', item)
        entries.append({
            "thread_id": match.group(1),
            "store": store,
            "title": _tag(item, "title"),
            "link": link,
            "image_url": big_image(image.group(1)) if image else None,
            "posted_at": parse_pubdate(_tag(item, "pubDate")),
        })
    return entries


def parse_pubdate(value: str) -> str | None:
    """Fecha del RSS (RFC 822, p. ej. 'Mon, 02 Nov 2026 13:16:42 +0100') en ISO UTC."""
    if not value:
        return None
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc).isoformat()


def _tag(item: str, name: str) -> str:
    m = re.search(rf"<{name}>(.*?)</{name}>", item, re.S)
    if not m:
        return ""
    value = re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip())
    return html_lib.unescape(value).strip()


def big_image(url: str) -> str:
    """La miniatura del RSS (150x150) en versión grande para la tarjeta."""
    return re.sub(r"/re/\d+x\d+/", "/re/1024x1024/", url)


def _json_string(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except ValueError:
        return raw


def parse_thread(page: str, thread_id: str) -> dict | None:
    """Datos de la oferta principal de una página de Chollometro.

    La página incluye también otras ofertas relacionadas; los datos de la principal
    están en el objeto JSON que contiene "threadId":"<id>".
    """
    anchor = re.search(r'"threadId"\s*:\s*"' + re.escape(thread_id) + '"', page)
    if not anchor:
        return None
    # Inicio del objeto JSON que contiene el threadId (llave de apertura equilibrada)
    depth, start = 0, None
    for i in range(anchor.start(), max(anchor.start() - 20000, 0), -1):
        ch = page[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            if depth == 0:
                start = i
                break
            depth -= 1
    if start is None:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(page[start:])
    except ValueError:
        obj = None
    if isinstance(obj, dict):
        return obj

    # Plan B: lectura por expresiones regulares alrededor del threadId
    before = page[max(start, anchor.start() - 4000):anchor.start()]
    after = page[anchor.end():anchor.end() + 6000]

    def last(pattern, text):
        found = re.findall(pattern, text)
        return found[-1] if found else None

    def num(v):
        return None if v in (None, "null") else float(v)

    title = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', after)
    return {
        "threadId": thread_id,
        "price": num(last(r'"price"\s*:\s*([\d.]+|null)', before)),
        "nextBestPrice": num(last(r'"nextBestPrice"\s*:\s*([\d.]+|null)', before)),
        "linkHost": last(r'"linkHost"\s*:\s*"([^"]*)"', before),
        "title": _json_string(title.group(1)) if title else None,
        "status": (re.search(r'"status"\s*:\s*"([^"]*)"', after) or [None, None])[1],
        "isExpired": "\"isExpired\":true" in after,
        "isMaybeExpired": "\"isMaybeExpired\":true" in after,
    }


def asin_from_redirect(location: str) -> str | None:
    """ASIN de la URL de redirección (la URL de Amazon puede venir codificada)."""
    decoded = location
    for _ in range(3):
        m = ASIN_RE.search(decoded)
        if m:
            return m.group(1)
        decoded = unquote(decoded)
    return None


TRACKING_PARAMS = re.compile(r"^(utm_|tag$|ref|aff|affiliate|awc$|clickid|gclid|fbclid|ranmid|ransite|irclickid|sscid|cjevent|mc_)", re.I)


def store_url_from_redirect(location: str) -> str | None:
    """URL final de la tienda desde la redirección de Chollometro, sin parámetros de seguimiento."""
    url = location
    for _ in range(4):        # destino anidado: redirección de Chollometro o red de afiliación (Awin…)
        query = parse_qs(urlsplit(url).query)
        inner = next((v[0] for k in ("url", "ued", "murl", "u", "dest", "destination")
                      for v in [query.get(k)] if v and v[0].startswith("http")), None)
        if not inner:
            break
        url = unquote(inner)
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc or parts.netloc.endswith("chollometro.com"):
        return None
    query = [(k, v) for k, vals in parse_qs(parts.query).items() for v in vals if not TRACKING_PARAMS.match(k)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def store_offer_id(url: str) -> str:
    """Identificador estable de 10 caracteres para una oferta que no es de Amazon (no hay ASIN)."""
    return "T" + hashlib.sha1(url.encode()).hexdigest()[:9].upper()


def clean_title(title: str) -> str:
    """Quita del título lo que añade la comunidad: precios, cupones, '(Precio mínimo)'…"""
    t = re.sub(r"\s*[\(\[][^\)\]]*(€|cup[oó]n|precio|m[ií]nimo|prime|env[ií]o)[^\)\]]*[\)\]]", "", title, flags=re.I)
    t = re.sub(r"\s*[-–|]\s*\d+[.,]?\d*\s?€.*$", "", t)
    t = re.sub(r"\s*\bpor\s+\d+[.,]?\d*\s?€.*$", "", t, flags=re.I)
    return re.sub(r"\s{2,}", " ", t).strip(" -–|") or title


# ------------------------------------------------------------------ fuente
class ChollometroSource:
    name = "chollometro"

    def __init__(self, settings: Settings, session=None, sleep=time.sleep, delay: float = 1.5,
                 seen_path: Path | None = None, clock=lambda: datetime.now(timezone.utc)):
        self.settings = settings
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self.sleep = sleep
        self.delay = delay
        # Hilos ya revisados: no se vuelven a abrir en cada pasada (con pasadas cada
        # pocos segundos, abrir otra vez cada oferta del RSS retrasaría las nuevas).
        self.seen_path = seen_path
        self.clock = clock
        self.seen: dict[str, str] = _read(seen_path, {}) if seen_path else {}

    def _remember(self, thread_id: str) -> None:
        self.seen[thread_id] = self.clock().isoformat()

    def _already_seen(self, thread_id: str) -> bool:
        when = self.seen.get(thread_id)
        if not when:
            return False
        try:
            return self.clock() - datetime.fromisoformat(when) < SEEN_TTL
        except ValueError:
            return False

    def _save_seen(self) -> None:
        if not self.seen_path:
            return
        limit = self.clock() - SEEN_TTL
        self.seen = {k: v for k, v in self.seen.items() if datetime.fromisoformat(v) >= limit}
        _write(self.seen_path, self.seen)

    def _get(self, url: str, **kw):
        resp = self.session.get(url, timeout=25, **kw)
        if resp.status_code in (403, 429, 503):
            raise SourceBlocked(f"Chollometro ha respondido {resp.status_code}")
        return resp

    def candidates(self) -> list[dict]:
        seen, entries = set(), []
        for feed in self.settings.chollometro_feeds:
            resp = self._get(feed)
            resp.raise_for_status()
            for entry in parse_rss(resp.text, self.settings.stores):
                if entry["thread_id"] not in seen:
                    seen.add(entry["thread_id"])
                    entries.append(entry)
        log.info("Chollometro: %s ofertas de tiendas aceptadas en los RSS", len(entries))
        return entries

    def offer_from_entry(self, entry: dict) -> Offer | None:
        resp = self._get(entry["link"])
        if resp.status_code != 200:
            return None
        data = parse_thread(resp.text, entry["thread_id"])
        if not data:
            log.warning("Chollometro: no se pudieron leer los datos de %s", entry["link"])
            return None
        store = entry.get("store") or "Amazon"
        is_amazon = store.lower() == "amazon"
        host = (data.get("linkHost") or "").lower()
        if is_amazon and host and "amazon." not in host:
            return None
        if data.get("isExpired") or data.get("isMaybeExpired") or str(data.get("status", "")).lower() == "expired":
            return None

        self.sleep(self.delay)
        visit = self._get(f"{BASE}/visit/threadmain/{entry['thread_id']}", allow_redirects=False)
        location = visit.headers.get("Location", "")
        url = None
        if is_amazon:
            asin = asin_from_redirect(location)
            if not asin:
                log.debug("Chollometro %s: sin ASIN en la redirección", entry["thread_id"])
                return None
        else:
            url = store_url_from_redirect(location)
            if not url:
                log.debug("Chollometro %s: sin enlace de tienda en la redirección", entry["thread_id"])
                return None
            asin = store_offer_id(url)

        def money(v):
            try:
                return float(v) if v not in (None, "", 0, "0") else None
            except (TypeError, ValueError):
                return None

        return Offer(
            asin=asin,
            title=clean_title(data.get("title") or entry["title"]),
            price=money(data.get("price")),
            previous_price=money(data.get("nextBestPrice")),
            image_url=entry.get("image_url"),
            posted_at=entry.get("posted_at"),
            store=store,
            url=url,
            platform_text=entry["title"],
            verified=True,               # precio publicado y moderado por la comunidad
            source_query=f"chollometro:{entry['thread_id']}",
        )

    def find_offers(self, limit: int, is_new: Callable[[Offer], bool]) -> list[Offer]:
        offers = []
        try:
            for entry in self.candidates():
                tid = entry["thread_id"]
                if self._already_seen(tid):
                    continue
                # filtro previo barato con el título del RSS (evita abrir páginas que no son juegos)
                if rejection_reason(Offer(asin="0000000000", title=entry["title"], price=1, previous_price=2),
                                    self.settings) in ("no es un videojuego (accesorio/hardware)",
                                                       "plataforma no reconocida o no objetivo"):
                    self._remember(tid)
                    continue
                self.sleep(self.delay)
                try:
                    offer = self.offer_from_entry(entry)
                except SourceBlocked:
                    raise
                except requests.RequestException as exc:
                    log.warning("Chollometro %s: error de red (%s)", tid, exc.__class__.__name__)
                    continue          # sin recordar: se reintenta en la próxima pasada
                if offer is None:
                    self._remember(tid)
                    continue
                reason = rejection_reason(offer, self.settings)
                if reason:
                    log.info("Descartada %s (%s): %s", offer.asin, offer.title[:50], reason)
                    self._remember(tid)
                    continue
                if is_new(offer):
                    offers.append(offer)   # sin recordar hasta que esté publicada
                else:
                    self._remember(tid)    # ya publicada: no hace falta volver a abrirla
        finally:
            self._save_seen()
        offers.sort(key=lambda o: o.discount_percent or 0, reverse=True)
        return offers[:limit]
