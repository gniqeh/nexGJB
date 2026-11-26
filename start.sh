#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
manager="${ENV_MANAGER:-}"
if [[ -z "$manager" && -f .env-manager ]]; then read -r manager < .env-manager; fi
if [[ -z "$manager" ]]; then
  for m in micromamba mamba conda; do
    if command -v "$m" >/dev/null 2>&1; then manager="$m"; break; fi
  done
fi
case "$manager" in micromamba|mamba|conda) ;; *) echo '请先运行 bash install.sh'; exit 1;; esac
exec "$manager" run -n nexgjb python -m uvicorn app:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8812}"
