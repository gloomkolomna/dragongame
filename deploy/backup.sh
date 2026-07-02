#!/bin/bash
# Daily DB backup script
DB_FILE="/opt/dragons/api/dragons.db"
BACKUP_DIR="/opt/dragons/api/backups"
BACKUPS_TO_KEEP=10

mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
cp "$DB_FILE" "$BACKUP_PATH"

ls -1t "$BACKUP_DIR"/dragons.db.bak.* 2>/dev/null | \
    tail -n +$((BACKUPS_TO_KEEP + 1)) | \
    xargs rm -f
