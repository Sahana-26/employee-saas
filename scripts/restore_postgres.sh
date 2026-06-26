#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: ./scripts/restore_postgres.sh ./backups/file.dump"
  exit 1
fi

BACKUP_FILE="$1"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-employeehub}"
DB_NAME="${DB_NAME:-employeehub}"

cat "$BACKUP_FILE" | docker compose exec -T "$DB_SERVICE" pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists

echo "Restore completed from: $BACKUP_FILE"
