# План: VK Bot + Mini App — Коллекция драконов (вышивка)

## 1. Цель и границы

Гибридная система: VK-бот (выращивание дракона по шагам) + VK Mini App
(отображение коллекции) + веб-админка (управление).

**Физический продукт:**
- Пластиковое яйцо (разных видов/цветов) — покупается игроком
- Внутри:
  - **PIN-код** на отдельном вкладыше (открыт сразу)
  - **Наклейка с изображением дракона — под скретч-слоем** (как на лотерейных
    билетах). Игрок сам решает, стирать ли её сразу или сохранить тайну до финала
    в боте. Так совмещаются «наклейка для буклета» и «тайна до раскрытия» —
    на честность игрока.
- Буклет для вклеивания наклеек (физическая коллекция)
- Игрок до последнего не знает, какого дракона выращивает (если не стёр скретч-слой)

**Что входит:**
- Регистрация игрока по PIN-коду (с наклейки внутри яйца)
- FSM-логика выращивания (2–5 шагов, зависит от редкости)
- Приём фотоотчёта: 2 фото (ДО/ПОСЛЕ вышивки) + слово `"вышито"` в одном сообщении
- Кодовая фраза единая для всех шагов — `"вышито"`
- VK Mini App (React + VKUI): сетка коллекции с процентом прогресса,
  детальная страница каждого дракона. До завершения — дракон скрыт (силуэт)
- Админ-панель (React, авторизация по VK ID):
  - CRUD драконов (включая тип яйца)
  - Расстановка драконов по ячейкам сетки (drag & drop)
  - Генерация и экспорт PIN-кодов
  - Просмотр прогресса игроков
- Брейншторм 100 драконов → заказчик отбирает 50

**Что НЕ входит:**
- Автоматический анализ фото (проверяется только наличие 2 фото + текст `"вышито"`)
- Монетизация / донат
- Производство физических яиц/буклетов (только цифровая часть)

## 2. Стек

| Компонент | Технология |
|---|---|
| VK Bot | Python 3.10+, `vk_api` (longpoll) |
| API | FastAPI (общая БД с ботом) |
| Mini App | React 18 + VKUI + VK Bridge, Node.js 16.x |
| Admin Panel | React (та же сборка, роут `/admin`) |
| DB | SQLite3 — WAL-режим (ботам и API) |
| Изображения | локально `images/dragons/`, отдача через FastAPI `/static/` |
| VK Bridge | `https://dev.vk.com/ru/mini-apps/vk-bridge` |
| Деплой | Linux-сервер (Ubuntu), systemd (бот) + gunicorn (FastAPI) + nginx (фронт) |

## 3. Модель данных (SQLite)

### Таблица `dragons`
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | название (скрыто от игрока до финала) |
| egg_type | TEXT | тип яйца (цвет, описание — "жёлтое с искрами") |
| rarity | INTEGER | 1–4 (обычный, редкий, эпический, легендарный) |
| steps_count | INTEGER | 2–5, **редактируемое**; дефолт по редкости (1→2, 2→3, 3→4, 4→5), админ может переопределить вручную |
| image_path | TEXT | путь к локальному файлу |
| silhouette_path | TEXT | силуэт (для отображения до раскрытия) |
| description | TEXT | текстовка финальной карточки |
| is_active | BOOL | флаг доступности |

### Таблица `dragon_steps`
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| dragon_id | INTEGER FK | |
| step_number | INTEGER | 1..steps_count |
| task_description | TEXT | задание по вышивке |
| magic_action | TEXT | магическое действие ("положить яйцо на лёд") |
| hint | TEXT | подсказка |

**Кодовая фраза:** единое слово `"вышито"` (любой регистр) — не хранится в БД.

Формат задания: «*Магическое действие* для выращивания дракона. **Вышей** NNN крестиков на сюжете с ...»

Пример:
> Положи яйцо на снег или лёд. Для этого вышей 300 крестиков на сюжете белыми или голубыми нитками.

### Таблица `collection_grid`
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| cell_x | INTEGER | колонка в сетке (0..N) |
| cell_y | INTEGER | строка в сетке (0..M) |
| dragon_id | INTEGER UNIQUE FK → dragons.id | NULL если ячейка пустая |

Сетка общая для всех игроков. Админ создаёт ячейки через админку
(кнопка «создать сетку N×M»). `dragon_id = NULL` для пустых ячеек.
Mini App при рендере берёт `MAX(cell_x)+1` и `MAX(cell_y)+1` как размеры
сетки. Ячейки без дракона рендерятся как пустые (серый контур).

**Динамика сетки:**
- Добавление нового дракона → админ перетаскивает в свободную ячейку
- Расширение сетки → админ добавляет столбцы/строки → новые пустые ячейки
- Никакой хардкод — Mini App рендерит всё из БД

### Таблица `pins`
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| code | TEXT UNIQUE | PIN (X7F9-K3M2) |
| dragon_id | INTEGER FK → dragons.id | |
| rarity | INTEGER | |
| status | TEXT | 'active', 'printed', 'used' |
| created_at | TEXT | |
| used_by | INTEGER FK → users.vk_id | |
| used_at | TEXT | |

### Таблица `users`
| Колонка | Тип | Описание |
|---|---|---|
| vk_id | INTEGER PK | |
| state | TEXT | FSM-состояние |
| current_dragon_id | INTEGER FK | дракон в процессе (скрыт от игрока) |
| current_step | INTEGER | |
| state_data | TEXT | JSON |
| registered_at | TEXT | |

### Таблица `user_progress`
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | |
| dragon_id | INTEGER FK | |
| step_number | INTEGER | |
| photo_before_id | TEXT | VK attachment |
| photo_after_id | TEXT | VK attachment |
| completed | BOOL | |
| completed_at | TEXT | |

### Таблица `user_dragons` (выращенные)
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | |
| dragon_id | INTEGER FK | |
| completed_at | TEXT | |
| UNIQUE(user_id, dragon_id) | | |

### Индексы
- `pins(code)` UNIQUE
- `user_progress(user_id, dragon_id, step_number)` UNIQUE
- `collection_grid(cell_x, cell_y)` UNIQUE
- `collection_grid(dragon_id)` UNIQUE

## 4. Архитектура

### Структура проекта
```
project/
├── bot/                    # VK Bot (longpoll)
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── fsm.py
│   ├── handlers/
│   │   ├── start.py
│   │   ├── pin.py
│   │   ├── grow.py          # приём фото + "вышито"
│   │   ├── collection.py    # ссылка на Mini App
│   │   └── admin.py
│   ├── services/
│   │   ├── pin_service.py
│   │   ├── step_service.py  # валидация: 2 фото + "вышито"
│   │   └── image_service.py # загрузка в VK
│   └── utils.py
├── api/                    # FastAPI
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── routes/
│   │   ├── collection.py
│   │   ├── dragon.py
│   │   ├── admin.py
│   │   └── auth.py
│   └── middleware.py
├── frontend/               # React + VKUI (Mini App + Admin)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Collection.tsx
│   │   │   ├── DragonDetail.tsx
│   │   │   ├── Login.tsx
│   │   │   └── Admin/
│   │   │       ├── Dashboard.tsx
│   │   │       ├── Dragons.tsx
│   │   │       ├── GridEditor.tsx
│   │   │       ├── Pins.tsx
│   │   │       └── Users.tsx
│   │   ├── api/client.ts
│   │   └── components/
│   │       ├── DragonCell.tsx   # силуэт/прогресс/раскрыт
│   │       └── ProgressBar.tsx
│   ├── public/
│   └── package.json
├── images/
│   └── dragons/            # {id}.png + {id}_silhouette.png
├── content/
│   └── dragons-list.md     # брейншторм 100 драконов
└── deploy/
    ├── bot.service
    ├── api.service
    └── nginx.conf
```

### Коммуникация компонентов

```
VK (чат) ←→ Bot (Python, longpoll)
                 │
                 ▼  общая БД SQLite (WAL)
                 │
VK Mini App ←→ FastAPI (REST) ←→ React SPA
    │             ▲                │
    │             │                └──── /admin (VK OAuth)
    └──── подписанные launch-params VK (vk_user_id + sign)
          бэкенд верифицирует sign секретом приложения
```

**Идентификация игрока в Mini App — критично:**
`vk_user_id` берётся НЕ из URL/query, а из **подписанных launch-params VK**
(параметры `vk_user_id` и `sign`, которые VK прокидывает при открытии Mini App).
FastAPI верифицирует подпись `sign` секретом приложения (алгоритм VK:
`sign = base64(HMAC-SHA256(query_string_without_sign, secret_key))`).
Дополнительно фронт дублирует через `VKWebAppGetUserInfo` (VK Bridge).
Бэкенд **не доверяет** `vk_id` из query/пути — только верифицированной подписи.

## 5. VK Mini App — коллекция пользователя

### UX: дракон скрыт до завершения

- **Не начат / в процессе**: ячейка показывает силуэт (silhouette) + % прогресса.
  Название дракона и изображение НЕ отображаются.
- **Выращен**: полное изображение + имя + редкость + описание.

Детальная страница (`/dragon/{id}`) также следует этому правилу:
- в процессе — только шаги без имени дракона
- выращен — полная карточка

### Страницы

**1. Сетка коллекции (`/`)**
- VK Bridge + подписанные launch-params → верифицированный `vk_user_id` →
  `GET /api/collection` (vk_id определяется бэкендом из подписи, не из URL)
- Ячейки по `collection_grid`:

| Статус | Вид | Кликабельно |
|---|---|---|
| Не начат | серый силуэт "?" | нет |
| В процессе | силуэт + % (затемнение убывает) | да → деталка |
| Выращен | полное изображение + галочка | да → полная карточка |

**2. Детальная (`/dragon/{id}`)**
- `GET /api/dragon/{id}` (vk_id определяется бэкендом из подписи launch-params)
- В процессе: «Яйцо {egg_type}» + список шагов (✅ / → / 📋)
- Выращен: название, изображение, редкость, описание, дата

**3. Ссылка из бота**: `https://vk.com/app{app_id}`

### API эндпоинты

> vk_id игрока определяется бэкендом из подписанных launch-params VK
> (параметр `sign`), **не** из URL/query. Подделать чужую коллекцию нельзя.

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/collection` | Сетка с прогрессом текущего игрока (vk_id из подписи) |
| GET | `/api/dragon/{id}` | Инфо (скрытое, если не выращен у текущего игрока) |
| GET | `/api/static/images/{id}.png` | Изображение |
| GET | `/api/auth/vk-login` | VK OAuth (для админки) |
| GET | `/api/auth/me` | Сессия админа |

Формат `/api/collection` (vk_id из подписи launch-params):
```json
{
  "grid": [
    {"x": 0, "y": 0, "dragon_id": 5, "status": "locked", "progress_pct": 0},
    {"x": 1, "y": 0, "dragon_id": 12, "status": "growing", "progress_pct": 50,
     "silhouette_url": "/api/static/images/12_silhouette.png"},
    {"x": 2, "y": 0, "dragon_id": 3, "status": "completed",
     "name": "Ледяной Ветер", "rarity": 2,
     "image_url": "/api/static/images/3.png"}
  ],
  "total_collected": 3,
  "total_dragons": 50
}
```

Формат `/api/dragon/{id}` (vk_id из подписи launch-params):
```json
{
  "is_revealed": false,
  "egg_type": "голубое яйцо с ледяными узорами",
  "steps_count": 3,
  "user_progress": {
    "status": "growing",
    "completed_steps": 1,
    "steps": [
      {"number": 1, "task": "Вышей 300 крестиков белыми/голубыми нитками", "completed": true},
      {"number": 2, "task": "Вышей 600 крестиков на сюжете с полётом", "completed": false},
      {"number": 3, "task": "Вышей один полный цветок на сюжете", "completed": false}
    ]
  }
}
```

## 6. Admin Portal

### Авторизация
- VK OAuth → проверка `vk_user_id ∈ config.admin_ids` → JWT-сессия
- Запасной вход по токену из конфига

### Полный workflow админа (пошаговый)

```
1. Создать сетку (Grid)
   Задать размеры (кол-во колонок × строк). Система создаст пустые ячейки.

2. Создать дракона (Dragon)
   Имя, редкость, egg_type, описание. Загрузить изображение + силуэт.
   При создании автоформируются N пустых шагов (steps_count от редкости).

3. Заполнить фазы выращивания (Steps)
   Для каждого шага: magic_action («положи яйцо на лёд») + task_description
   («вышей 300 крестиков голубыми нитками»). Число шагов можно менять.

4. Разместить дракона в ячейке (Grid)
   Drag & drop дракона в нужную позицию сетки. Один дракон = одна ячейка.

5. Сгенерировать PIN-коды (Pins)
   Указать количество → распределить по драконам → экспортировать CSV.
```

### Функции

**1. Dashboard** — статистика: PIN, игроки, последние действия

**2. Grid — управление сеткой (`/admin/grid`)**
- Создать новую сетку: задать `columns` × `rows` (например 10×5 = 50 ячеек)
- Автосоздание пустых ячеек в таблице `collection_grid`
- При добавлении новых драконов — можно расширить сетку
- Drag & drop: перетащить карточку дракона в ячейку → сохранить `dragon_id`
- Визуальный предпросмотр: как выглядит коллекция в Mini App
- Подсветка: ячейки с драконом (зелёные), пустые (серые)

**3. Dragons — CRUD драконов (`/admin/dragons`)**
- Список всех драконов (таблица / карточки)
- Создать дракона: имя, редкость (1–4), egg_type, описание
- Загрузить `image` и `silhouette`
- При создании: `steps_count` авто из редкости, сразу создаются пустые шаги
- Редактировать / архивировать (is_active = false)

**4. Steps — фазы выращивания (`/admin/dragons/{id}/steps`)**
- Список шагов (step_number, magic_action, task_description, hint)
- Добавить / удалить / переставить шаг (меняется steps_count дракона)
- Редактор каждого шага: два поля
  - **MagicAction**: текст магического действия («Положи яйцо на снег»)
  - **Задание**: текст вышивки («Вышей 300 крестиков белыми/голубыми нитками»)
- Предпросмотр: как это увидит игрок в боте
- **Важно**: бот читает шаги динамически из БД при каждом переходе —
  можно менять задания даже для активных драконов

**5. PIN Management (`/admin/pins`)**
- Генерация партии: количество + фильтр по редкости → случайное распределение
- Просмотр: таблица с фильтром по статусу (active / printed / used)
- Экспорт CSV для печати на листках-вкладышах
- Статус-машина: active → printed (админ отметил) → used (игрок ввёл)

**6. Users — игроки (`/admin/users`)**
- Список игроков: vk_id, дата регистрации, текущий дракон/шаг
- Деталка игрока: все драконы (выращенные / в процессе), пошаговый прогресс
- Админ-действия: «скип шага» (принудительно завершить), «сбросить прогресс»

## 7. VK Bot — FSM

```
idle ──(/pin или "пин")──→ await_pin ──(верный PIN)──→ grow_step_1
grow_step_N ──(2 фото в одном сообщении + текст содержит "вышито")──→ grow_step_{N+1}
                                                                      → completed
```

**Ключевое:** на всех шагах бот НЕ раскрывает имя/изображение дракона.
Обращается: "твоё яйцо", "твой дракончик", "яйцо с ледяными узорами".

**completed:** бот загружает картинку дракона в VK, пишет поздравление
с раскрытием имени + описания, отправляет ссылку на Mini App.

**Динамическое чтение шагов из БД:**

Бот не хранит шаги в памяти и не хардкодит их количество. При каждом переходе:
1. Запрашивает `steps_count` из `dragons WHERE id = current_dragon_id`
2. Запрашивает текущий шаг из `dragon_steps WHERE dragon_id = X AND step_number = N`
3. Отправляет задание игроку
4. При успешном отчёте → записывает в `user_progress` → переводит на `step+1`
5. Если `step > steps_count` → completed, раскрывает дракона

Это означает: админ может в любой момент изменить задания, добавить/удалить шаги,
и текущие игроки получат обновлённые тексты при следующем переходе.

Команда `/collection` → ссылка на Mini App.

## 8. PIN-коды

**Формат:** 4 цифры (например `4729`), генерируется автоматически при создании дракона.
Каждый дракон имеет ровно один PIN-код. Код уникален в пределах системы.

**Привязка к игроку** — будет добавлена позже.

**Продукт:** пластиковое яйцо (цвет/дизайн соответствует типу яйца в БД) →
внутри наклейка дракона + листок с PIN-кодом.

## 9. Изображения

- `images/dragons/{id}.png` — полное изображение
- `images/dragons/{id}_silhouette.png` — силуэт (до раскрытия)
- FastAPI отдаёт через `/api/static/images/`
- Бот при финале: `vk.upload.messages_upload` → attachment

## 10. Контент: брейншторм драконов

**Задача:** сгенерировать список из 100 драконов с:
- Название
- Редкость (1–4)
- Тип яйца (цвет, текстура, визуал)
- Описание (для финальной карточки)
- 2–5 шагов выращивания в формате: MagicAction → задание по вышивке

Заказчик отбирает 50 из 100. Хранить в `content/dragons-list.md`.

### Структура записи:
```markdown
### Дракон #N: Название
- **Редкость:** 1–4
- **Яйцо:** описание цвета/текстуры/визуала
- **Описание:** 1–2 предложения про дракона
- **Шаги:**
  1. MagicAction. Вышей NNN крестиков ...
  2. MagicAction. Вышей NNN крестиков ...
  ...
```

## 11. Фазы реализации

### Фаза 0 — Подготовка
- [ ] Создать структуру проекта, virtualenv, package.json
- [ ] `requirements.txt`: vk_api, fastapi, uvicorn, gunicorn, python-jose
- [ ] `frontend/package.json` (Node.js 16.x): react, vkui, @vkontakte/vk-bridge
- [ ] Настроить VK сообщество: токен бота, Longpoll API
- [ ] Зарегистрировать VK Mini App в VK Developers → app_id
- [ ] VK OAuth для админки (приложение VK ID)
- [ ] **Брейншторм 100 драконов** → `content/dragons-list.md` → отбор 50

### Фаза 1 — База + Бот (ядро)
- [ ] `bot/db.py` — таблицы (SQLite, WAL)
- [ ] `bot/models.py` — датаклассы
- [ ] `bot/fsm.py` — get_state/set_state
- [ ] `bot/main.py` — longpoll loop + диспетчер
- [ ] `bot/handlers/start.py` — /start
- [ ] `bot/services/pin_service.py` — генерация PIN
- [ ] `bot/handlers/pin.py` — ввод PIN → старт (скрывая дракона)
- [ ] `bot/services/step_service.py` — проверка: ≥2 фото + "вышито" в тексте
- [ ] `bot/handlers/grow.py` — приём отчётов, продвижение по шагам
- [ ] `bot/services/image_service.py` — загрузка в VK
- [ ] `bot/handlers/collection.py` — ссылка на Mini App
- [ ] `bot/handlers/admin.py` — админ-команды

### Фаза 2 — FastAPI (API)
- [ ] `api/main.py` — FastAPI + CORS
- [ ] `api/routes/collection.py` — GET /api/collection/{vk_id}
- [ ] `api/routes/dragon.py` — GET /api/dragon/{id} (скрытие до revealed)
- [ ] `api/routes/auth.py` — VK OAuth + JWT
- [ ] `api/middleware.py` — admin middleware

### Фаза 3 — Mini App (React + VKUI)
- [ ] Vite + React + VKUI + VK Bridge
- [ ] Collection: сетка с силуэтами / прогрессом / раскрытыми
- [ ] DragonCell: locked(?)/growing(%+силуэт)/completed(изображение)
- [ ] DragonDetail: скрытый режим (яйцо + шаги) / полная карточка

### Фаза 4 — Admin Portal
- [ ] VK OAuth login
- [ ] Dashboard
- [ ] Dragons CRUD + Steps editor + egg_type
- [ ] Grid Editor (drag & drop)
- [ ] PIN generation + export CSV
- [ ] Users / progress

### Фаза 5 — Деплой
- [ ] Сборка React → nginx (SPA)
- [ ] systemd: bot.service + api.service (gunicorn)
- [ ] nginx: /api/* → FastAPI, / → React
- [ ] Настройка VK Mini App: URL, иконка, права
- [ ] Тест полного цикла: PIN → 2-5 шагов → Mini App → админка
- [ ] Приёмочное с реальным игроком

## 12. Риски

| Риск | Смягчение |
|---|---|
| **Подмена vk_id в Mini App (чужая коллекция)** | vk_id берётся из подписанных launch-params VK (`sign`), бэкенд верифицирует HMAC-SHA256 секретом приложения; значение из query/пути не доверяется |
| **SQLite конкуренция (бот + API)** | WAL-режим, timeout=30, раздельные соединения |
| **VK Mini App модерация** | Изучить правила заранее, только свой контент |
| **VK OAuth в админке** | Запасной вход по токену из конфига |
| **Изменение VK API** | Версия vk_api зафиксирована |
| **Потеря данных** | Ежедневный бэкап `cp` файла БД + ротация через cron |
