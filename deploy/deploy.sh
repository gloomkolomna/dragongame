#!/bin/bash
#
# Деплой системы «Коллекция драконов» на прод.
# Логика:
#   1. Фиксируем текущую ревизию Alembic (точка отката БД) и git (точка отката кода).
#   2. Бэкап БД строго до миграции. Бэкап dist (фронтенд) до сборки.
#   3. git pull.
#   4. alembic upgrade head.
#   5. Сборка фронта + рестарт сервисов (dragons-api + dragons-bot).
#   6. Health-check после рестарта.
#   7. При ЛЮБОЙ ошибке на этапах 3–6:
#      — откат БД (downgrade или бэкап)
#      — откат кода (git reset --hard)
#      — восстановление старого dist (фронтенда)
#      — переустановка зависимостей от старой версии
#      — рестарт сервисов
#

set -euo pipefail

# ===== Конфигурация =====
APP_DIR="/opt/dragons"
API_DIR="$APP_DIR/api"
FRONTEND_DIR="$APP_DIR/frontend"
DB_FILE="$API_DIR/dragons.db"
BACKUP_DIR="$API_DIR/backups"
BACKUPS_TO_KEEP=10
GIT_REMOTE="https://github.com/gloomkolomna/dragongame"
GIT_BRANCH="main"
HEALTH_URL="https://belovolovhome.ru/dragons/api/"
LOG_FILE="$API_DIR/deploy.log"

# Флаги состояния
PREV_REV=""                   # ревизия Alembic до миграции
PREV_GIT=""                   # git revision до pull
FRESH_DEPLOY=0
BACKUP_PATH=""
DIST_BACKUP_PATH=""            # бэкап папки dist (если был)
MIGRATION_RAN=0
BUILD_RAN=0                   # 1, если сборка фронта уже запускалась
SERVICES_RESTARTED=0

mkdir -p "$BACKUP_DIR"

# ===== Логирование =====
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ===== Откат БД =====
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

    if [ -n "$BACKUP_PATH" ] && [ -f "$BACKUP_PATH" ]; then
        log "ОТКАТ: восстановление БД из '$BACKUP_PATH'..."
        cp "$BACKUP_PATH" "$DB_FILE"
        log "ОТКАТ: БД восстановлена из бэкапа."
        return 0
    fi

    log "ОТКАТ: нет ни точки отката, ни бэкапа — состояние БД неизвестно, требуется ручное вмешательство!"
    return 1
}

# ===== Полный откат: БД + код + фронтенд + сервисы =====
rollback_all() {
    log "=== ПОЛНЫЙ ОТКАТ ВСЕХ КОМПОНЕНТОВ ==="

    rollback_db || log "ОТКАТ: не удалось полностью откатить БД."

    if [ -n "$PREV_GIT" ]; then
        log "ОТКАТ: сброс git к '$PREV_GIT'..."
        cd "$APP_DIR"
        git reset --hard "$PREV_GIT"
        git clean -fd 2>/dev/null || true
        log "ОТКАТ: git сброшен к '$PREV_GIT'."
    else
        log "ОТКАТ: предыдущая git-ревизия неизвестна, пропускаю сброс кода."
    fi

    # Переустановка зависимостей от старой версии кода
    log "ОТКАТ: переустановка Python-зависимостей..."
    cd "$API_DIR"
    source venv/bin/activate
    pip install -r requirements.txt || log "ОТКАТ: pip install завершился с ошибкой (не критично)."

    # Восстановление старого фронтенда
    if [ -n "$DIST_BACKUP_PATH" ] && [ -d "$DIST_BACKUP_PATH" ]; then
        log "ОТКАТ: восстановление старого фронтенда из '$DIST_BACKUP_PATH'..."
        rm -rf "$FRONTEND_DIR/dist"
        mv "$DIST_BACKUP_PATH" "$FRONTEND_DIR/dist"
    fi

    log "ОТКАТ: перезапуск сервисов..."
    systemctl restart dragons-api dragons-bot || true

    # Очистка временного бэкапа dist
    rm -rf "$FRONTEND_DIR/dist.bak" 2>/dev/null || true

    log "ОТКАТ завершён. API: $(systemctl is-active dragons-api || true). Bot: $(systemctl is-active dragons-bot || true)."
}

# ===== Ловушка ошибок =====
on_error() {
    local exit_code=$?
    log "ДЕПЛОЙ ПРОВАЛЕН (код $exit_code). Запускаю полный откат..."
    trap - ERR
    rollback_all
    log "Деплой завершён с ошибкой. API: $(systemctl is-active dragons-api || true). Bot: $(systemctl is-active dragons-bot || true)."
}
trap on_error ERR

# ===== 1. Текущая ревизия БД + git =====
log "=== 1. Фиксация текущего состояния ==="
cd "$APP_DIR"

PREV_GIT=$(git rev-parse HEAD 2>/dev/null || echo "")
if [ -n "$PREV_GIT" ]; then
    log "Git-ревизия до деплоя: $PREV_GIT"
else
    log "Не удалось определить текущую git-ревизию."
fi

cd "$API_DIR"
source venv/bin/activate

PREV_REV=$(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)
if [ -z "$PREV_REV" ]; then
    log "Текущая ревизия БД не определена (пустая/новая БД)."
    FRESH_DEPLOY=1
else
    log "Текущая ревизия БД: $PREV_REV"
fi

# ===== 2. Бэкап БД + dist =====
log "=== 2. Резервное копирование ==="

# Бэкап БД
if [ -f "$DB_FILE" ]; then
    BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
    cp "$DB_FILE" "$BACKUP_PATH"
    log "Бэкап БД создан: $BACKUP_PATH ($(du -h "$BACKUP_PATH" | cut -f1))"

    ls -1t "$BACKUP_DIR"/dragons.db.bak.* 2>/dev/null | tail -n +$((BACKUPS_TO_KEEP + 1)) | while read -r old; do
        rm -f "$old"
        log "Удалён старый бэкап: $old"
    done
else
    log "Внимание: файл БД '$DB_FILE' не найден — бэкап пропущен."
    BACKUP_PATH=""
fi

# Бэкап старого dist (чтобы при откате фронтенд остался рабочим)
if [ -d "$FRONTEND_DIR/dist" ]; then
    DIST_BACKUP_PATH="$FRONTEND_DIR/dist.bak"
    rm -rf "$DIST_BACKUP_PATH"
    cp -r "$FRONTEND_DIR/dist" "$DIST_BACKUP_PATH"
    log "Бэкап dist создан: $DIST_BACKUP_PATH"
fi

# ===== 3. Git pull =====
log "=== 3. Git pull ==="
cd "$APP_DIR"
rm -f frontend/tsconfig.tsbuildinfo
git fetch "$GIT_REMOTE" "$GIT_BRANCH"
git reset --hard FETCH_HEAD

# ===== 4. Зависимости + миграции =====
log "=== 4. Установка зависимостей и миграции ==="
cd "$API_DIR"
source venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
MIGRATION_RAN=1
log "Миграции применены. Текущая ревизия: $(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)"

# ===== 5. Сборка фронтенда =====
log "=== 5. Сборка фронтенда ==="
cd "$FRONTEND_DIR"
rm -rf "$FRONTEND_DIR/dist"
npm install
npm run build
BUILD_RAN=1

# ===== 6. Перезапуск сервисов =====
log "=== 6. Перезапуск сервисов ==="
systemctl restart dragons-api
systemctl restart dragons-bot
SERVICES_RESTARTED=1
sleep 3
systemctl status dragons-api dragons-bot --no-pager | tee -a "$LOG_FILE" || true

# ===== 7. Health-check =====
log "=== 7. Health-check ==="
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
    false
fi

log "=== Деплой успешно завершён ==="
log "Проверь: https://belovolovhome.ru/dragons/"

# Очистка временных файлов после успешного деплоя
rm -rf "$DIST_BACKUP_PATH" 2>/dev/null || true
