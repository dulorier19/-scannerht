#!/bin/sh
set -eu

if [ "${SERVICE_MODE:-}" = "bot" ] || [ "${RAILWAY_SERVICE_NAME:-}" = "scannerht-bot" ] || [ -n "${API_BASE_URL:-}" ]; then
  exec node bot/index.js
fi

exec python run_backend.py
