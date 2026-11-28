#!/usr/bin/env bash
# Guarda data/*.json en la rama "estado" (commit forzado). Solo si ha cambiado algo.
# Uso (en GitHub Actions): GH_TOKEN=... scripts/guardar_estado.sh
set -euo pipefail
cd "$GITHUB_WORKSPACE"
shopt -s nullglob
files=(data/*.json)
if [ ${#files[@]} -eq 0 ]; then echo "No hay estado que guardar."; exit 0; fi

hash=$(cat "${files[@]}" | sha256sum | cut -d' ' -f1)
if [ -f /tmp/estado_hash ] && [ "$(cat /tmp/estado_hash)" = "$hash" ]; then exit 0; fi

rm -rf /tmp/estado && mkdir -p /tmp/estado && cp "${files[@]}" /tmp/estado/
cd /tmp/estado
git init -q -b estado
git config user.name  "hadouken-bot"
git config user.email "hadouken-bot@users.noreply.github.com"
git add -A
git commit -q -m "Estado $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" estado
echo "$hash" > /tmp/estado_hash
echo "Estado guardado en la rama 'estado'."
