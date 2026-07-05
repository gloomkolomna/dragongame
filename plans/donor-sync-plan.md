# Интеграция Donut: синхронизация донат-статуса в игре «Драконы»

## Исходные данные

- **Donut-бэкенд** (отдельный проект): `belovolovhome.ru/krestiki-s-korgi/`
  - `GET /api/donor/{vk_id}` — возвращает `{"vk_id": ..., "is_don": bool, "don_since": ...}`
  - Авторизация: заголовок `X-API-Key`
- **Игра «Драконы»**: FastAPI (Группа Б, ID 239999455) + бот (Longpoll)
- **Привилегии донатов** — отдельная задача, в этом плане только инфраструктура синхронизации

## Архитектура

```
  Donut-бэкенд
  GET /api/donor/{vk_id}
        ▲
        │  HTTP (X-API-Key)
        │
  ┌─────┴──────────────────┐
  │  Игра «Драконы»        │
  │                        │
  │  background thread ────┤  раз в 24ч
  │  (bot/services/        │
  │   donor_sync.py)       │
  │                        │
  │  donor_cache table     │
  │  (game DB)             │
  └────────────────────────┘
```

## Модель: `DonorCache`

```python
class DonorCache(Base):
    __tablename__ = "donor_cache"
    vk_id = Column(Integer, primary_key=True)
    is_don = Column(Boolean, default=False)
    don_since = Column(String, nullable=True)
    updated_at = Column(String, default="")       # когда обновили статус
    last_synced_at = Column(String, default="")   # когда ходили в donut-backend
```

Отдельная таблица — не смешивается с игровым FSM и не требует миграции существующих таблиц.

## Конфиг (`api/config.py`)

```python
DONUT_API_URL = os.getenv("DONUT_API_URL", "").rstrip("/")
DONUT_API_KEY = os.getenv("DONUT_API_KEY", "")
DONOR_SYNC_INTERVAL_HOURS = int(os.getenv("DONOR_SYNC_INTERVAL_HOURS", "24"))
```

## Воркер: `bot/services/donor_sync.py`

Паттерн — копия `bot/scheduler.py`:

```python
def run_donor_sync(session_factory, interval_hours=24):
    while True:
        db = session_factory()
        try:
            _sync_all(db)
        except Exception as e:
            log_error(...)
        finally:
            db.close()
        time.sleep(interval_hours * 3600)


def _sync_all(db):
    users = db.query(User).all()
    for user in users:
        # httpx.get → donut-backend
        # upsert donor_cache
        # commit per user
```

### Логика `_sync_all`

1. SELECT всех `users`
2. Для каждого `user.vk_id`:
   - `httpx.get(f"{DONUT_API_URL}/{vk_id}", headers={"X-API-Key": ...}, timeout=10)`
   - Если 200: upsert `DonorCache` (is_don, don_since, updated_at, last_synced_at)
   - Если не 200 / ошибка: логирует, переходит к следующему
3. commit после каждого пользователя (изоляция ошибок)

## Интеграция в `bot/main.py`

```python
from bot.donor_sync import run_donor_sync

donor_sync_thread = threading.Thread(
    target=run_donor_sync,
    args=(SessionLocal, config.DONOR_SYNC_INTERVAL_HOURS),
    daemon=True,
)
donor_sync_thread.start()
```

Вторая daemon-нить рядом с `run_timeout_checker`.

## Изменения по файлам

| Файл | Действие |
|---|---|
| `api/models.py` | Добавить модель `DonorCache` |
| `api/config.py` | `DONUT_API_URL`, `DONUT_API_KEY`, `DONOR_SYNC_INTERVAL_HOURS` |
| `bot/services/donor_sync.py` | Создать — воркер |
| `bot/main.py` | Запустить вторую daemon-нить |
| `api/alembic/versions/` | Миграция: `op.create_table("donor_cache")` |
| `api/routes/admin.py` | `GET /admin/donors` — просмотр кеша |
| `bot/tests/test_donor_sync.py` | Тесты (мок httpx) |
| `api/tests/test_donor_cache.py` | Тесты модели + admin endpoint |

## Что отложено

- **Callback API для Группы Б** — детекция `group_join` в реальном времени
- **Привилегии донатов** — отдельная задача после инфраструктуры

## Тесты

### `bot/tests/test_donor_sync.py`
- `test_sync_creates_cache_row` — donut вернул is_don=True → новая строка
- `test_sync_updates_existing` — повторный вызов обновляет `updated_at`
- `test_sync_sets_is_don_false` — donut вернул is_don=False
- `test_sync_handles_http_error` — donut недоступен → пропуск, без падения
- `test_sync_handles_user_not_found` — donut вернул 404 → is_don=False
- `test_sync_no_users` — пустая БД → без ошибок

### `api/tests/test_donor_cache.py`
- `test_create_donor_cache_row` — создать строку, прочитать
- `test_admin_get_donors` — GET /admin/donors возвращает кеш

## Порядок реализации

| # | Задача | Зависимость |
|---|--------|-------------|
| 1 | Модель + конфиг | — |
| 2 | Миграция | 1 |
| 3 | `bot/services/donor_sync.py` | 1 |
| 4 | Запуск нити в `bot/main.py` | 3 |
| 5 | `GET /admin/donors` | 1 |
| 6 | Тесты: `test_donor_cache.py` | 1, 5 |
| 7 | Тесты: `test_donor_sync.py` | 3 |
| 8 | Прогон всех тестов | 6, 7 |
