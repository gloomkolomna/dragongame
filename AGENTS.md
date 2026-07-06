# 🐉 Бестиарий драконьих легенд — AGENTS.md

## Проект

VK Mini App + Bot для выращивания драконов через вышивку. Пользователь
активирует дракона по PIN-коду, проходит N шагов — отправляет текстовое
сообщение с количеством вышитых крестиков (например, «вышито 1500»),
в конце получает карточку дракона в коллекции.

## Важное

- Если пользователь задает вопрос - сперва ответить.
- **Если что-то не понятно — задать вопрос пользователю прежде чем делать.** Не додумывать.

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
    models.py         # Все ORM модели (10 таблиц)
    db.py             # Engine + SessionLocal
    config.py         # env-конфиг
    auth.py           # VK OAuth + JWT
    middleware.py     # Логирование ошибочных запросов (4xx/5xx)
    routes/
      admin.py        # CRUD админки (драконы, шаги, юзеры, семейства, сетка)
      collection.py   # Endpoint коллекции для мини-аппа
      auth.py         # OAuth endpoints
    services/
      dragon_service.py  # CRUD драконов + файлы (с timestamp в имени)
    alembic/versions/    # Миграции
    tests/
      conftest.py        # TestClient + in-memory SQLite + override auth
      test_models.py
      test_admin_routes.py
  bot/
    main.py           # Longpoll loop + command dispatch
    fsm.py            # FSM: idle, await_pin, await_garden, grow_step_N(_norm/_x2)
    keyboard.py       # VK keyboard builders
    scheduler.py      # Фоновый поток проверки истекших таймаутов
    handlers/
      commands.py     # start, help, status, garden, switch_to
      grow.py         # Обработка шагов (крестики + норма/штраф)
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
    src/
      pages/
        admin/
          UserDragonProgress.tsx  # Прогресс конкретного дракона игрока
          ...
  images/dragons/     # Яйца + взрослые драконы
  plans/              # Документация
  dev.ps1             # Локальный запуск (API :8001, frontend :5173, bot)
```

## База данных — ключевые таблицы

- **dragons** — определения драконов (имя, редкость, PIN, egg_type, семейство)
- **dragon_steps** — шаги дракона (magic_action, task_description, hint, keyword,
  timeout_hours, timeout_minutes, crosses_norm)
- **users** — vk_id, state (FSM), current_dragon_id, current_step
- **user_progress** — user_id + dragon_id + step_number: completed
- **user_dragons** — user_id + dragon_id: completed_at, next_step_available_at,
  timeout_notified
- **families** — семейства/союзы драконов (name, description, color, sort_order)
- **collection_grid** — визуальная сетка коллекции (family_id, cell_x, cell_y, dragon_id)
- **error_logs** — логи ошибок бота/API (source, error_type, message, traceback_text)
- **api_request_logs** — логи ошибочных запросов (method, path, status_code, client_ip, created_at MSK)
- **service_heartbeats** — пульс сервисов (service_name, last_seen, status)

## Таймауты (механика)

1. Поля `timeout_hours` / `timeout_minutes` на `DragonStep`
2. После завершения шага → `set_step_timeout()` → записывает
   `next_step_available_at` + сбрасывает `timeout_notified = False`
3. При входящем сообщении → `get_timeout_remaining()` → если > 0 — блокировка
4. Чекер (`scheduler.py`) каждые 30с: ищет `next_step_available_at <= now AND
   timeout_notified == False`, шлёт уведомление, ставит `timeout_notified = True`
5. При скипе/рестарте/резете/переключении админом → очистка полей
6. `complete_dragon()` → очищает `next_step_available_at`

## Выращивание — механика крестиков

1. Поле `crosses_norm` на `DragonStep` — норма крестиков (целое, ≥ 1, по умолчанию 1000)
2. Бот показывает шаг с кнопками «✅ Норма» и «⚠ Штраф (x2)»
3. Пользователь выбирает режим, затем отправляет «вышито [число]»
4. **Норма:** число ≥ crosses_norm → шаг выполнен
5. **Штраф (x2):** число ≥ crosses_norm × 2 → шаг выполнен
6. Число < нормы → сообщение «вышили меньше нормы», остаётся в ожидании
7. Нет «вышито» / нет числа — подсказка формата
8. После завершения всех шагов → `complete_dragon()` → поздравление

## Как запустить

```powershell
.\dev.ps1                       # Всё сразу
.\dev.ps1 -NoFrontend           # Без фронта
.\dev.ps1 -NoBackend            # Без API
.\dev.ps1 -NoBot                # Без бота
```

## Как запустить тесты

```powershell
# Python (API + bot)
api\venv\Scripts\python.exe -m pytest api/tests bot/tests -v --tb=short

# Frontend (vitest)
cd frontend; npx vitest run
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

После любого изменения Python-кода (API, бот, сервисы) необходимо посмотреть, добавилось ли что-то новое или удалилось, написать на это тест, запустить тесты и убедиться, что все проходят:

```powershell
api\venv\Scripts\python.exe -m pytest api/tests bot/tests -v --tb=short
```

Если тесты не проходят — исправить до завершения задачи.

**_63 теста (Python): 14 API + 4 модели + 17 grow_service + 8 grow_handler + 9 commands + 4 FSM + 7 scheduler._**

## Конвенции кода

- Python: никаких комментариев без запроса
- TypeScript: без комментариев, без лишних типов
- SQLAlchemy: Column, Integer, String, Boolean, Text, ForeignKey, default=
- Все импорты моделей внутри функций (lazy import) в bot/services/*.py
- Пустые строки между определениями классов/функций
- **Если что-то не понятно — задать вопрос пользователю прежде чем делать.** Не додумывать.

## FSM состояния

- `idle` — ожидание
- `await_pin` — ожидание PIN-кода
- `await_garden` — выбор дракона из списка
- `grow_step_N` — дракон активирован, на шаге N, задание ещё не начато
- `grow_step_N_norm` — ожидание текста «вышито [число]» в режиме Норма
- `grow_step_N_x2` — ожидание текста «вышито [число]» в режиме Штраф (x2)
- `is_growing(state)` — проверка, выращивает ли пользователь
- `is_waiting_text(state)` — проверка, ждёт ли бот сообщение с крестиками
- `state_mode(state)` — возвращает "norm" или "x2" из суффикса состояния
- `COMPLETED` — дракон выращен (завершён)

## Клавиатуры бота

- `idle_keyboard()` — Добавить дракона / Сменить / Помощь / Бестиарий
- `growing_keyboard()` — Статус / Сменить / Помощь / Бестиарий (без «Перейти»)
- `start_growing_keyboard()` — Перейти к выращиванию / Сменить / Помощь / Бестиарий (только при активации PIN)
- `waiting_keyboard()` — Статус / Сменить / Помощь / Бестиарий (без «Перейти», режим ожидания крестиков)
- `step_buttons_keyboard()` — Норма / Штраф(x2) / Статус / Сменить / Бестиарий
- `await_pin_keyboard()` — при вводе PIN
- `await_garden_keyboard()` — при выборе дракона
- Бестиарий всегда самая нижняя строка (кроме complete-дракона)

## Команды бота

- `start` / `выращивать` — приветствие (с таймаутом — без нормы, без таймаута — с кнопкой «Перейти»)
- `help` / `помощь` — справка
- `status` / `статус` — прогресс: при таймауте — без нормы и шага; при готовности — с кнопкой «Перейти к выращиванию»
- `garden` / `сменить` / `бестиарий` — список драконов (растущие — egg_type, завершённые — имя)
- `pin` / `дракона` — активация по PIN (показывает яйцо + кнопку «Перейти к выращиванию»)
- `grow` / `перейти к выращиванию` — показать описание шага + кнопки Норма/Штраф
- `norm` / `норма` — начать задание в режиме Норма
- `x2` / `штраф` — начать задание в режиме Штраф (x2)
- `switch_to` (payload: `{"cmd":"switch_to","dragon_id":N}`) — с нотификации
- `garden_cancel` / `0` / `не менять` — отмена переключения (с проверкой таймаута)

## Обработка шагов (grow.py)

1. Пользователь нажимает «🌱 Перейти к выращиванию» → описание шага + кнопки Норма/Штраф
2. Выбирает Норма или Штраф → бот ждёт сообщение «вышито [число]»
3. Извлекает число из текста (первое `\d+`), сравнивает с нормой
4. Недостаточно → «вышили меньше нормы (X)», ждёт повторно
5. Достаточно → шаг выполнен, переход к следующему
6. Следующий шаг: при таймауте → сообщение с оставшимся временем, без задания
7. Последний шаг → `complete_dragon()` → поздравление + картинка дракона
8. Во время таймаута бот отвечает на сообщения: «🥚 Яйцо «{тип}» выращивается. ⏳ Осталось: X ч. Y мин.»

## Нотификации (scheduler)

- Фоновый поток с `daemon=True`
- Каждые 30с проверяет истекшие таймауты
- Если юзер на этом драконе → присылает описание шага + кнопки Норма/Штраф
- Если на другом → присылает кнопку переключения

## Изображения драконов

- Сохраняются с timestamp в имени: `{dragon_id}_{timestamp}{ext}`
- Каждая замена генерирует новый URL → нет кеширования браузером
- Старый файл удаляется через `_cleanup_old`

## Админка — ключевые эндпоинты

- `GET /admin/users/{vk_id}` — детали игрока: dragons_collected (только завершённые), dragons_active (растущие), dragons_total
- `GET /admin/users/{vk_id}/dragons/{dragon_id}/steps` — шаги любого дракона игрока (не только активного)
- `POST /admin/users/{vk_id}/steps/{n}/toggle` — переключить статус шага (принимает `{dragon_id}` в body)
- `POST /admin/users/{vk_id}/skip-step` — пропустить шаг (принимает `{dragon_id}` в body)
- `POST /admin/users/{vk_id}/reset-dragon` — сбросить прогресс (принимает `{dragon_id}` в body)
- `DELETE /admin/users/{vk_id}/dragons/{dragon_id}` — удалить дракона у игрока
- `GET /admin/logs/api` — последние строки gunicorn error log
- `GET /admin/logs/api-requests` — логи ошибочных запросов (4xx/5xx)
- `POST /admin/logs/clear` — очистить error_logs + api_request_logs
- `GET /collection/{vk_id}/families` — возвращает color семейства
- `GET /collection/dragon/{dragon_id}` — возвращает family_color, next_step_available_at

## Мини-апп (коллекция)

- Цвет семейства применяется к: заголовку, описанию, вкладкам, имени дракона, типу яйца, прогресс-бару, проценту
- На странице DragonDetail: цвет семейства на заголовке, прогресс-баре
- Будущие шаги скрыты: только пройденные + текущий (при таймауте — только пройденные)
- Если completed_steps === 0 (не приступал) — прогресс-бар и шаги не показываются
- Ячейки: адаптивные 140–200px с горизонтальным скроллом
- Картинку дракона/яйца можно увеличить по клику (модально)
