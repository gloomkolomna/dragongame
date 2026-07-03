# 🐉 Бестиарий драконьих легенд — AGENTS.md

## Проект

VK Mini App + Bot для выращивания драконов через вышивку. Пользователь
активирует дракона по PIN-коду, проходит N шагов (присылая 2 фото + слово
"вышито" в одном сообщении), в конце получает карточку дракона в коллекции.

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend API | Python 3.14 / FastAPI 0.104 / SQLAlchemy 2.x |
| Database | SQLite (WAL mode) |
| Migrations | Alembic |
| Bot | vk_api (longpoll) |
| Frontend | React 18 / TypeScript / Vite 5 |
| Auth | VK ID OAuth 2.0 + JWT |
| Python venv | `api/venv/Scripts/python.exe` |

## Структура

```
/ Коллекция драконов/
  api/
    main.py           # FastAPI app + routes
    models.py         # Все ORM модели (8 таблиц)
    db.py             # Engine + SessionLocal
    config.py         # env-конфиг
    auth.py           # VK OAuth + JWT
    routes/
      admin.py        # CRUD админки (драконы, шаги, юзеры, семейства, сетка)
      collection.py   # Endpoint коллекции для мини-аппа
      auth.py         # OAuth endpoints
    services/
      dragon_service.py  # CRUD драконов + файлы
    alembic/versions/    # Миграции
    tests/
      conftest.py        # TestClient + in-memory SQLite + override auth
      test_models.py
      test_admin_routes.py
  bot/
    main.py           # Longpoll loop + command dispatch
    fsm.py            # FSM: idle, await_pin, await_garden, grow_step_N
    keyboard.py       # VK keyboard builders
    scheduler.py      # Фоновый поток проверки истекших таймаутов
    handlers/
      commands.py     # start, help, status, garden, switch_to
      grow.py         # Обработка шагов (2 фото + "вышито")
      pin.py          # PIN entry flow
    services/
      grow_service.py # Логика шагов, таймаутов, прогресса
      pin_service.py  # PIN validation + activation
      user_service.py # get_or_create_user
    tests/
      conftest.py     # In-memory SQLite
      test_fsm.py
      test_grow_service.py
      test_grow_handler.py
      test_commands.py
      test_scheduler.py
  frontend/           # React SPA
  images/dragons/     # Яйца + взрослые драконы
  plans/              # Документация
  dev.ps1             # Локальный запуск (API :8001, frontend :5173, bot)
```

## База данных — ключевые таблицы

- **dragons** — определения драконов (имя, редкость, PIN, семейство)
- **dragon_steps** — шаги дракона (magic_action, task_description, hint, keyword,
  timeout_hours, timeout_minutes)
- **users** — vk_id, state (FSM), current_dragon_id, current_step
- **user_progress** — user_id + dragon_id + step_number: completed, фото
- **user_dragons** — user_id + dragon_id: completed_at, next_step_available_at,
  timeout_notified
- **families** — семейства/союзы драконов
- **collection_grid** — визуальная сетка коллекции

## Таймауты (механика)

1. Поля `timeout_hours` / `timeout_minutes` на `DragonStep`
2. После завершения шага → `set_step_timeout()` → записывает
   `next_step_available_at` + сбрасывает `timeout_notified = False`
3. При входящем сообщении → `get_timeout_remaining()` → если > 0 — блокировка
4. Чекер (`scheduler.py`) каждые 30с: ищет `next_step_available_at <= now AND
   timeout_notified == False`, шлёт уведомление, ставит `timeout_notified = True`
5. При скипе/рестарте/резете/переключении админом → очистка полей
6. `complete_dragon()` → очищает `next_step_available_at`

## Как запустить

```powershell
.\dev.ps1                       # Всё сразу
.\dev.ps1 -NoFrontend           # Без фронта
.\dev.ps1 -NoBackend            # Без API
.\dev.ps1 -NoBot                # Без бота
```

## Как запустить тесты

```powershell
api\venv\Scripts\python.exe -m pytest api/tests bot/tests -v --tb=short
```

## Миграции

```powershell
cd api
.\venv\Scripts\python.exe -m alembic upgrade head
```

`alembic.ini` в `api/`, `env.py` переопределяет URL из `config.DATABASE_URL`.

## Импорты

- API и bot импортируют `models` напрямую (api/ добавляется в sys.path)
- Bot main.py добавляет корень и `api/` в sys.path
- Тесты добавляют корень и `api/` в sys.path через conftest.py

## Обязательно: прогон тестов

После любого изменения Python-кода (API, бот, сервисы) необходимо
запустить тесты и убедиться, что все проходят:

```powershell
api\venv\Scripts\python.exe -m pytest api/tests bot/tests -v --tb=short
```

Если тесты не проходят — исправить до завершения задачи.

**_58 тестов: 10 API + 4 модели + 16 grow_service + 6 grow_handler + 9 commands + 4 FSM + 7 scheduler + 2 timing._**

## Конвенции кода

- Python: никаких комментариев без запроса
- TypeScript: без комментариев, без лишних типов
- SQLAlchemy: Column, Integer, String, Boolean, Text, ForeignKey, default=
- Все импорты моделей внутри функций (lazy import) в bot/services/*.py
- Пустые строки между определениями классов/функций

## FSM состояния

- `idle` — ожидание
- `await_pin` — ожидание PIN-кода
- `await_garden` — выбор дракона из списка
- `grow_step_N` — выращивание на шаге N
- `is_growing(state)` — проверка, выращивает ли пользователь

## Команды бота

- `start` / `выращивать` — приветствие
- `help` / `помощь` — справка
- `status` / `статус` — текущий прогресс + таймаут
- `garden` / `сменить` / `бестиарий` — список драконов
- `pin` / `дракона` — активация по PIN
- `switch_to` (payload: `{"cmd":"switch_to","dragon_id":N}`) — с нотификации
- `garden_cancel` — отмена переключения

## Обработка шагов

- Ровно 2 фото + слово "вышито" в одном сообщении
- Проверка таймаута перед обработкой
- После шага: advance `current_step`, при таймауте — `set_step_timeout()`
- Последний шаг → `complete_dragon()` → `state = idle`

## Нотификации (scheduler)

- Фоновый поток с `daemon=True`
- Каждые 30с проверяет истекшие таймауты
- Если юзер на этом драконе → присылает описание шага
- Если на другом → присылает кнопку "🐉 Перейти к выращиванию"
