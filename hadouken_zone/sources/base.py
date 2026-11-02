"""Contrato común de las fuentes de ofertas.

Cada fuente (Chollometro, Amazon, en el futuro la API oficial de Amazon u otras webs)
implementa `find_offers` y devuelve objetos `Offer` ya validados con `rules.py`.
Para añadir una fuente nueva: crear su módulo en `sources/`, registrarla en
`sources/__init__.py` y activarla con OFFER_SOURCES en el .env.
"""

from __future__ import annotations

from typing import Callable, Protocol

from ..models import Offer


class SourceBlocked(RuntimeError):
    """La fuente ha bloqueado el acceso (CAPTCHA, 403, 503…): se reintenta en el próximo ciclo."""


class OfferSource(Protocol):
    name: str

    def find_offers(self, limit: int, is_new: Callable[[Offer], bool]) -> list[Offer]:
        """Ofertas publicables (como mucho `limit`), de mayor a menor descuento."""
        ...
