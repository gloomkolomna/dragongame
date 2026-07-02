# План: Admin Panel — Коллекция драконов

**Статус:** ✅ Базовая админка готова. Семейства, per-family сетки, цветовая индикация — реализованы сверх плана.

---

## Статус по шагам

| Шаг | Статус | Что сделано |
|---|---|---|
| 1. Auth | ✅ Готово | VK OAuth PKCE + JWT + whitelist + dev-login |
| 1.5. Alembic | ✅ Готово | env.py, migrations, WAL, foreign_keys ON |
| 2. Dashboard | ✅ Готово | GET /stats, Dashboard.tsx, AdminLayout.tsx |
| 3. Dragons CRUD | ✅ Готово | CRUD, multipart upload, image cleanup |
| 4. Steps Editor | ✅ Готово | CRUD, reorder, steps_count sync |
| 5. Grid Editor | ✅ Готово | Per-family, resize, drag & drop, modal preview |
| 6. PIN Manager | ✅ Готово (изменено) | 4-значные per-dragon, сводная таблица |
| 7. Users | ✅ Готово | Список, деталка, skip step, reset dragon |
| 8. Deploy | ✅ Готово | deploy.sh, backup.sh, systemd, nginx config |

---

## Что добавлено сверх плана

### Семейства / Союзы (`families`)
- Таблица `families` (id, name, description, sort_order, **color**)
- Страницы `/admin/families`, `/admin/families/new`, `/admin/families/:id/edit`
- CRUD через JSON, удаление с подтверждением
- **Палитра цветов:** 35 пресетов + нативный color picker + ручной HEX
- Цветной индикатор в таблице драконов и списке семейств
- Навигация: клик по цвету → переход к сетке семейства

### Per-family сетки
- `collection_grid.family_id` — у каждого семейства своя сетка
- GridEditor: выбор семейства сверху, создание/изменение размера per-family
- Ячейки: имя (жирный 16px, кликабельно), редкость, яйцо (cover), дракон (contain, 250px)
- Миниатюры яйца и дракона в панели неразмещённых
- Модальное окно: клик по яйцу/дракону — полноэкранный просмотр

### Улучшения таблицы драконов
- Убран столбец ID
- Сортировка по всем колонкам (↑/↓)
- Поколоночные фильтры (имя, редкость, яйцо, шаги, семейство, PIN)
- Счётчик `N из M`
- `family_id` обязательно при создании (фронт + бэк)

### Collection API для Mini App
- `GET /collection/{vk_id}?family_id=N` — сетка с состояниями ячеек
- `GET /collection/{vk_id}/families` — сводка по семействам (total/collected)

### Инструменты разработчика
- `dev.ps1` — одной командой запуск бэка (:8001) + фронта (:5173), Ctrl+C убивает оба процесса
- `RESET_DB=true` в `.env` — пересоздаёт все таблицы при старте

---

## Что осталось (будущие фазы)

| Задача | Приоритет |
|---|---|
| VK Bot (longpoll FSM) | Высокий |
| Mini App: вкладки семейств, яйцо+прогресс | Высокий |
| Привязка PIN к игроку | Средний |
| Multi-dragon выращивание (`/garden`) | Низкий |

---

## Детальный план (исходный, с отметками)

### Шаг 1 — Auth ✅
- [x] `api/config.py` — VK_*, SECRET_KEY, DATABASE_URL, APP_ENV, DEV_LOGIN_ENABLED
- [x] `api/models.py` — SQLAlchemy модели всех таблиц
- [x] `api/auth.py` — PKCE, JWT, whitelist, get_current_admin
- [x] `api/routes/auth.py` — vk-login, vk-callback, me, config, dev-login
- [x] `frontend` — Login.tsx, AuthContext.tsx, ProtectedRoute.tsx

### Шаг 1.5 — Alembic ✅
- [x] `api/alembic.ini` и `api/alembic/env.py`
- [x] Начальная миграция + миграции изменений (keyword, pin_per_dragon, families, color)
- [x] `python -m alembic upgrade head` — применяется

### Шаг 2 — Dashboard ✅
- [x] GET /api/admin/stats
- [x] Dashboard.tsx + AdminLayout.tsx с сайдбаром
- [x] 6 карточек-счётчиков с анимацией (Framer Motion)

### Шаг 3 — Dragons CRUD ✅
- [x] `api/services/dragon_service.py` — CRUD + загрузка изображений
- [x] `api/routes/admin.py` — dragons CRUD эндпоинты (multipart)
- [x] `frontend` — DragonsList.tsx, DragonForm.tsx
- [x] **Сверх плана:** сортировка, фильтры, цвет семейства, убран ID

### Шаг 4 — Steps Editor ✅
- [x] `api/routes/admin.py` — steps эндпоинты
- [x] `frontend` — StepsEditor.tsx
- [x] Сохранение через ручной JSON (Pydantic model silently failed)
- [x] Новые шаги с `id:0` создаются, существующие обновляются
- [x] Re-number при удалении

### Шаг 5 — Grid Editor ✅ (переработан)
- [x] `api/routes/admin.py` — grid эндпоинты
- [x] `frontend` — GridEditor.tsx
- [x] **Сверх плана:** per-family сетки, выбор семейства, модальный просмотр изображений
- [x] **Сверх плана:** миниатюры яйца и дракона в ячейках
- [x] **Сверх плана:** resize с проверкой занятых ячеек

### Шаг 6 — PIN Manager ✅ (изменена концепция)
- ~~Генерация пачек PIN~~ → Каждый дракон имеет один 4-значный код
- [x] PIN генерируется при создании дракона
- [x] `frontend` — PinManager.tsx (сводная таблица)
- ~~Экспорт CSV~~ (упрощено — не нужно при per-dragon формате)

### Шаг 7 — Users ✅
- [x] `api/routes/admin.py` — users эндпоинты
- [x] `frontend` — UsersList.tsx
- [x] Деталка игрока: коллекция, скип шага, сброс

### Шаг 8 — Бэкап и деплой ✅
- [x] `deploy/backup.sh` — ежедневный бэкап + ротация
- [x] `deploy/deploy.sh` — 7-этапный деплой с откатом
- [x] `deploy/dragons-api.service` — systemd gunicorn :8001
- [x] `deploy/dragons-bot.service` — systemd python bot
- [x] `deployment-guide.md` — полная инструкция (nginx, systemd, локальная разработка)
