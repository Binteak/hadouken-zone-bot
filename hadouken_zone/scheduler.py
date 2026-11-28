"""Planificador del bot 24/7.

Cada día (zona horaria TIMEZONE):
  - GOOD_MORNING_TIME (09:00): mensaje de buenos días con imagen.
  - Después, cada SCAN_INTERVAL_MINUTES (30): escaneo de Amazon y publicación de todas
    las ofertas nuevas, con OFFER_DELAY_SECONDS (60) entre una y otra.
  - GOOD_NIGHT_TIME (23:00): hilo de buenas noches (resumen del día + mejores ofertas como
    respuestas silenciosas). Después ya no se publican ofertas hasta el día siguiente.
  - A partir de ACTIVE_UNTIL (23:30) se detiene hasta el día siguiente.

El estado (último buenos días y último escaneo) se guarda en data/state.json, así que
reiniciar el bot no repite mensajes.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import Settings
from .storage import StateStore

log = logging.getLogger(__name__)

GOOD_MORNING_GRACE = timedelta(hours=2)   # si el bot arranca más tarde, ese día no hay buenos días
TICK_SECONDS = 20


class Scheduler:
    def __init__(self, settings: Settings, pipeline, state: StateStore | None = None,
                 clock=None, sleep=time.sleep):
        self.settings = settings
        self.pipeline = pipeline
        self.state = state or StateStore()
        self.tz = ZoneInfo(settings.timezone)
        self.clock = clock or (lambda: datetime.now(self.tz))
        self.sleep = sleep
        pipeline.still_active = lambda: self.is_active(self.clock())

    # ------------------------------------------------------------ reglas de tiempo
    def is_active(self, now: datetime) -> bool:
        return self.settings.good_morning_time <= now.time() < self.settings.active_until

    def good_morning_due(self, now: datetime) -> bool:
        if not self.is_active(now) or self.state["last_good_morning"] == now.date().isoformat():
            return False
        start = now.replace(hour=self.settings.good_morning_time.hour,
                            minute=self.settings.good_morning_time.minute, second=0, microsecond=0)
        return now - start <= GOOD_MORNING_GRACE

    def good_night_due(self, now: datetime) -> bool:
        t = self.settings.good_night_time
        if t is None or not self.is_active(now) or now.time() < t:
            return False
        return self.state["last_good_night"] != now.date().isoformat()

    def scan_due(self, now: datetime, ignore_interval: bool = False) -> bool:
        if not self.is_active(now):
            return False
        if self.state["last_good_night"] == now.date().isoformat():
            return False             # tras las buenas noches ya no se publica hasta mañana
        if ignore_interval:          # modo cron: cada ejecución programada escanea
            return True
        last = self.state["last_scan_at"]
        if not last:
            return True
        return now - datetime.fromisoformat(last) >= timedelta(minutes=self.settings.scan_interval_minutes)

    def price_check_due(self, now: datetime) -> bool:
        minutes = self.settings.price_check_minutes
        if minutes <= 0 or not self.is_active(now):
            return False
        if self.state["last_good_night"] == now.date().isoformat():
            return False
        last = self.state["last_price_check_at"]
        if not last:
            return True
        try:
            return now - datetime.fromisoformat(last) >= timedelta(minutes=minutes)
        except ValueError:
            return True

    # ------------------------------------------------------------ ejecución
    def tick(self, ignore_interval: bool = False) -> list[str]:
        """Ejecuta lo que toque ahora. Devuelve las acciones realizadas (útil en tests).

        ignore_interval=True (modo cron): el intervalo lo marca el cron, no SCAN_INTERVAL_MINUTES.
        """
        done = []
        now = self.clock()
        if self.good_morning_due(now):
            try:
                self.pipeline.send_good_morning(now.date())
                done.append("good_morning")
            except Exception:
                log.exception("Error enviando el buenos días")
            # se marca igualmente para no reintentar en bucle
            self.state.set("last_good_morning", now.date().isoformat())
            self.sleep(self.settings.offer_delay_seconds)
            now = self.clock()

        if self.good_night_due(now):
            # se marca antes de enviar: si algo falla no se repite el hilo en cada pasada
            self.state.set("last_good_night", now.date().isoformat())
            try:
                self.pipeline.send_good_night(now.date(), self.tz)
                done.append("good_night")
            except Exception:
                log.exception("Error enviando las buenas noches")
            return done

        if self.scan_due(now, ignore_interval):
            self.state.set("last_scan_at", now.isoformat())   # el intervalo cuenta desde el inicio
            self.pipeline.run_scan()
            done.append("scan")

        now = self.clock()
        if self.price_check_due(now):
            self.state.set("last_price_check_at", now.isoformat())
            try:
                self.pipeline.check_prices(now.date(), self.tz)
                done.append("price_check")
            except Exception:
                log.exception("Error revisando los precios de las ofertas publicadas")
        return done

    def run_forever(self) -> None:
        s = self.settings
        log.info(
            "Hadouken Zone en marcha | buenos días %s | escaneo cada %s min | %s s entre ofertas | "
            "activo hasta %s | DRY_RUN=%s",
            s.good_morning_time.strftime("%H:%M"), s.scan_interval_minutes, s.offer_delay_seconds,
            s.active_until.strftime("%H:%M"), s.dry_run,
        )
        while True:
            try:
                self.tick()
            except Exception:
                log.exception("Error inesperado en el planificador")
            self.sleep(TICK_SECONDS)
