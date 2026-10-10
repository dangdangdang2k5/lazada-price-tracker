#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${APP_ROOT:-/opt/lazada-tracker}"
APP_USER="${APP_USER:-lazada}"
REPO_URL="${REPO_URL:-https://github.com/dangdangdang2k5/lazada-price-tracker.git}"
REPO_REF="${REPO_REF:-main}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root (or with sudo)." >&2
  exit 1
fi

arch="$(dpkg --print-architecture)"
if [[ "$arch" != "arm64" ]]; then
  echo "Expected Ubuntu ARM64 (arm64), detected: $arch" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  git python3 python3-venv python3-pip build-essential sqlite3 ca-certificates curl

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_ROOT" --create-home --shell /usr/sbin/nologin "$APP_USER"
fi

install -d -o "$APP_USER" -g "$APP_USER" -m 750 \
  "$APP_ROOT" "$APP_ROOT/data" "$APP_ROOT/backups" "$APP_ROOT/secrets" "$APP_ROOT/data/debug/lazada" \
  /etc/lazada-tracker

if [[ ! -d "$APP_ROOT/.git" ]]; then
  source_dir="$(mktemp -d /tmp/lazada-tracker-src.XXXXXX)"
  trap 'rm -rf "$source_dir"' EXIT
  git clone --branch "$REPO_REF" --depth 1 "$REPO_URL" "$source_dir"
  cp -a "$source_dir/." "$APP_ROOT/"
  rm -rf "$source_dir"
  trap - EXIT
else
  git -C "$APP_ROOT" fetch --depth 1 origin "$REPO_REF"
  git -C "$APP_ROOT" checkout -q "$REPO_REF"
  git -C "$APP_ROOT" pull --ff-only origin "$REPO_REF"
fi

python3 -m venv "$APP_ROOT/.venv"
"$APP_ROOT/.venv/bin/python" -m pip install --upgrade pip wheel
"$APP_ROOT/.venv/bin/pip" install --requirement "$APP_ROOT/backend/requirements-production.txt"

if [[ ! -f /etc/lazada-tracker/lazada-tracker.env ]]; then
  install -m 600 -o root -g root "$APP_ROOT/.env.example" /etc/lazada-tracker/lazada-tracker.env
  echo "Created /etc/lazada-tracker/lazada-tracker.env; edit its secrets before starting the service."
fi

echo "--- Playwright ARM64 compatibility check ---"
"$APP_ROOT/.venv/bin/python" -c 'from playwright.async_api import async_playwright; print("Playwright Python import: OK")'
"$APP_ROOT/.venv/bin/python" -m playwright install --dry-run chromium || \
  echo "WARNING: Playwright bundled Chromium is not confirmed for ARM64."

if command -v chromium >/dev/null 2>&1; then
  chromium --version || true
elif command -v chromium-browser >/dev/null 2>&1; then
  chromium-browser --version || true
else
  echo "WARNING: No system Chromium detected. HTTP crawler can run; Playwright fallback is unverified."
fi

install -m 644 "$APP_ROOT/deploy/lazada-tracker.service" /etc/systemd/system/lazada-tracker.service
chown -R "$APP_USER":"$APP_USER" "$APP_ROOT"
systemctl daemon-reload

echo "Installation prepared. Review /etc/lazada-tracker/lazada-tracker.env, then run:"
echo "  systemctl enable --now lazada-tracker"
echo "  journalctl -u lazada-tracker -f"
