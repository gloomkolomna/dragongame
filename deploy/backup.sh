#!/bin/bash
# Daily DB backup script
DB_FILE="/opt/dragons/api/dragons.db"
BACKUP_DIR="/opt/dragons/api/backups"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
cp "$DB_FILE" "$BACKUP_PATH"

find "$BACKUP_DIR" -name "dragons.db.bak.*" -type f -mtime +$RETENTION_DAYS -delete
