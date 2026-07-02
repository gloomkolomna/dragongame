#!/bin/bash
set -euo pipefail

APP_DIR="/opt/dragons"
API_DIR="$APP_DIR/api"
FRONTEND_DIR="$APP_DIR/frontend"
DB_FILE="$API_DIR/dragons.db"
BACKUP_DIR="$API_DIR/backups"
BACKUPS_TO_KEEP=10
HEALTH_URL="https://belovolovhome.ru/dragons/api/"
LOG_FILE="$API_DIR/deploy.log"

PREV_REV=""
FRESH_DEPLOY=0
BACKUP_PATH=""
MIGRATION_RAN=0
SERVICE_RESTARTED=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

rollback_db() {
    log "ОТКАТ: попытка вернуться к ревизии '$PREV_REV'..."
    if [ "$MIGRATION_RAN" -eq 1 ] && [ -n "$PREV_REV" ] && [ "$FRESH_DEPLOY" -eq 0 ]; then
        cd "$API_DIR" && source venv/bin/activate
        if python -m alembic downgrade "$PREV_REV"; then
            log "ОТКАТ: успешный downgrade."
            return 0
        fi
        log "ОТКАТ: downgrade не удался, восстанавливаю из бэкапа..."
    fi
    if [ -n "$BACKUP_PATH" ] && [ -f "$BACKUP_PATH" ]; then
        cp "$BACKUP_PATH" "$DB_FILE"
        log "ОТКАТ: БД восстановлена из бэкапа."
        return 0
    fi
    log "ОТКАТ: нужно ручное вмешательство."
    return 1
}

on_error() {
    local ec=$?
    log "ДЕПЛОЙ ПРОВАЛЕН (код $ec)."
    rollback_db || log "ОТКАТ не удался."
    if [ "$SERVICE_RESTARTED" -eq 1 ]; then
        systemctl restart dragons-api || true
    fi
    log "Статус: $(systemctl is-active dragons-api || true)."
}
trap on_error ERR

log "=== 1. Текущая ревизия ==="
cd "$API_DIR" && source venv/bin/activate
PREV_REV=$(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)
[ -z "$PREV_REV" ] && FRESH_DEPLOY=1 || log "Ревизия: $PREV_REV"

log "=== 2. Бэкап ==="
mkdir -p "$BACKUP_DIR"
if [ -f "$DB_FILE" ]; then
    BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
    cp "$DB_FILE" "$BACKUP_PATH"
    log "Бэкап: $BACKUP_PATH"
    ls -1t "$BACKUP_DIR"/dragons.db.bak.* | tail -n +$((BACKUPS_TO_KEEP+1)) | xargs rm -f
else
    log "БД не найдена — новая установка."
fi

log "=== 3. git pull ==="
cd "$APP_DIR" && git pull

log "=== 4. Миграции ==="
cd "$API_DIR" && source venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
MIGRATION_RAN=1
log "Ревизия: $(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)"

log "=== 5. Сборка фронта ==="
cd "$FRONTEND_DIR"
rm -rf dist && npm install && npm run build

log "=== 6. Перезапуск ==="
systemctl restart dragons-api
systemctl restart dragons-bot
SERVICE_RESTARTED=1
sleep 3
systemctl is-active dragons-api dragons-bot

log "=== 7. Health-check ==="
for i in 1 2 3 4 5; do
    if curl -fsS -o /dev/null "$HEALTH_URL"; then
        log "=== Деплой успешно завершён ==="
        exit 0
    fi
    log "Попытка $i/5..."
    sleep 3
done
log "Health-check провалился."
false
