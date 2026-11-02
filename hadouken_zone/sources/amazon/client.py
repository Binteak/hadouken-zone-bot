"""Cliente HTTP para Amazon: pausas entre peticiones y detección de CAPTCHA.

Política: peticiones espaciadas (REQUEST_DELAY_SECONDS + aleatorio), sin rotación de
proxies ni intentos de saltar CAPTCHA. Si Amazon muestra un CAPTCHA, el ciclo se
detiene y se reintenta en el siguiente escaneo.
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from urllib.parse import urlencode

import requests

from ...config import DEBUG_DIR
from ..base import SourceBlocked
from .parser import is_captcha

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}


class CaptchaError(SourceBlocked):
    """Amazon ha pedido verificación humana: hay que parar y esperar."""


class AmazonClient:
    def __init__(self, domain: str = "www.amazon.es", delay: float = 4.0, session=None, sleep=time.sleep):
        self.domain = domain
        self.delay = delay
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self._sleep = sleep
        self._last = 0.0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last
        pause = self.delay + random.uniform(0, self.delay / 2)
        if self._last and elapsed < pause:
            self._sleep(pause - elapsed)
        self._last = time.monotonic()

    def get(self, url: str) -> str:
        self._wait()
        resp = self.session.get(url, timeout=25)
        html = resp.text
        if resp.status_code == 503 or is_captcha(html):
            self.save_debug(html, "captcha")
            raise CaptchaError(f"Amazon ha mostrado un CAPTCHA o bloqueo ({resp.status_code})")
        resp.raise_for_status()
        return html

    def search_url(self, query: str, page: int = 1) -> str:
        params = {"k": query, "i": "videogames"}
        if page > 1:
            params["page"] = page
        return f"https://{self.domain}/s?{urlencode(params)}"

    def product_url(self, asin: str) -> str:
        return f"https://{self.domain}/dp/{asin}"

    @staticmethod
    def save_debug(html: str, label: str) -> None:
        """Guarda el HTML en logs/html_debug/ para ajustar selectores si Amazon cambia."""
        try:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            name = f"{datetime.now():%Y%m%d_%H%M%S}_{label}.html"
            (DEBUG_DIR / name).write_text(html or "", encoding="utf-8")
            files = sorted(DEBUG_DIR.glob("*.html"))
            for old in files[:-20]:            # conservar solo los 20 últimos
                old.unlink(missing_ok=True)
        except OSError:
            pass
