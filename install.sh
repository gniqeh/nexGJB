#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
manager="${1:-}"
if [[ -z "$manager" ]]; then
  for m in micromamba mamba conda; do
    if command -v "$m" >/dev/null 2>&1; then manager="$m"; break; fi
  done
fi
case "$manager" in micromamba|mamba|conda) ;; *) echo '请安装 micromamba、mamba 或 conda'; exit 1;; esac
if "$manager" run -n nexgjb python -c 'import fastapi, uvicorn, shapely, pyproj' >/dev/null 2>&1; then
  "$manager" env update -n nexgjb -f environment.yml
else
  "$manager" create -y -f environment.yml
fi
mkdir -p static/leaflet data
for file in leaflet.js leaflet.css; do
  if [[ ! -s "static/leaflet/$file" ]]; then
    "$manager" run -n nexgjb curl -fL --retry 2 "https://unpkg.com/leaflet@1.9.4/dist/$file" -o "static/leaflet/$file.tmp"
    mv "static/leaflet/$file.tmp" "static/leaflet/$file"
  fi
done
printf '%s\n' "$manager" > .env-manager
echo '安装完成'
