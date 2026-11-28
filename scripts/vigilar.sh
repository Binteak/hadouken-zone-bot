#!/usr/bin/env bash
# Modo vigilancia (GitHub Actions): en vez de una pasada por ejecución, el mismo runner
# repite "python main.py --ciclo" cada WATCH_INTERVAL_SECONDS durante WATCH_MINUTES
# (máximo ~5 h 30 min; GitHub corta los trabajos a las 6 h). Así no se pierden de 1 a 6
# minutos en cada arranque en frío y una oferta nueva se detecta en menos de un minuto.
#
# Se termina antes si se sale del horario del canal (WATCH_UNTIL, hora de Madrid).
# Si se lanza fuera de horario, hace una sola pasada (como antes) y termina.
set -uo pipefail

WATCH_MINUTES="${WATCH_MINUTES:-330}"
WATCH_INTERVAL_SECONDS="${WATCH_INTERVAL_SECONDS:-45}"
WATCH_FROM="${WATCH_FROM:-0800}"
WATCH_UNTIL="${WATCH_UNTIL:-2335}"
SAVE="${SAVE_STATE:-false}"

in_hours() {
  local now; now=$(TZ="${TIMEZONE:-Europe/Madrid}" date +%H%M)
  [ "$((10#$now))" -ge "$((10#$WATCH_FROM))" ] && [ "$((10#$now))" -lt "$((10#$WATCH_UNTIL))" ]
}

deadline=$(( $(date +%s) + WATCH_MINUTES * 60 ))
passes=0
while :; do
  python main.py --ciclo || echo "::warning::La pasada ha fallado; se sigue vigilando."
  passes=$((passes + 1))
  if [ "$SAVE" = "true" ]; then scripts/guardar_estado.sh || echo "::warning::No se pudo guardar el estado."; fi

  if ! in_hours; then echo "Fuera del horario del canal: fin de la vigilancia."; break; fi
  if [ "$(( $(date +%s) + WATCH_INTERVAL_SECONDS ))" -ge "$deadline" ]; then
    echo "Tiempo máximo de vigilancia alcanzado."; break
  fi
  sleep "$WATCH_INTERVAL_SECONDS"
done
echo "Vigilancia terminada tras $passes pasadas."
