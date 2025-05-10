#!/bin/bash
set -e

# Playwright-Browser installieren, falls nicht vorhanden
if [ ! -d "/ms-playwright/chromium-"* ]; then
  echo "[Entrypoint] Installiere Playwright-Browser..."
  playwright install --with-deps || true
fi

# Starte den API-Server (Original Entrypoint)
exec /start.sh 