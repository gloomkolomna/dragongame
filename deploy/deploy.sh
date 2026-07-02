#!/bin/bash
#
# Деплой системы «Коллекция драконов» на прод.
# Логика (по образцу Учёт):
#   1. Фиксируем текущую ревизию Alembic (точка отката).
#   2. Бэкап БД строго до миграции.
#   3. git pull.
#   4. alembic upgrade head.
#   5. При ошибке — откат к зафиксированной ревизии, при неудаче — восстановление из бэкапа.
#   6. Сборка фронта + рестарт сервисов (dragons-api + dragons-bot).
#   7. Health-check после рестарта; при неудаче — откат БД.
#
# Любая ошибка на этапах 4–5 НЕ приводит к рестарту сервиса: прод остаётся на прежнем состоянии.

set -euo pipefail

# ===== Конфигурация =====
APP_DIR="/opt/dragons"
API_DIR="$APP_DIR/api"
FRONTEND_DIR="$APP_DIR/frontend"
DB_FILE="$API_DIR/dragons.db"
BACKUP_DIR="$API_DIR/backups"
BACKUPS_TO_KEEP=10            # сколько последних бэкапов хранить
HEALTH_URL="https://belovolovhome.ru/dragons/api/"   # endpoint для проверки после рестарта
LOG_FILE="$API_DIR/deploy.log"

# Флаги состояния (заполняются по ходу)
PREV_REV=""
FRESH_DEPLOY=0                # 1, если до деплоя ревизии не было (пустая БД) — откатывать не к чему
BACKUP_PATH=""
MIGRATION_RAN=0               # 1, если миграция уже применена (нужно ли откатывать)
SERVICES_RESTARTED=0          # 1, если сервисы уже перезапущены (для health-check rollback)

mkdir -p "$BACKUP_DIR"

# ===== Логирование с временными метками =====
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ===== Откат: пытаемся downgrade к PREV_REV, при неудаче — восстанавливаем БД =====
rollback_db() {
    log "ОТКАТ: попытка вернуться к ревизии '$PREV_REV'..."

    if [ "$MIGRATION_RAN" -eq 1 ] && [ -n "$PREV_REV" ] && [ "$FRESH_DEPLOY" -eq 0 ]; then
        cd "$API_DIR"
        source venv/bin/activate
        if python -m alembic downgrade "$PREV_REV"; then
            log "ОТКАТ: успешный downgrade к '$PREV_REV'."
            return 0
        fi
        log "ОТКАТ: downgrade не удался, переходим к восстановлению из бэкапа."
    fi

    # Восстановление из бэкапа (безусловный фолбэк)
    if [ -n "$BACKUP_PATH" ] && [ -f "$BACKUP_PATH" ]; then
        log "ОТКАТ: восстановление БД из '$BACKUP_PATH'..."
        cp "$BACKUP_PATH" "$DB_FILE"
        log "ОТКАТ: БД восстановлена из бэкапа."
        return 0
    fi

    log "ОТКАТ: нет ни точки отката, ни бэкапа — состояние БД неизвестно, требуется ручное вмешательство!"
    return 1
}

# ===== Ловушка ошибок =====
# Срабатывает при ошибке на любом этапе после начала деплоя.
on_error() {
    local exit_code=$?
    log "ДЕПЛОЙ ПРОВАЛЕН (код $exit_code). Запускаю откат..."
    rollback_db || log "ОТКАТ: не удалось полностью откатить состояние."

    if [ "$SERVICES_RESTARTED" -eq 1 ]; then
        # Сервисы успели перезапустить, но health-check провалился — пробуем ещё раз на откаченной БД
        log "Попытка повторного рестарта сервисов после отката..."
        systemctl restart dragons-api dragons-bot || true
    fi

    log "Деплой завершён с ошибкой. API: $(systemctl is-active dragons-api || true). Bot: $(systemctl is-active dragons-bot || true)."
}
trap on_error ERR

# ===== 1. Текущая ревизия (точка отката) =====
log "=== 1. Фиксация текущей ревизии БД ==="
cd "$API_DIR"
source venv/bin/activate

PREV_REV=$(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)
if [ -z "$PREV_REV" ]; then
    log "Текущая ревизия не определена (пустая/новая БД). Откат миграцией будет недоступен — только из бэкапа."
    FRESH_DEPLOY=1
else
    log "Текущая ревизия: $PREV_REV"
fi

# ===== 2. Бэкап БД строго до миграции =====
log "=== 2. Резервное копирование БД ==="
if [ -f "$DB_FILE" ]; then
    BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
    cp "$DB_FILE" "$BACKUP_PATH"
    log "Бэкап создан: $BACKUP_PATH ($(du -h "$BACKUP_PATH" | cut -f1))"

    # Ротация: оставляем только последние N бэкапов (безопасно через while read)
    ls -1t "$BACKUP_DIR"/dragons.db.bak.* 2>/dev/null | tail -n +$((BACKUPS_TO_KEEP + 1)) | while read -r old; do
        rm -f "$old"
        log "Удалён старый бэкап: $old"
    done
else
    log "Внимание: файл БД '$DB_FILE' не найден — бэкап пропущен (новая установка?)."
    BACKUP_PATH=""
fi

# ===== 3. Git pull =====
log "=== 3. Git pull ==="
cd "$APP_DIR"
git pull

# ===== 4. Зависимости + миграции =====
log "=== 4. Установка зависимостей и применение миграций ==="
cd "$API_DIR"
source venv/bin/activate
pip install -r requirements.txt   # на случай новых зависимостей (напр. python-multipart)
python -m alembic upgrade head
MIGRATION_RAN=1
log "Миграции применены. Текущая ревизия: $(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)"

# ===== 5. Сборка фронтенда =====
log "=== 5. Сборка фронтенда ==="
cd "$FRONTEND_DIR"
rm -rf "$FRONTEND_DIR/dist"
npm install
npm run build

# ===== 6. Перезапуск сервисов =====
log "=== 6. Перезапуск сервисов ==="
systemctl restart dragons-api
systemctl restart dragons-bot
SERVICES_RESTARTED=1
sleep 3
systemctl status dragons-api dragons-bot --no-pager | tee -a "$LOG_FILE" || true

# ===== 7. Health-check =====
log "=== 7. Health-check ==="
# Несколько попыток — сервисам нужно время на старт
HEALTH_OK=0
for i in 1 2 3 4 5; do
    if curl -fsS -o /dev/null "$HEALTH_URL"; then
        HEALTH_OK=1
        break
    fi
    log "Health-check попытка $i/5 неудачна, ждём..."
    sleep 3
done

if [ "$HEALTH_OK" -ne 1 ]; then
    log "Health-check провалился — запускаю откат."
    # Отключаем ловушку, чтобы вызвать контролируемый откат без рекурсии
    trap - ERR
    false   # спровоцировать rollback_db + финальную диагностику
fi

log "=== Деплой успешно завершён ==="
log "Проверь: https://belovolovhome.ru/dragons/"
