"""Persistencia en JSON: historial de ofertas publicadas y estado del planificador."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import DATA_DIR
from .models import Offer, utcnow_iso


def _read(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write(path: Path, data) -> None:
    """Escritura atómica: archivo temporal + reemplazo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


class OfferStore:
    """Historial por ASIN en data/offers.json. Evita publicar duplicados."""

    def __init__(self, path: Path | None = None):
        self.path = path or DATA_DIR / "offers.json"
        self.data = _read(self.path, {"offers": {}})
        self.data.setdefault("offers", {})

    def get(self, asin: str) -> dict | None:
        return self.data["offers"].get(asin)

    def should_publish(self, offer: Offer, republish_after_days: int, now: datetime | None = None) -> bool:
        """Nueva oferta, o ya publicada hace más de N días, o ahora más barata (≥5 %)."""
        record = self.get(offer.asin)
        if not record or not record.get("last_published_at"):
            return True
        now = now or datetime.now(timezone.utc)
        last = datetime.fromisoformat(record["last_published_at"])
        if now - last >= timedelta(days=republish_after_days):
            return True
        last_price = record.get("last_published_price")
        return bool(last_price and offer.price and offer.price <= last_price * 0.95)

    def published_on(self, day, tz) -> list[dict]:
        """Ofertas cuya última publicación cae en `day` (fecha local en la zona `tz`)."""
        out = []
        for record in self.data["offers"].values():
            when = record.get("last_published_at")
            if when and datetime.fromisoformat(when).astimezone(tz).date() == day:
                out.append(record)
        return out

    def mark_published(self, offer: Offer, url: str) -> None:
        now = utcnow_iso()
        record = self.data["offers"].setdefault(offer.asin, {"first_published_at": now, "times_published": 0})
        record.update(
            asin=offer.asin,
            title=offer.title,
            platform=offer.platform,
            url=url,
            image_url=offer.image_url,
            last_published_at=now,
            last_published_price=offer.price,
            last_previous_price=offer.previous_price,
            last_discount_percent=offer.discount_percent,
        )
        record["times_published"] = record.get("times_published", 0) + 1
        self.save()

    def save(self) -> None:
        self.data["updated_at"] = utcnow_iso()
        _write(self.path, self.data)


class StateStore:
    """Estado del planificador en data/state.json (último buenos días, último escaneo)."""

    def __init__(self, path: Path | None = None):
        self.path = path or DATA_DIR / "state.json"
        self.data = _read(self.path, {})

    def __getitem__(self, key):
        return self.data.get(key)

    def set(self, key, value) -> None:
        self.data[key] = value
        _write(self.path, self.data)
