# 🐲 Бестиарий драконьих легенд — AGENTS.md

## Проект

VK Mini App + Bot для выращивания драконов через вышивку. Пользователь
активирует дракона по PIN-коду, проходит N шагов — отправляет текстовое
сообщение с количеством вышитых крестиков (например, «вышито 1500»),
в конце получает карточку дракона в коллекции.

## graphify
This project has a graphify knowledge graph at graphify-out/.

### Rules:

- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run graphify update . to keep the graph current (AST-only, no API cost)

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

**_179 тестов (Python)._**

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

### Расширение (фазы 1–7)

- `legend_N` / `legend_N_norm` / `legend_N_x2` — прохождение отрывка легенды N (rarity 3); `is_legend`, `is_legend_waiting`, `legend_fragment_from_state`
- `epic_egg_N` / `epic_egg_N_norm` / `epic_egg_N_x2` — рост яйца эпического; `is_epic_egg`, `is_epic_egg_waiting`, `epic_egg_step_from_state`
- `await_epic_name` — ожидание имени эпического дракона после вылупления
- `epic_care_<stage_id>` / `..._norm` / `..._x2` — уход за эпическим на стадии; `is_epic_care`, `is_epic_care_waiting`, `epic_care_state(stage_id, suffix="")`
- `await_epic_restart` — выбор после финала эпического (такого же / случайного)
- `await_epics` — выбор эпического дракона из списка вылупленных (переключение активного `epic_dragon_id`)
- Магазин работает без отдельного FSM-состояния (по payload-командам `shop`/`buy`)

## Клавиатуры бота

- `idle_keyboard()` — Добавить дракона / Сменить / Помощь / Бестиарий
- `growing_keyboard()` — Статус / Сменить / Помощь / Бестиарий (без «Перейти»)
- `start_growing_keyboard()` — Перейти к выращиванию / Сменить / Помощь / Бестиарий (только при активации PIN)
- `waiting_keyboard()` — Статус / Сменить / Помощь / Бестиарий (без «Перейти», режим ожидания крестиков)
- `step_buttons_keyboard()` — Норма / Штраф(x2) / Статус / Сменить / Бестиарий
- `await_pin_keyboard()` — при вводе PIN
- `await_garden_keyboard()` — при выборе дракона (без кнопки «Сменить яйцо»)
- `shop_keyboard(items, page, total_pages)` — товары стадии + пагинация + Сменить яйцо (магазин)
- `legend_buttons_keyboard()` — Норма / Штраф(x2) / Сменить яйцо / Бестиарий (легенда)
- `epic_egg_buttons_keyboard()` — Норма / Штраф(x2) / Сменить яйцо / Бестиарий (яйцо эпического)
- `epic_care_keyboard()` — Норма / Штраф(x2) / Магазин / Сменить яйцо / Бестиарий (уход)
- `keyboard_with_legends(kb_json)` — вставляет кнопку «🐲 Легендарные драконы» если у юзера есть выращенные легендарные
- `keyboard_with_epics(kb_json)` — вставляет кнопку «🐉 Эпические драконы» если у юзера есть вылупленные эпические (не показывается в состояниях `await_epics`, `await_epic_name`, `epic_egg_*`, `epic_care_*`)
- Кнопка «🔄🥚 Сменить яйцо дракона» (garden) присутствует на всех клавиатурах, КРОМЕ `await_garden_keyboard` (не показывается внутри самого раздела смены)
- `idle_keyboard()`/`growing_keyboard()` содержат кнопку «🛒 Магазин»
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
- `legends` / `легендарные` — список легендарных драконов, выбор → чтение легенды
- `balance` / `копилка` / `баланс` — показать копилку крестиков
- `shop` / `магазин` / `лавка` — магазин стадии; `buy` (payload `{"cmd":"buy","item_id":N}`) — покупка
- `epic` / `эпический` / `пещера` — уход за эпическим (яйцо/имя/стадии)
- `epics` / `эпические драконы` — список вылупленных эпических, выбор → переключение активного и переход к его заданиям; `0` — отмена
- `legend` (payload `{"cmd":"legend","dragon_id":N}`) — рассказать легенду легендарного
- `epic_restart` (payload `{"cmd":"epic_restart","mode":"same"|"random"}`) — после финала эпического

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
- `DELETE /admin/users/{vk_id}` — удалить игрока со всем прогрессом (драконы, прогресс, легенды, сокровища, инвентарь, подозрительные, эпик care/moodlets); логи не трогаются
- `GET /admin/logs/api` — последние строки gunicorn error log
- `GET /admin/logs/api-requests` — логи ошибочных запросов (4xx/5xx)
- `POST /admin/logs/clear` — очистить error_logs + api_request_logs
- `GET /admin/suspicious/detailed` — подозрительные отчёты для страницы (vk_id, ФИО, ссылка на чат сообщества, текст сообщения, заявлено/норма, дата) + total
- `DELETE /admin/suspicious/{report_id}` — удалить подозрительный отчёт
- `GET /admin/stats` — включает suspicious_total (для плашки на дашборде)
- `GET /collection/{vk_id}/families` — возвращает color семейства
- `GET /collection/dragon/{dragon_id}` — возвращает family_color, next_step_available_at

## Мини-апп (коллекция)

- Цвет семейства применяется к: заголовку, описанию, вкладкам, имени дракона, типу яйца, прогресс-бару, проценту
- На странице DragonDetail: цвет семейства на заголовке, прогресс-баре
- Будущие шаги скрыты: только пройденные + текущий (при таймауте — только пройденные)
- Если completed_steps === 0 (не приступал) — прогресс-бар и шаги не показываются
- Ячейки: адаптивные 140–200px с горизонтальным скроллом
- Картинку дракона/яйца можно увеличить по клику (модально)
