# План: улучшение кода бота и API «Коллекция драконов»

Дата составления: 2026-07-07

## Границы (из ответов пользователя)

- ✅ Полный объём (все проблемы)
- ❌ Схему БД НЕ трогаем (timestamp String, типы, отношения остаются). N+1 и сравнение дат компенсируем кодом (joins/joinedload + единый хелпер дат). `busy_timeout` добавить МОЖНО — это PRAGMA, не миграция.
- ✅ Единый доменный слой (`api/services/`) — устраняет дубли `complete_dragon` и рассинхрон
- ✅ Расширить тесты

---

## ЭТАП 0 — Безопасность (P0, блокирующее)

**`api/db.py`** — добавить `PRAGMA busy_timeout=5000` и `PRAGMA synchronous=NORMAL` в `_set_sqlite_pragma` (стр. 19–20). Решает `database is locked` при 4 конкурирующих писателях (bot longpoll + scheduler + uvicorn + middleware).

**`api/config.py:7`** — `SECRET_KEY` без дефолта: при отсутствии в prod (`APP_ENV != "dev"`) поднимать `RuntimeError`. Оставить дефолт только для dev.

**`api/routes/auth.py:78-94`** — `/dev-login` дополнительно защищать: требовать непустой `DEV_LOGIN_SECRET` env и совпадения с query/body. Убрать риск случайного деплоя `.env.example` = полный захват админки.

**`api/routes/auth.py:62`** — токен из URL `?token=` → в `httpOnly` cookie (`set_access_cookie`) + `GET /api/auth/token` для SPA-извлечения через SameSite.

**`api/main.py:39-53`** — `serve_image`: добавить проверку `os.path.commonpath([filepath, IMAGES_DIR]) == IMAGES_DIR` (или `filepath.startswith(IMAGES_DIR + os.sep)`) перед отдачей. Закрывает path traversal.

**`api/routes/collection.py`** — IDOR: применить `verify_launch_params` из `auth.py` (уже существует, мёртвая). Каждый эндпоинт `/collection/{vk_id}` и `/dragon/{dragon_id}` принимает `verify` query (строка launch params) → валидация HMAC подписи VK. Опционально для dev-режима (`DEV_BYPASS_SIGNATURE=true`).

---

## ЭТАП 1 — Критические баги (P0)

**1.1 NameError в `toggle_user_step`** (`admin.py:547-674`). При `dragon_id` в body переменная `user` не создаётся, но используется на стр. 579, 595, 622–660. Исправить: получить `user` в начале функции всегда (`db.query(User).filter(User.vk_id==vk_id).first()`, 404 если нет). Заменить `user.current_dragon_id` → `dragon_id` в конструкторах `UserProgress` (579, 604) и cascade-запросах (595, 612, 623, 631, 636, 662) — там нужен разрешённый `dragon_id`, а не активный. На 579 сейчас `dragon_id=user.current_dragon_id` — семантическая ошибка.

**1.2 Зависание финального шага** (`grow.py:221-235`). При `step >= total` и `total_timeout_min > 0` бот НЕ вызывает `complete_dragon`, переводит в `grow_step_{total+1}`, ждёт scheduler. Исправить: даже при ненулевом таймауте вызывать `complete_dragon` + поздравление после установки таймаута, либо (если таймаут = «вылупление») явно документировать и не ставить фиктивный `current_step = total+1`. Решение через доменный слой (Этап 3) — единая функция `finish_or_schedule`.

**1.3 БАГ2 коллекции** (`collection.py:71-76`). Комментарий `# БАГ2` — статус growing вычисляется неверно. Починить: `status="growing"` если `dragon_id in growing_ids` (есть `UserDragon`) ИЛИ `dragon_id in progress_map`. Убрать `done` из тернарника на 94 (определён только в ветке `elif`) — вынести `completed_steps` в явный if/elif.

**1.4 `middleware.py:14-24`** — `db.close()` в `finally`, убрать `except Exception: pass` → логировать в `error_logs` с `source="api"`.

**1.5 `scheduler.py:228-229`** — `_send` ретраи (3 попытки с backoff). Критично: `timeout_notified=True` ставится даже если отправка упала → юзер навсегда теряет уведомление. Логика: ставить `timeout_notified=True` только после успешной отправки.

**1.6 `scheduler.py:95-102`** — заменить строковое сравнение дат на парсинг через единый хелпер `parse_dt(s)` → сравнение `datetime`. Хрупкость устраняется на уровне хелпера.

**1.7 `main.py:279`, `scheduler.py:71`** — `except Exception: pass` при записи `ErrorLog` → `except Exception as e: print(...)` (минимум в stderr), не молчать.

**1.8 `grow.py:144,149,...`** — `handle_grow_message` всегда возвращает True. Либо убрать return, либо сделать осмысленным (False = «не обработано, отдать главной диспетчеризации»). Убрать мёртвый контракт.

**1.9 `pin.py:28`** — `isalnum()` → `re.fullmatch(r"[A-Z0-9]{5}", code)` для соответствия тексту «A-Z и цифры».

---

## ЭТАП 2 — Создание доменного слоя (`api/services/`)

Цель: единый источник истины для прогресса/уведомлений/файлов. Бот и API вызывают одни функции.

**`api/services/progress_service.py`** (НОВЫЙ):
- `complete_step(db, vk_id, dragon_id, step_number, photo_before, photo_after)` — перенос из `bot/services/grow_service.py:72` + cascade-логика из `admin.py:586-619`.
- `complete_dragon(db, vk_id, dragon_id)` — единая функция: ставит `UserDragon.completed_at`, сбрасывает `User.state=IDLE/current_dragon_id=None/current_step=0`, чистит таймаут. Возвращает `(dragon, family_name)` для форматирования. **Все 5 мест** (`grow.py:237-242`, `scheduler.py:135-142`, `admin.py:636-641`, `admin.py:774-782`, `commands.py:139-140`) вызывают только её.
- `skip_step(db, vk_id, dragon_id, step_number)` — перенос из `admin.py:730-790`.
- `reset_dragon(db, vk_id, dragon_id)` — перенос из `admin.py:793-827`.
- `restart_dragon(db, vk_id, dragon_id)` — перенос из `admin.py:830-863`.
- `toggle_step(db, vk_id, dragon_id, step_number)` — перенос из `admin.py:547-674` с исправленным NameError.
- `set_step_timeout`, `get_timeout_remaining`, `clear_step_timeout` — перенос из `grow_service.py`, переиспользуются ботом и scheduler.
- Все операции записи прогресса оборачивать в `with db.begin()` (BEGIN IMMEDIATE в SQLite) для read-modify-write атомарности — закрывает race между админом и ботом.

**`api/services/storage.py`** (НОВЫЙ) — единый код сохранения/чистки файлов:
- `save_upload(file, kind: Literal["dragon","family"], dragon_or_family_id)` — с UUID-суффиксом (`uuid4().hex[:8]`) вместо `int(time())` → коллизии устранены.
- `cleanup_old(old_path)` — без мёртвого параметра `prefix`.
- `validate_image(file)` — whitelist MIME (`image/png`, `image/jpeg`, `image/webp`) + размер ≤ 10 МБ (анти-DoS через `read()` чанками).
- `images_dir()` — единый резолвер от корня репо (устраняет 6 разных `os.path.join(__file__, "..", ..)`).

**`api/services/notification_service.py`** (НОВЫЙ) — единый VK-sender:
- `get_vk_api()` — переиспользуемый singleton `VkApi` (вместо создания нового на каждый вызов в `admin.py:395,685,707`).
- `notify_user(vk_id, message, attachment="", keyboard=None)` — с ретраями.
- `upload_image(vk, filepath, peer_id, log_error)` — единая (устраняет дубль `main.upload_image` ↔ `scheduler._upload_image`).
- `_notify_user`/`_upload_vk_image`/`_resolve_vk_names` из `admin.py` переходят сюда.

**`api/services/format.py`** (НОВЫЙ) — общие хелперы:
- `format_remaining(remaining: timedelta) -> str` → `"X ч. Y мин."`. Устраняет **10 копий** (5 в commands.py, 4 в grow.py, 1 в main.py).
- `format_step(step_def, n, total)` → перенос из `grow.py:16` и `admin.py:_format_step_text`. Устраняет дубль.
- `parse_dt(s)`, `now_msk_iso()` — единый парсинг/форматирование timestamp-строк (схема не меняется, но хрупкость убирается в одно место).
- `MINIAPP_URL` константа (вместо 4 хардкодов в commands.py:387, grow.py:260, scheduler.py:163,212).

**`api/services/security.py`** (НОВЫЙ) — обёртки вокруг `auth.py`:
- `require_launch_params(verify: str, vk_id: int)` — FastAPI-зависимость для collection-роутов.

---

## ЭТАП 3 — Рефакторинг бота и API на доменный слой

**`bot/services/grow_service.py`** — оставить тонкие обёртки или удалить, заменив импорты на `api/services/progress_service`. `complete_dragon`/`complete_step` становятся re-export. Убрать мёртвый `clear_step_timeout` (или подключить к `complete_dragon`/reset).

**`bot/handlers/grow.py`**:
- `_handle_crosses_check` (157 строк) разбить на `parse_crosses(text)`, `validate_mode(state)`, `record_step(...)`, `format_completion(dragon, family)` — SRP.
- Блок 221–235 (зависание финального шага) → `progress_service.finish_or_schedule(...)`.
- Блоки 221–274 и 275–307 → параметризованный `advance_step(db, vk_id, dragon_id, ...)`.
- `handle_norm_command`/`handle_x2_command` → единый `start_mode(user, dragon, mode)` с параметром suffix/multiplier.
- Убрать `log_err` замыкания (5 копий) → `notification_service.upload_image(log_error=...)`.
- Убрать inline-клавиатуру завершения (253–262) → `idle_keyboard()` или `completed_keyboard()` в `keyboard.py`.

**`bot/handlers/commands.py`**:
- `switch_dragon` (204) и `handle_switch_to` (304) → общая `_do_switch(db, vk_id, dragon_id, send_message, ...)`.
- `_completed_keyboard` (377) → в `keyboard.py`, единый билдер.
- N+1 в `handle_garden` (133,142) → один JOIN-запрос `UserDragon + Dragon` + агрегация `UserProgress.count()` через `group_by`/subquery.
- Operator-precedence баг `dragon.egg_type or "яйцо" if dragon else "?"` (189, 221) → `(dragon.egg_type or "яйцо") if dragon else "?"`. То же в `main.py:35`.
- Опечатка «яйц драконов» (121) → «яиц».

**`bot/handlers/pin.py`** — упростить вложенность `handle_pin_entry`, использовать `progress_service` для проверки активации, единый `log_err`.

**`bot/scheduler.py`**:
- `_upload_image`, `_send`, `_switch_garden_keyboard` → удалить, использовать `notification_service`.
- `_check_expired` → использует `progress_service.get_timeout_remaining` и `complete_dragon`.
- Вынести локальные импорты наверх (конвенция AGENTS.md про lazy-import относится к `bot/services/*.py`, scheduler — точка входа).

**`bot/main.py`**:
- `_handle_growing_chat` (31–62) → в `handlers/commands.py` (бизнес-логика не в точке входа).
- Дублирующий импорт `from datetime import datetime` (25, 28) → один.
- Неиспользуемые импорты `step_from_state`, `grow_state` (18) → убрать.
- `extract_cmd` (88–97) — substring-матчинг (`"дракона" in t`) → priority-список `(regex, cmd)` с ранним возвратом. Убирает ложные срабатывания («нужна помощь с драконом» → /help).
- Бесконечный `sleep(60)` без токена (108–113) → лог + clean exit (код != 0).

**`api/routes/admin.py`** (944 строки → ~400):
- `toggle_user_step`, `skip_step`, `reset_dragon`, `restart_dragon` → тонкие обёртки над `progress_service` (по 5–15 строк каждая).
- Тройной дубль сохранения шагов (64–88, 112–150, 182–216) → `progress_service.save_steps(db, dragon_id, steps_payload)`.
- `list_users`, `get_user_detail`, `get_user_steps`, `get_user_dragon_steps`, `list_families` → JOIN/агрегация (joinedload или `func.count().label(...)`) вместо N+1.
- `_format_step_text`, `_notify_user`, `_upload_vk_image`, `_resolve_vk_names` → удалить (в `services`).
- `_notify_user` вызывался ДО `db.commit()` (657–671 vs 673) → коммитить первой строкой ответа, уведомлять второй.
- `list_api_logs` (895–908) — чтение файла с `seek`/iterator (реверс по строкам с лимитом), не весь файл в память.
- `/health` (927) — `datetime.now()` без tz → `now_msk()`.

**`api/middleware.py`** — сессия в `finally`, `except Exception` → лог в `error_logs` (`source="api"`).

---

## ЭТАП 4 — Конфигурация и двух баз (P1)

**`api/config.py:10`** — `DATABASE_URL` без относительного дефолта. Абсолютный путь от корня репо через `Path(__file__).resolve().parents[1] / "api" / "dragons.db"`. Устраняет расхождение `./dragons.db` ↔ `api/dragons.db` (в репо лежат две базы).

**Удалить `dragons.db` в корне репо** (53 КБ, реликт) — после подтверждения, что это не основная база. `api/dragons.db` (106 КБ, актуальная) — оставить.

**`api/main.py:10`** — убрать `init_db()` (create_all в обход Alembic). Схему создаёт только `alembic upgrade head`. `RESET_DB` env-флаг → удалить или вынести в CLI-скрипт `api/scripts/reset_db.py` с подтверждением.

**Удалить пустой реликт `api/images/dragons/`**.

**`api/db.py:30-35`** — `init_db`/`reset_database` оставить как dev-утилиту, не вызывать на старте.

---

## ЭТАП 5 — Мёртвый код и чистка

- `bot/fsm.py:7` `COMPLETED` — либо присваивать в `complete_dragon`, либо удалить из проверок `is_growing`. Рекомендую удалить (мёртвое).
- `bot/fsm.py` `GROW_STEP` импорт в `commands.py:6`, `step_from_state` в `main.py:18` — убрать неиспользуемые.
- `bot/keyboard.py` — объединить `growing_keyboard`/`waiting_keyboard`/`idle_keyboard` через единый `_base_keyboard(extra_rows=[])`.
- `bot/keyboard.py:23` `row()` — убрать эвристику цвета по подстроке label → явный параметр `color=` в вызывающем коде.
- `bot/services/pin_service.py:14` — `activate_pin(db, vk_id, dragon_id: int)` вместо объекта.
- `bot/services/user_service.py` `get_or_create_user` — обернуть в транзакцию, ловить `IntegrityError` на PK-конфликте → re-query (закрывает race двух одновременных сообщений).
- `collection.py:140` `from models import DragonStep` внутри функции → наверх.
- `services/__init__.py` `# TODO` → удалить.

---

## ЭТАП 6 — Тесты (расширение покрытия)

AGENTS.md требует прогон `api\venv\Scripts\python.exe -m pytest api/tests bot/tests -v` (сейчас 63 теста). Целевое — ~90+ после расширения.

**Новые тесты на исправленные баги (регресс):**
- `test_toggle_step_with_dragon_id` — воспроизводит NameError (`admin.py:547`), фиксирует фикс.
- `test_final_step_completes_dragon` — `step == total` + таймаут → `complete_dragon` вызывается, не `grow_step_{total+1}`.
- `test_collection_growing_status` — БАГ2 (`collection.py:71`).
- `test_serve_image_path_traversal` — `/api/static/images/../../etc/passwd` → 404.
- `test_send_retry_on_vk_error` — `scheduler._send` ретраит, `timeout_notified` только при успехе.
- `test_secret_key_required_in_prod` — `APP_ENV=production` без `SECRET_KEY` → raise.

**Новые тесты на доменный слой:**
- `test_progress_service_complete_dragon` — сброс user, чистка таймаута, idempotent.
- `test_progress_service_toggle_cascade` — mark N complete → все <N complete; unmark N → все >N incomplete.
- `test_progress_service_skip/reset/restart`.
- `test_progress_service_transaction_atomicity` — падение между step и dragon-complete → откат.

**Тесты безопасности:**
- `test_collection_requires_signature` — без `verify` → 401; с неверной подписью → 401; с верной → 200.
- `test_dev_login_requires_secret` — без `DEV_LOGIN_SECRET` → 403.

**Тесты сервисов:**
- `test_storage_save_upload_collision` — два аплоада в одну секунду → разные имена.
- `test_storage_validate_image_mime` — `.svg`/`.html` → reject; большой файл → reject.
- `test_pin_service_validate_format` — кириллица/юникод → reject.
- `test_user_service_get_or_create_race` — два потока → одна строка.
- `test_format_remaining / format_step` — все ветки.

**Покрытие bot (ранее ноль):**
- `test_extract_cmd_priority` — «помощь с драконом» → /help, не /pin.
- `test_handle_norm_x2_unified`.
- `test_pin_handler`.
- `test_keyboard_payloads` — проверка `{"cmd": "norm"}` и цветов.

Конвенция из AGENTS.md: ленивые импорты моделей только в `bot/services/*.py`, пустые строки между определениями, без комментариев без запроса, SQLAlchemy `Column/Integer/...`.

---

## Последовательность выполнения (от наименее рискованного)

1. **Этап 0** (безопасность) — точечные правки, прогон тестов.
2. **Этап 1** (баги P0) — точечные правки + регресс-тесты на каждый.
3. **Этап 2** (доменный слой) — создание `services/`, ничего не ломает (старый код ещё работает).
4. **Этап 3** (рефакторинг на слой) — по одному файлу: `grow_service` → `scheduler` → `handlers/*` → `admin.py`. После каждого — прогон тестов.
5. **Этап 4** (конфиг/БД-пути) — после стабилизации.
6. **Этап 5** (чистка мёртвого кода).
7. **Этап 6** (тесты) — накатываются параллельно с каждым этапом (TDD на багах).

После каждого этапа: `api\venv\Scripts\python.exe -m pytest api/tests bot/tests -v --tb=short`. На траверсал/сигнатуры — отдельные тесты.

---

## Ожидаемый результат

- Устранены 9 критических багов (NameError, зависание шага, БАГ2, traversal, IDOR, SECRET_KEY, dev-login, send-retry, silent-except).
- Дублирование устранено: `complete_dragon` (5→1), `format_remaining` (10→1), `upload_image` (2→1), `log_err` (5→1), клавиатуры, `format_step` (2→1), `MINIAPP_URL` (5→1).
- Единый доменный слой → бот и API разделяют ответственность, прогресс/завершение атомарны (`BEGIN IMMEDIATE`).
- Race `database is locked` закрыт `busy_timeout`.
- Покрытие тестов ~90+ (с 63), включая безопасность и сервисы.
- `admin.py` 944 → ~400 строк, `grow.py` `_handle_crosses_check` 157 → разбит на SRP-функции.

Схема БД НЕ меняется (по вашему решению) — риски сравнения дат строками компенсированы единым хелпером `parse_dt`/`now_msk_iso`, N+1 — JOIN-запросами в коде.
