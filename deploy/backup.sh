#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${APP_ROOT:-/opt/lazada-tracker}"
DB_FILE="${DB_FILE:-$APP_ROOT/data/lazada_tracker.db}"
BACKUP_DIR="${BACKUP_DIR:-$APP_ROOT/backups}"

if [[ "$(id -un)" != "${APP_USER:-lazada}" ]]; then
  echo "Run this backup as the lazada service user, for example: sudo -u lazada $0" >&2
  exit 1
fi

if [[ ! -f "$DB_FILE" ]]; then
  echo "Database not found: $DB_FILE" >&2
  exit 1
fi

install -d -m 700 "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$BACKUP_DIR/lazada_tracker_$timestamp.db"
sqlite3 "$DB_FILE" ".backup '$backup_file'"
chmod 600 "$backup_file"
find "$BACKUP_DIR" -type f -name 'lazada_tracker_*.db' -mtime +14 -delete
echo "SQLite backup created: $backup_file"
