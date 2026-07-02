# Deployment Guide — Коллекция драконов

## 0. Сосуществование с Учёт

На сервере уже работает система «Учёт» на стандартных портах:

| Компонент | Учёт | Драконы |
|---|---|---|
| nginx (front) | :80/:443, `/crm/*` | :80/:443, `/dragons/*` |
| gunicorn (API) | :8000, `/crm/api/*` | **:8001**, `/dragons/api/*` |
| База | `/opt/crm/crm/src/backend/uchet.db` | `/opt/dragons/api/dragons.db` |

Оба проекта живут на одном домене `belovolovhome.ru` в разных URL-путях.
Порты gunicorn разные — конфликтов нет. nginx разводит запросы по `location`.

## 1. Архитектура на сервере

```
               ┌─── nginx :80/:443 ──────────────────────┐
               │                                          │
               │  /crm/*          → Учёт (gunicorn :8000) │
               │  /dragons/*      → SPA (dist/)           │
   HTTPS ────→│  /dragons/api/*  → drag.api  :8001       │
               │  /dragons/api/static/* → images/         │
               │                                          │
               └──────────────────────────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  dragons-api         │
                          │  (gunicorn, :8001)   │
                          │  FastAPI             │
                          └──────────┬───────────┘
                                     │
  ┌─────────────────┐               │
  │ dragons-bot      │               │
  │ (Python longpoll)│───────────────┤
  └────────┬─────────┘               │
           │                         │
           ▼                         ▼
  ┌────────────────────────────────────────────┐
  │          SQLite (WAL-режим)                 │
  │   /opt/dragons/api/dragons.db              │
  └────────────────────────────────────────────┘
           ▲
  ┌────────┴────────┐
  │   backup.sh      │  cron daily at 3:00
  └─────────────────┘
```

Три процесса Драконов:
- **dragons-bot** — VK longpoll бот (Python, systemd)
- **dragons-api** — FastAPI админка + Mini App API (gunicorn :8001, systemd)
- **nginx** — общий для Учёт + Драконы, location-блок `/dragons/*`

## 2. Подготовка сервера

### 2.1 Системные зависимости

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git curl

# Node.js 16.x (для сборки фронта)
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install -y nodejs

# Проверка версий
python3 --version   # ≥ 3.10
node --version      # ≥ 16.x
nginx -v
```

### 2.1.5 База данных

SQLite не требует установки — встроена в Python. Достаточно создания файла.
WAL-режим включается через `db.py` при первом запуске:
```python
cursor.execute("PRAGMA journal_mode=WAL")
```

Для ручной проверки БД на сервере пригодится CLI:
```bash
sudo apt install -y sqlite3
```

### 2.2 Пользователь и директории

```bash
# Создаём системного пользователя (если ещё не создан)
sudo useradd -r -s /bin/false -m dragons 2>/dev/null || true

# Структура проекта (РЯДОМ с Учёт, не внутри)
sudo mkdir -p /opt/dragons/{api,api/backups,api/alembic/versions,bot,frontend,images/dragons,deploy}
sudo chown -R dragons:dragons /opt/dragons
```

### 2.3 Клонирование проекта

```bash
cd /opt/dragons
sudo -u dragons git clone https://github.com/your/repo.git .
# или rsync/scp файлы проекта
```

## 3. Python-окружение

```bash
cd /opt/dragons/api
sudo -u dragons python3 -m venv venv
sudo -u dragons venv/bin/pip install -r requirements.txt
```

**requirements.txt** (example):
```
fastapi==0.104.*
uvicorn[standard]==0.24.*
gunicorn==21.*
python-jose[cryptography]==3.*
httpx==0.25.*
python-dotenv==1.*
alembic==1.*
sqlalchemy==2.*
vk_api==11.*
```

## 4. Файл .env

Файл `/opt/dragons/api/.env`:

```bash
# === Flask/FastAPI ===
SECRET_KEY=<random-64-char-string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
DATABASE_URL=sqlite:////opt/dragons/api/dragons.db
APP_ENV=production

# === VK OAuth (админка) ===
VK_CLIENT_ID=1234567
VK_CLIENT_SECRET=abcdef123456
VK_REDIRECT_URI=https://belovolovhome.ru/dragons/api/auth/vk-callback
VK_ALLOWED_IDS=123456789,987654321

# === VK Bot ===
VK_GROUP_TOKEN=vk1.a.abcdef...
VK_GROUP_ID=234567890

# === Фронтенд/Mini App ===
FRONTEND_URL=https://belovolovhome.ru/dragons
VK_MINI_APP_ID=1234567
```

Сгенерировать `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Установить права:
```bash
sudo chmod 600 /opt/dragons/api/.env
sudo chown dragons:dragons /opt/dragons/api/.env
```

## 5. Сборка фронтенда

```bash
cd /opt/dragons/frontend
sudo -u dragons npm install
sudo -u dragons npm run build
# → dist/ готов к отдаче через nginx (location /dragons/)
```

**Важно:** React Router должен использовать `basename="/dragons"`,
иначе роутинг сломается. В `App.tsx`:
```tsx
import { BrowserRouter } from 'react-router-dom';
// ...
<BrowserRouter basename="/dragons">
  {/* ... */}
</BrowserRouter>
```

Все ссылки на API в `api/client.ts` должны использовать относительный путь
`/dragons/api/` (не абсолютный с доменом).

## 6. systemd-сервисы

### 6.1 dragons-api (FastAPI через gunicorn)

Файл `/etc/systemd/system/dragons-api.service`:

```ini
[Unit]
Description=Dragons API (FastAPI gunicorn)
After=network.target

[Service]
User=dragons
Group=dragons
WorkingDirectory=/opt/dragons/api
Environment=PATH=/opt/dragons/api/venv/bin
ExecStart=/opt/dragons/api/venv/bin/gunicorn \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8001 \
    --access-logfile /var/log/dragons/api-access.log \
    --error-logfile /var/log/dragons/api-error.log \
    --timeout 120 \
    api.main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Пояснение параметров:**
- `-w 2` — 2 worker'а (хватит для SQLite с WAL, больше — риск блокировок БД)
- `--bind 127.0.0.1:8001` — слушает localhost (порт 8000 занят Учёт)
- `--timeout 120` — таймаут запроса (на загрузку изображений через админку)

### 6.2 dragons-bot (VK longpoll бот)

Файл `/etc/systemd/system/dragons-bot.service`:

```ini
[Unit]
Description=Dragons VK Bot (longpoll)
After=dragons-api.service
Wants=dragons-api.service

[Service]
User=dragons
Group=dragons
WorkingDirectory=/opt/dragons/bot
Environment=PATH=/opt/dragons/api/venv/bin
Environment=PYTHONPATH=/opt/dragons/api
ExecStart=/opt/dragons/api/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Пояснение:**
- `After=dragons-api.service` — бот стартует после API (ждёт инициализацию БД)
- `RestartSec=10` — при падении longpoll'а бот перезапускается через 10 сек
- `PYTHONPATH=/opt/dragons/api` — импорт общего `db.py` из api/

### 6.3 Активация сервисов

```bash
# Создать папку для логов
sudo mkdir -p /var/log/dragons
sudo chown dragons:dragons /var/log/dragons

# Копировать unit-файлы
sudo cp /opt/dragons/deploy/dragons-api.service /etc/systemd/system/
sudo cp /opt/dragons/deploy/dragons-bot.service /etc/systemd/system/

# Перечитать конфигурацию
sudo systemctl daemon-reload

# Включить автозапуск при старте сервера
sudo systemctl enable dragons-api
sudo systemctl enable dragons-bot

# Запустить
sudo systemctl start dragons-api
sudo systemctl start dragons-bot

# Проверить статус
sudo systemctl status dragons-api dragons-bot
```

### 6.4 Управление сервисами

```bash
# Статус
sudo systemctl status dragons-api dragons-bot

# Логи (последние 50 строк)
sudo journalctl -u dragons-api -n 50 --no-pager
sudo journalctl -u dragons-bot -n 50 --no-pager

# Логи в реальном времени
sudo journalctl -u dragons-bot -f

# Перезапуск
sudo systemctl restart dragons-api
sudo systemctl restart dragons-bot

# Остановка
sudo systemctl stop dragons-api dragons-bot
```

## 7. nginx — блок /dragons

Дополняем существующий конфиг Учёт (уже есть в `/etc/nginx/sites-available/`).
**Не создаём новый server-блок** — добавляем location-блоки `/dragons/*`
внутрь того же server-блока, что обслуживает `belovolovhome.ru`.

Добавить в server-блок (рядом с существующими `/crm/*` location'ами):

```nginx
# ===== Драконы =====

# Статика: изображения драконов
# Mini App грузит: /dragons/api/static/images/{id}.png
location /dragons/api/static/ {
    alias /opt/dragons/images/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# FastAPI (админка + API Mini App)
# Проксируется на gunicorn :8001, префикс /dragons/api убирается
# → FastAPI видит /api/auth, /api/admin/... (чистые пути)
location /dragons/api/ {
    proxy_pass http://127.0.0.1:8001/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /dragons;

    proxy_read_timeout 120s;
    proxy_send_timeout 120s;
    client_max_body_size 10M;
}

# SPA (React — админка + Mini App)
# Все запросы /dragons/* не к API → index.html
location /dragons/ {
    alias /opt/dragons/frontend/dist/;
    index index.html;
    try_files $uri $uri/ /dragons/index.html;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 7d;
        add_header Cache-Control "public, must-revalidate";
    }
}
```

**Ключевые моменты:**
- `proxy_pass http://127.0.0.1:8001/api/;` → nginx отрезает `/dragons` от пути,
  FastAPI не знает о внешнем префиксе. Роуты остаются `/api/auth`, `/api/admin/...`
- `try_files $uri $uri/ /dragons/index.html;` → React SPA с basename `/dragons`
- `X-Forwarded-Prefix: /dragons` → FastAPI использует для формирования
  корректных redirect URL (callback, login)
- SSL, сертификаты и весь server-блок Учёт — не трогаем

### Активация

```bash
# Добавить блоки /dragons в существующий конфиг belovolovhome.ru
sudo nano /etc/nginx/sites-available/belovolovhome  # или как называется файл Учёт

# Проверить конфиг
sudo nginx -t

# Перезагрузить (не restart — чтобы не уронить Учёт)
sudo systemctl reload nginx
```

SSL-сертификат уже настроен для `belovolovhome.ru` (Учёт) — новый не нужен.

## 8. Резервное копирование БД

### backup.sh

Файл `/opt/dragons/deploy/backup.sh`:

```bash
#!/bin/bash
DB_FILE="/opt/dragons/api/dragons.db"
BACKUP_DIR="/opt/dragons/api/backups"
BACKUPS_TO_KEEP=10

mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
cp "$DB_FILE" "$BACKUP_PATH"

# Ротация: удаляем старые, оставляем последние N
ls -1t "$BACKUP_DIR"/dragons.db.bak.* 2>/dev/null | \
    tail -n +$((BACKUPS_TO_KEEP + 1)) | \
    xargs rm -f
```

### cron

```bash
sudo chmod +x /opt/dragons/deploy/backup.sh
sudo chown dragons:dragons /opt/dragons/deploy/backup.sh

# Добавить в cron (каждый день в 3:00)
echo "0 3 * * * root /opt/dragons/deploy/backup.sh" | \
    sudo tee /etc/cron.d/dragons-backup
```

## 9. Порядок первого запуска

```bash
# 1. Системные зависимости
sudo apt install -y python3 python3-venv git sqlite3

# 2. Клонировать проект рядом с Учёт
git clone ... /opt/dragons/
sudo chown -R dragons:dragons /opt/dragons

# 3. Python venv + зависимости
cd /opt/dragons/api
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 4. Создать .env
cp .env.example .env
nano .env     # вписать VK_CLIENT_ID, SECRET_KEY, VK_ALLOWED_IDS
chmod 600 .env

# 5. Инициализировать БД (Alembic, WAL включается автоматически)
cd /opt/dragons/api
source venv/bin/activate
python -m alembic upgrade head
deactivate

# 6. Собрать фронт
cd /opt/dragons/frontend
npm install
npm run build

# 7. Настроить systemd
sudo cp deploy/dragons-api.service /etc/systemd/system/
sudo cp deploy/dragons-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dragons-api dragons-bot

# 8. Добавить блок /dragons в nginx
sudo nano /etc/nginx/sites-available/belovolovhome
sudo nginx -t && sudo systemctl reload nginx

# 9. Бэкап
sudo chmod +x /opt/dragons/deploy/backup.sh
echo "0 3 * * * root /opt/dragons/deploy/backup.sh" | sudo tee /etc/cron.d/dragons-backup

# 10. Запустить
sudo systemctl start dragons-api dragons-bot

# 11. Проверить
sudo systemctl status dragons-api dragons-bot
ls -lh /opt/dragons/api/dragons.db
curl -fsS https://belovolovhome.ru/dragons/api/
curl -fsS https://belovolovhome.ru/dragons/
```

## 10. Деплой обновлений

### deploy.sh

Файл `/opt/dragons/deploy/deploy.sh` (исполняемый):

```bash
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
        cd "$API_DIR"
        source venv/bin/activate
        if python -m alembic downgrade "$PREV_REV"; then
            log "ОТКАТ: успешный downgrade к '$PREV_REV'."
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

# ─── 1. Текущая ревизия ───
log "=== 1. Текущая ревизия ==="
cd "$API_DIR" && source venv/bin/activate
PREV_REV=$(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)
[ -z "$PREV_REV" ] && FRESH_DEPLOY=1 || log "Ревизия: $PREV_REV"

# ─── 2. Бэкап ДО миграции ───
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

# ─── 3. git pull ───
log "=== 3. git pull ==="
cd "$APP_DIR" && git pull

# ─── 4. Миграции ───
log "=== 4. Миграции ==="
cd "$API_DIR" && source venv/bin/activate
pip install -r requirements.txt   # на случай новых зависимостей
python -m alembic upgrade head
MIGRATION_RAN=1
log "Ревизия после миграции: $(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)"

# ─── 5. Сборка фронта ───
log "=== 5. Сборка фронта ==="
cd "$FRONTEND_DIR"
rm -rf dist
npm install
npm run build

# ─── 6. Перезапуск ───
log "=== 6. Перезапуск ==="
systemctl restart dragons-api
systemctl restart dragons-bot
SERVICE_RESTARTED=1
sleep 3
systemctl is-active dragons-api dragons-bot

# ─── 7. Health-check ───
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
```

## 11. Мониторинг и диагностика

```bash
# Проверить, что всё работает
systemctl is-active dragons-api dragons-bot nginx

# Посмотреть использование ресурсов
systemctl status dragons-api dragons-bot --no-pager

# Логи FastAPI
tail -f /var/log/dragons/api-access.log
tail -f /var/log/dragons/api-error.log

# Логи systemd (бот и API)
journalctl -u dragons-bot -f
journalctl -u dragons-api -f

# Логи nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Проверить БД
ls -lh /opt/dragons/api/dragons.db
echo "SELECT COUNT(*) FROM dragons; SELECT COUNT(*) FROM users;" | \
    sqlite3 /opt/dragons/api/dragons.db

# Проверить бэкапы
ls -lht /opt/dragons/api/backups/
```

## 12. Восстановление из бэкапа

```bash
# Остановить сервисы
sudo systemctl stop dragons-api dragons-bot

# Восстановить БД
sudo cp /opt/dragons/api/backups/dragons.db.bak.20260701_030000 \
       /opt/dragons/api/dragons.db
sudo chown dragons:dragons /opt/dragons/api/dragons.db

# Запустить
sudo systemctl start dragons-api dragons-bot
```

## 14. Локальная разработка

### 14.0 Структура и расположение

```
D:\Боты\Коллекция драконов\
├── api/                  ← FastAPI (Python)
│   ├── main.py           ← точка входа
│   ├── .env              ← локальные переменные (не в git)
│   └── venv/             ← виртуальное окружение
├── bot/                  ← VK longpoll бот (Python)
│   └── main.py           ← точка входа (пока заглушка)
├── frontend/             ← React 18 + Vite + TypeScript
│   └── vite.config.ts    ← прокси и base path
├── images/               ← изображения драконов
└── plans/                ← документация
```

### 14.1 Бэкенд (FastAPI, порт 8001)

#### 14.1.1 Первый запуск

```powershell
# 1. Перейти в папку API
cd D:\Боты\Коллекция драконов\api

# 2. Создать venv (один раз)
python -m venv venv

# 3. Активировать и установить зависимости
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Создать .env из шаблона
Copy-Item .env.example .env

# 5. Отредактировать .env — включить dev-режим
#    APP_ENV=dev
#    DEV_LOGIN_ENABLED=true
#    DATABASE_URL=sqlite:///./dragons.db
#    FRONTEND_URL=http://127.0.0.1:5173

# 6. Применить миграции (создаст файл БД dragons.db)
python -m alembic upgrade head

# 7. Запустить
.\venv\Scripts\python -m uvicorn api.main:app --port 8001 --reload
# или (из папки api):
uvicorn api.main:app --port 8001 --reload
```

**Проверка:** открыть http://127.0.0.1:8001/api/ — должен вернуть `{"status":"ok","service":"dragons-api"}`.

#### 14.1.2 Локальный .env (минимальный)

```ini
APP_ENV=dev
DEV_LOGIN_ENABLED=true
SECRET_KEY=dev-secret-key-any-random-string
DATABASE_URL=sqlite:///./dragons.db
FRONTEND_URL=http://127.0.0.1:5173

# Сбросить БД при старте (удаляет все данные и создаёт заново)
# RESET_DB=true

# Для реального VK OAuth (можно не заполнять — работает dev-login)
VK_CLIENT_ID=
VK_CLIENT_SECRET=
VK_REDIRECT_URI=
VK_ALLOWED_IDS=

# Для бота (можно не заполнять)
VK_GROUP_TOKEN=
VK_GROUP_ID=0
```

**Dev-login:** при `DEV_LOGIN_ENABLED=true` можно войти в админку без VK OAuth — на странице логина появится кнопка «Dev Login».

**Сброс БД:** добавьте `RESET_DB=true` в `.env` и перезапустите бэкенд — все таблицы будут пересозданы (удобно при изменении моделей в обход Alembic). После пересоздания удалите `RESET_DB` обратно, чтобы не сбрасывать БД при каждом запуске.

#### 14.1.3 Перезапуск при изменениях

- `--reload` следит за Python-файлами и перезагружает сервер автоматически.
- Если изменения в `routes/admin.py` не подхвачены — остановить (`Ctrl+C`) и запустить заново.

### 14.2 Фронтенд (Vite, порт 5173)

```powershell
# 1. Перейти в папку фронта
cd D:\Боты\Коллекция драконов\frontend

# 2. Установить зависимости (один раз)
npm install

# 3. Запустить дев-сервер
npm run dev
```

**Проверка:** открыть http://127.0.0.1:5173/dragons/admin/login

### 14.3 Как работает прокси

Vite проксирует запросы фронта к API:

```
браузер          →  http://127.0.0.1:5173/dragons/api/admin/dragons
Vite прокси      →  http://127.0.0.1:8001/api/admin/dragons   (rewrite убрал /dragons)
FastAPI          →  обрабатывает /api/admin/dragons
```

Фронт использует относительный путь `/dragons/api/...` для всех запросов к API,
и Vite сам превращает их в запросы к бэкенду на порту 8001.

### 14.4 Бот (VK longpoll)

Бот пока в заглушке (`bot/main.py` — выводит приветствие). Для локального теста:

```powershell
cd D:\Боты\Коллекция драконов
.\api\venv\Scripts\python -m bot.main
```

Для полноценного запуска боту нужны:
- `VK_GROUP_TOKEN` (ключ сообщества VK)
- `VK_GROUP_ID` (ID сообщества)
- Поднятый API (порт 8001) для чтения/записи в БД

Бот использует тот же venv, что и API (импортирует `api.db`, `api.models`).

### 14.5 Mini App — локальная отладка

VK Mini App в продакшене открывается внутри VK (iframe), но локально можно:

1. **Через браузер:** страницы Mini App (`/dragons/app/...`) работают напрямую
   в браузере с моковыми данными (вкладка Collection).

2. **Через VK DevTools:** открыть VK Mini App в режиме разработчика:
   - Зайти в управление VK Mini App → Настройки → Режим разработки
   - Указать URL: `https://belovolovhome.ru/dragons` (или ngrok-туннель)
   - VK Bridge API будет работать, но только на VK-домене или localhost с ngrok

3. **Альтернатива для локального теста:** ngrok
   ```powershell
   ngrok http 5173
   # → https://xxxx.ngrok.io → указать в настройках Mini App VK
   ```

### 14.6 Быстрый старт (шпаргалка)

```powershell
# Терминал 1 — бэкенд
cd D:\Боты\Коллекция драконов\api
.\venv\Scripts\Activate.ps1
uvicorn api.main:app --port 8001 --reload

# Терминал 2 — фронтенд
cd D:\Боты\Коллекция драконов\frontend
npm run dev
```

После запуска обоих:
| Что | URL |
|---|---|
| API health | http://127.0.0.1:8001/api/ |
| Админка (логин) | http://127.0.0.1:5173/dragons/admin/login |
| Админка (дашборд) | http://127.0.0.1:5173/dragons/admin/dashboard |
| Админка (драконы) | http://127.0.0.1:5173/dragons/admin/dragons |
| Mini App (коллекция) | http://127.0.0.1:5173/dragons/app/collection |
| Mini App (детали) | http://127.0.0.1:5173/dragons/app/dragon/1 |

### 14.7 Типовые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `Connection refused` на API | Бэкенд не запущен | Запустить uvicorn (14.1) |
| Страница логина пустая / 404 | Vite не запущен или не тот URL | `npm run dev`, открыть `/dragons/admin/login` |
| Изменения в routes/admin.py не видны | `--reload` не подхватил | Остановить uvicorn и запустить заново |
| Белый экран, ошибки в консоли | Не установлены npm-пакеты | `npm install` |
| `No module named 'api'` | uvicorn запущен не из корня проекта | Запускать из `D:\Боты\Коллекция драконов\api` |
| Не работает VK OAuth локально | Нет валидных VK_CLIENT_ID/SECRET | Использовать dev-login (кнопка на странице логина) |
| Нужно сбросить БД | Изменились модели, нужна чистая БД | Добавить `RESET_DB=true` в `.env` и перезапустить бэкенд |

### 14.8 PIN-коды

Каждый дракон имеет **один** четырёхзначный PIN-код. Код генерируется автоматически при создании дракона (случайные 4 цифры, уникальные).

- Увидеть коды: страница «PIN-коды» в админке — сводная таблица всех драконов
- Код хранится в поле `dragons.pin_code` (VARCHAR(4), UNIQUE)
- Код нельзя задать вручную или удалить — он создаётся вместе с драконом
- Привязка PIN к игроку будет добавлена позже (сейчас таблица показывает: Дракон | PIN-код | Редкость | Тип яйца | Шагов | Активен)
