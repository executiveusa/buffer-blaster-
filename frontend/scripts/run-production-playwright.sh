#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.55.0}"

npm install --no-save --package-lock=false "@playwright/test@${PLAYWRIGHT_VERSION}"
npx playwright install chromium
npx playwright test --config=playwright.config.ts
