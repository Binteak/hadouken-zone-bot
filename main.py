"""Hadouken Zone - punto de entrada.

    py main.py                 Arranca el bot 24/7 (buenos días + escaneo cada 30 min)
    py main.py --ciclo         Una sola pasada del calendario y termina (modo cron / GitHub Actions):
                               buenos días si toca hoy + escaneo si está en horario
    py main.py --once          Un solo escaneo de Amazon y publicación ahora
    py main.py --buenos-dias   Envía ahora el mensaje de buenos días
    py main.py --test          Envía el mensaje de presentación del canal
    py main.py --verificar     Comprueba el token y el canal de Telegram sin publicar nada

Con DRY_RUN=true en .env todo se muestra en consola y no se publica nada.
"""

import argparse
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from hadouken_zone import __version__, messages
from hadouken_zone.config import Settings
from hadouken_zone.logging_setup import setup_logging
from hadouken_zone.pipeline import Pipeline
from hadouken_zone.scheduler import Scheduler
from hadouken_zone.telegram import TelegramClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Hadouken Zone - ofertas de PS5 y Switch en Telegram")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ciclo", action="store_true", help="una pasada del calendario y termina (cron)")
    group.add_argument("--once", action="store_true", help="un escaneo y publicación ahora")
    group.add_argument("--buenos-dias", action="store_true", help="envía el buenos días ahora")
    group.add_argument("--test", action="store_true", help="envía el mensaje de presentación")
    group.add_argument("--verificar", action="store_true", help="comprueba token y canal sin publicar")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("hadouken_zone")
    settings = Settings.from_env()
    log.info("HADOUKEN ZONE v%s | DRY_RUN=%s | fuentes: %s", __version__, settings.dry_run,
             ", ".join(settings.offer_sources))

    telegram = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id, settings.dry_run)

    if args.verificar:
        try:
            bot, chat = telegram.check()
        except Exception as exc:
            log.error("Configuración de Telegram NO válida: %s", exc)
            return 1
        log.info("Telegram OK: bot %s con acceso al canal '%s'", bot, chat)
        return 0

    if args.test:
        telegram.send_message(messages.test_message())
        log.info("Mensaje de prueba enviado")
        return 0

    pipeline = Pipeline(settings, telegram)

    if args.buenos_dias:
        pipeline.send_good_morning(datetime.now(ZoneInfo(settings.timezone)).date())
        return 0

    if args.once:
        pipeline.run_scan()
        return 0

    if args.ciclo:
        done = Scheduler(settings, pipeline).tick(ignore_interval=True)
        log.info("Pasada terminada: %s", ", ".join(done) or "nada que hacer en este horario")
        return 0

    try:
        Scheduler(settings, pipeline).run_forever()
    except KeyboardInterrupt:
        log.info("Bot detenido por el usuario")
    return 0


if __name__ == "__main__":
    sys.exit(main())
