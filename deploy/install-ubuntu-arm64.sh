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
  git python3.10 python3.10-venv python3-pip build-essential sqlite3 ca-certificates curl

python3.10 -c 'import sys; assert sys.version_info[:2] == (3, 10), sys.version; print("Python:", sys.version)'

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home /nonexistent --no-create-home --shell /usr/sbin/nologin "$APP_USER"
fi

if [[ ! -d "$APP_ROOT/.git" ]]; then
  if [[ -e "$APP_ROOT" ]] && [[ -n "$(find "$APP_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "Refusing to clone into non-empty non-Git directory: $APP_ROOT" >&2
    exit 1
  fi
  git clone --branch "$REPO_REF" --depth 1 "$REPO_URL" "$APP_ROOT"
else
  # This script runs as root, matching the root-owned checkout. Do not use a
  # global safe.directory exception and do not discard local source changes.
  if [[ -n "$(git -C "$APP_ROOT" status --porcelain --untracked-files=normal)" ]]; then
    echo "Refusing to update: repository has local changes or untracked files." >&2
    echo "Commit/stash or inspect them before re-running this script." >&2
    exit 1
  fi
  remote_ref="origin/$REPO_REF"
  fetch_refspec="+refs/heads/$REPO_REF:refs/remotes/origin/$REPO_REF"

  # A shallow checkout does not necessarily contain the common ancestor needed
  # by merge-base. Deepen it before deciding whether a fast-forward is safe.
  # This changes only origin/<branch>, never the worktree or local HEAD.
  if [[ "$(git -C "$APP_ROOT" rev-parse --is-shallow-repository)" == "true" ]]; then
    git -C "$APP_ROOT" fetch --unshallow --prune origin "$fetch_refspec"
  else
    git -C "$APP_ROOT" fetch --prune origin "$fetch_refspec"
  fi

  if git -C "$APP_ROOT" merge-base --is-ancestor HEAD "$remote_ref"; then
    git -C "$APP_ROOT" merge --ff-only "$remote_ref"
  elif git -C "$APP_ROOT" merge-base --is-ancestor "$remote_ref" HEAD; then
    echo "Refusing to update: local HEAD is ahead of $remote_ref." >&2
    echo "No reset, checkout, or overwrite was performed." >&2
    exit 1
  else
    echo "Refusing to update: local and remote histories have diverged." >&2
    echo "No reset, checkout, or overwrite was performed." >&2
    exit 1
  fi
fi

# Source and virtual environment are root-owned. The service account can read
# and execute them but only owns the explicit runtime directories below.
chown -R root:root "$APP_ROOT/.git" "$APP_ROOT/backend" "$APP_ROOT/frontend" "$APP_ROOT/deploy" "$APP_ROOT/scripts"
chown root:root "$APP_ROOT" "$APP_ROOT/.env.example" "$APP_ROOT/.gitignore" "$APP_ROOT/Dockerfile" "$APP_ROOT/docker-compose.yml" "$APP_ROOT/products.json" "$APP_ROOT/render.yaml" "$APP_ROOT/README.md"
chmod -R go-w "$APP_ROOT/.git" "$APP_ROOT/backend" "$APP_ROOT/frontend" "$APP_ROOT/deploy" "$APP_ROOT/scripts"
chmod -R a+rX "$APP_ROOT/backend" "$APP_ROOT/frontend" "$APP_ROOT/deploy" "$APP_ROOT/scripts"

python3.10 -m venv "$APP_ROOT/.venv"
"$APP_ROOT/.venv/bin/python" -m pip install --upgrade pip wheel
"$APP_ROOT/.venv/bin/pip" install --requirement "$APP_ROOT/backend/requirements-production.txt"

install -d -o "$APP_USER" -g "$APP_USER" -m 750 \
  "$APP_ROOT/data" "$APP_ROOT/backups" "$APP_ROOT/secrets" "$APP_ROOT/data/debug/lazada"
# Preserve runtime content while fixing ownership after a root-run installation.
# These are the only application-owned writable paths.
chown -R "$APP_USER":"$APP_USER" "$APP_ROOT/data" "$APP_ROOT/backups" "$APP_ROOT/secrets"
chmod -R u+rwX,go-rwx "$APP_ROOT/data" "$APP_ROOT/backups" "$APP_ROOT/secrets"
chmod -R a+rX "$APP_ROOT/.venv"
install -d -o root -g root -m 750 /etc/lazada-tracker

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
systemctl daemon-reload

echo "Installation prepared. Review /etc/lazada-tracker/lazada-tracker.env, then run:"
echo "  systemctl enable --now lazada-tracker"
echo "  journalctl -u lazada-tracker -f"
