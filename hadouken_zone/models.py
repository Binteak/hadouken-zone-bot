"""Modelo de datos de una oferta."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Offer:
    asin: str
    title: str
    price: float | None = None
    previous_price: float | None = None
    platform: str | None = None          # "PS5" | "Nintendo Switch" | None
    image_url: str | None = None
    platform_text: str = ""              # texto extra de plataforma (ficha / resultado)
    available: bool = True
    verified: bool = False               # precios confirmados en la ficha del producto
    source_query: str = ""
    found_at: str = field(default_factory=utcnow_iso)

    @property
    def discount_percent(self) -> int | None:
        if not self.price or not self.previous_price or self.previous_price <= 0:
            return None
        return round((1 - self.price / self.previous_price) * 100)

    @property
    def savings(self) -> float | None:
        if self.price is None or self.previous_price is None:
            return None
        return round(self.previous_price - self.price, 2)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["discount_percent"] = self.discount_percent
        return data
