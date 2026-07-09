# Интеграция VK Donut: донат-бэкенд + HTTP API

## Исходные данные

- **Группа А** (krestiki_s_korgi, ID 206593200): основная группа, VK Donut уже работает
- **Группа Б** (ID 239999455): игровая группа, бот выращивания драконов
- Привилегии для донов — **отдельная задача**, в этом плане только инфраструктура

## Архитектура

```
┌─────────────────────────────────────────────┐
│  belovolovhome.ru/krestiki-s-korgi          │
│  Донат-бэкенд (новый, отдельный проект)      │
│                                             │
│  POST /api/webhooks/donut  ← VK Callback    │
│  GET  /api/donor/{vk_id}   → Игры читают    │
│  GET  /api/health          → healthcheck    │
│                                             │
│  SQLite: donors.db                          │
│    donors(vk_id PK, is_don, don_since,      │
│           updated_at)                       │
└─────────────────────────────────────────────┘
        ▲                       │
        │   HTTP (API key)      │
        │                       ▼
┌───────┴──────────┐   ┌──────────────────┐
│ Игра «Драконы»   │   │ Будущая игра 2   │
│ (бот)            │   │ (бот)            │
│ VK_GROUP: 239..  │   │                  │
└──────────────────┘   └──────────────────┘
```

Почему отдельный бэкенд:
- Несколько игр смогут ходить в один донат-бэкенд
- Изоляция: донат-логика не смешивается с игровой
- Заложена возможность добавить бота в донат-группу позже

---

## Задача 1: Действия пользователя (VK) — без изменений

### 1.1 Числовой ID группы с донатами
Зайти в krestiki_s_korgi → Управление → `group_id=206593200`. Записать точный ID.

### 1.2 Настроить Callback API в группе с донатами
**Управление сообществом → Работа с API → Callback API**

1. Версия API: **5.199**
2. **URL**: `https://belovolovhome.ru/krestiki-s-korgi/api/webhooks/donut`
3. Нажать «Подтвердить» — VK пришлёт тестовый запрос, сервер должен вернуть `confirmation_token`
4. После подтверждения скопировать:
   - **Строка подтверждения** (confirmation token)
   - **Секретный ключ** (secret key)
5. Выбрать события:
   - `donut_subscription_create`
   - `donut_subscription_prolonged`
   - `donut_subscription_expired`
   - `donut_subscription_cancelled`
6. Сохранить

### 1.3 Создать `.env` для донат-бэкенда (в его корне)

```env
SECRET_KEY=<сгенерировать, например openssl rand -hex 32>
DATABASE_URL=sqlite:///donors.db
VK_DONUT_GROUP_ID=206593200
VK_DONUT_CALLBACK_SECRET=<секретный ключ из Callback API>
VK_DONUT_CONFIRMATION_TOKEN=<строка подтверждения>
API_KEY=<сгенерировать ключ для защиты GET /api/donor/>
```

`API_KEY` нужен, чтобы игровые боты авторизовывались при запросе статуса дона. Передаётся в заголовке `X-API-Key`.

### 1.4 Настроить nginx (обязательно **до** нажатия «Подтвердить»)

Callback API VK стучится по публичному URL `https://belovolovhome.ru/krestiki-s-korgi/api/webhooks/donut`. Значит nginx должен принять запрос по префиксу `/krestiki-s-korgi/` и проксировать его на локальный процесс донат-бэкенда (uvicorn/gunicorn, например `127.0.0.1:8010`).

Ключевой момент: приложение отдаёт роуты без префикса (`/api/webhooks/donut`, `/api/donor/...`, `/api/health`), поэтому в nginx префикс `/krestiki-s-korgi` нужно **срезать** (trailing slash в `proxy_pass`).

Пример блока внутри `server { ... }` (тот же, что обслуживает `belovolovhome.ru`, с уже настроенным SSL):

```nginx
location /krestiki-s-korgi/ {
    proxy_pass http://127.0.0.1:8010/;   # слэш в конце срезает /krestiki-s-korgi/

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_read_timeout 30s;
}
```

Проверка сопоставления путей:

| Публичный URL | Уходит на бэкенд как |
|---|---|
| `/krestiki-s-korgi/api/webhooks/donut` | `/api/webhooks/donut` |
| `/krestiki-s-korgi/api/donor/123` | `/api/donor/123` |
| `/krestiki-s-korgi/api/health` | `/api/health` |

Применить конфиг:

```bash
sudo nginx -t          # проверить синтаксис
sudo systemctl reload nginx
```

Проверить, что эндпоинт доступен снаружи (до подтверждения в VK):

```bash
curl https://belovolovhome.ru/krestiki-s-korgi/api/health
# ожидаем: {"status":"ok","service":"donut-backend"}
```

Важно:
- Донат-бэкенд должен быть запущен и слушать `127.0.0.1:8010` (порт согласовать с юзером/деплоем) **до** нажатия «Подтвердить» в VK — иначе VK получит 502 и подтверждение не пройдёт.
- Убедиться, что для `belovolovhome.ru` есть валидный SSL-сертификат (VK требует HTTPS).
- VK при подтверждении ждёт ответ **простой строкой** с `confirmation_token` (без JSON, без кавычек, `Content-Type: text/plain`) и HTTP 200.

---

## Задача 2: Донат-бэкенд — структура проекта

Новый проект в **отдельной директории** (путь уточнит пользователь). Структура:

```
donut-backend/
├── .env
├── requirements.txt        # fastapi, uvicorn, sqlalchemy, httpx
├── main.py                 # FastAPI app + роуты
├── config.py               # env-конфиг
├── models.py               # Таблица donors
├── db.py                   # Engine + SessionLocal + init_db
├── webhook.py              # Логика обработки Callback API
├── api_key.py              # Зависимость проверки X-API-Key
└── tests/
    ├── conftest.py          # TestClient + in-memory SQLite
    └── test_webhook.py      # Тесты webhook + GET /api/donor/
```

### 2.1 config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///donors.db")
VK_DONUT_GROUP_ID = int(os.getenv("VK_DONUT_GROUP_ID", "0"))
VK_DONUT_CALLBACK_SECRET = os.getenv("VK_DONUT_CALLBACK_SECRET", "")
VK_DONUT_CONFIRMATION_TOKEN = os.getenv("VK_DONUT_CONFIRMATION_TOKEN", "")
API_KEY = os.getenv("API_KEY", "")
```

### 2.2 models.py

```python
from sqlalchemy import Column, Integer, Boolean, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Donor(Base):
    __tablename__ = "donors"
    vk_id = Column(Integer, primary_key=True)
    is_don = Column(Boolean, default=False)
    don_since = Column(String, nullable=True, default=None)
    updated_at = Column(String, default="")
```

### 2.3 db.py

Аналог `api/db.py` из игры — движок, `SessionLocal`, `init_db()`, SQLite WAL + foreign keys.

### 2.4 main.py — FastAPI + роуты

```python
from fastapi import FastAPI, Depends, HTTPException
from db import init_db, SessionLocal, get_db
from webhook import process_callback
from api_key import verify_api_key

init_db()
app = FastAPI()

@app.post("/api/webhooks/donut")
async def donut_webhook(request: Request):
    # 1. confirmation → вернуть токен
    # 2. проверить secret
    # 3. обработать событие → обновить donors
    # 4. вернуть "ok"

@app.get("/api/donor/{vk_id}")
def get_donor_status(vk_id: int, db=Depends(get_db), _=Depends(verify_api_key)):
    donor = db.query(Donor).filter(Donor.vk_id == vk_id).first()
    if not donor:
        return {"vk_id": vk_id, "is_don": False, "don_since": None}
    return {"vk_id": donor.vk_id, "is_don": donor.is_don, "don_since": donor.don_since}

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "donut-backend"}
```

### 2.5 api_key.py — защита GET /api/donor/

```python
from fastapi import Header, HTTPException
from config import API_KEY

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
```

### 2.6 webhook.py — логика обработки

```python
from datetime import datetime
from fastapi import HTTPException, Request
from config import VK_DONUT_CALLBACK_SECRET, VK_DONUT_CONFIRMATION_TOKEN, VK_DONUT_GROUP_ID

async def process_callback(request: Request, db):
    body = await request.json()

    event_type = body.get("type", "")
    if event_type == "confirmation":
        return VK_DONUT_CONFIRMATION_TOKEN  # str, не JSON

    secret = body.get("secret", "")
    if secret != VK_DONUT_CALLBACK_SECRET:
        raise HTTPException(status_code=403)

    obj = body.get("object", {})
    user_id = obj.get("user_id")
    if not user_id:
        return "ok"

    from models import Donor
    donor = db.query(Donor).filter(Donor.vk_id == user_id).first()
    now = datetime.now().isoformat()

    if event_type in ("donut_subscription_create", "donut_subscription_prolonged"):
        if not donor:
            donor = Donor(vk_id=user_id, is_don=True, don_since=now, updated_at=now)
            db.add(donor)
        else:
            donor.is_don = True
            donor.don_since = now
            donor.updated_at = now
    elif event_type in ("donut_subscription_expired", "donut_subscription_cancelled"):
        if donor:
            donor.is_don = False
            donor.updated_at = now
    else:
        pass  # неизвестный тип — ok

    db.commit()
    return "ok"
```

Группа (`group_id`) в теле запроса игнорируется — принимаем события только от одной группы (та, что настроена в Callback API). Можно добавить проверку `body.get("group_id") == VK_DONUT_GROUP_ID` для дополнительной безопасности.

### 2.7 requirements.txt

```
fastapi>=0.104,<1.0
uvicorn[standard]>=0.24,<1.0
sqlalchemy>=2.0,<3.0
python-dotenv>=1.0,<2.0
httpx>=0.25,<1.0
pytest>=7.0,<9.0
```

---

## Задача 3: Бот игры — чтение статуса дона (отдельно)

Бот игры «Драконы» будет запрашивать донат-бэкенд:

```python
import httpx

DONUT_API_URL = "https://belovolovhome.ru/krestiki-s-korgi/api/donor"
DONUT_API_KEY = "<тот же API_KEY из .env донат-бэкенда>"

def check_don(vk_id: int) -> bool:
    try:
        resp = httpx.get(f"{DONUT_API_URL}/{vk_id}", headers={"X-API-Key": DONUT_API_KEY})
        return resp.json().get("is_don", False)
    except Exception:
        return False
```

**Это не входит в текущий план** — будет отдельной задачей вместе с привилегиями.

---

## Задача 4: Тесты

Файл: `donut-backend/tests/test_webhook.py`

- `test_confirmation_returns_token` — POST confirmation → возвращает токен (строка, не JSON)
- `test_subscription_create_new_donor` — create → новый Donor, is_don=True
- `test_subscription_create_existing_donor` — create на существующего → is_don=True
- `test_subscription_prolonged_sets_is_don` — prolong → is_don=True
- `test_subscription_expired_clears_is_don` — expired → is_don=False
- `test_subscription_cancelled_clears_is_don` — cancelled → is_don=False
- `test_invalid_secret_returns_403` — неверный secret → 403
- `test_unknown_event_returns_ok` — неизвестный тип события → "ok"
- `test_get_donor_without_api_key` — GET без заголовка → 403
- `test_get_donor_with_invalid_api_key` — GET с неверным ключом → 403
- `test_get_donor_existing` — GET существующего дона → is_don=True, don_since
- `test_get_donor_not_found` — GET несуществующего → is_don=False

### conftest.py

Стандартный: `TestClient` + override `get_db` на in-memory SQLite. `config.API_KEY` задаётся в `@pytest.fixture(autouse=True)`.

---

## Задача 5: Валидация

1. Запустить тесты донат-бэкенда:
   ```powershell
   <путь-к-венву-донат-бэкенда>\python.exe -m pytest tests -v --tb=short
   ```
2. После деплоя — зайти в настройки Callback API группы krestiki_s_korgi, нажать «Подтвердить», должно пройти успешно
3. Попросить тестового пользователя оформить/отменить подписку — проверить `GET /api/donor/{vk_id}`

---

## Порядок выполнения

| # | Задача | Зависимость |
|---|--------|-------------|
| 1 | Пользователь: получить ID группы, настроить Callback API, подготовить .env | — |
| 2 | Создать структуру donut-backend/ (config.py, models.py, db.py) | — |
| 3 | webhook.py — логика обработки событий | 2 |
| 4 | main.py — FastAPI app + роуты | 2, 3 |
| 5 | api_key.py — защита GET /api/donor/ | 4 |
| 6 | Тесты: conftest.py + test_webhook.py | 4 |
| 7 | Прогон тестов | 6 |
| 8 | Деплой на belovolovhome.ru/krestiki-s-korgi | 7 |
| 9 | Подтверждение Callback API в настройках VK | 8 |
| 10 | Ручная проверка с реальной подпиской | 9 |

**Задачи 2 и 3 можно делать параллельно.** Задача 4 зависит от обеих.

---

## Открытый вопрос

Путь к директории `donut-backend/` на сервере и в файловой системе — уточнить у пользователя при реализации.
