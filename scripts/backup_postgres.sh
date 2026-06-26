#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-employeehub}"
DB_NAME="${DB_NAME:-employeehub}"
FILE_NAME="${1:-employeehub-$(date +%Y%m%d-%H%M%S).dump}"

mkdir -p "$BACKUP_DIR"
docker compose exec "$DB_SERVICE" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$BACKUP_DIR/$FILE_NAME"
echo "Backup completed: $BACKUP_DIR/$FILE_NAME"
