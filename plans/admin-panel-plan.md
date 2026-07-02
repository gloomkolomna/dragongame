# План: Admin Panel — Коллекция драконов

## 1. Цель

Веб-панель администратора для управления контентом игры:
драконы, сетка коллекции, шаги выращивания, PIN-коды, игроки.

## 2. Стек

| Слой | Технология |
|---|---|
| Фронтенд | React 18 + VKUI + react-router-dom v6 |
| Бэкенд | FastAPI (Python 3.10+, тот же сервер что бот и Mini App) |
| Auth | VK OAuth PKCE (`id.vk.com`) + JWT + whitelist по ID |
| БД | SQLite3 — WAL-режим (общая с ботом и Mini App API) |
| Сборка | Vite |

## 3. Auth — авторизация

### Бэкенд (по образцу `D:\Боты\Учет\src\backend`)

**Эндпоинты:**

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/auth/vk-login` | Генерация VK OAuth URL (PKCE) |
| GET | `/api/auth/vk-callback` | Обмен кода → проверка whitelist → JWT → редирект на фронт |
| GET | `/api/auth/me` | Данные текущего пользователя (из JWT) |
| GET | `/api/auth/config` | Флаг `dev_login_enabled` |

**Файлы:**
- `api/auth.py` — функции: PKCE (code_verifier/challenge), обмен кода,
  проверка whitelist, JWT create/verify, `get_current_admin` dependency
- `api/routes/auth.py` — роуты выше
- `api/config.py` — `SECRET_KEY`, `VK_CLIENT_ID`, `VK_CLIENT_SECRET`,
  `VK_REDIRECT_URI`, `VK_ALLOWED_IDS` (из `.env`)

**Whitelist:**
```python
# .env
VK_ALLOWED_IDS=123456789,987654321

# config.py
def get_allowed_vk_ids() -> set[int]:
    raw = os.getenv("VK_ALLOWED_IDS", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}

# При vk-callback: if user_id not in allowed → 403
```

**Dev-режим (локальный вход без VK):**

При `APP_ENV=dev` в `.env` включается обходной вход для локальной разработки.
Работает так же как в `Учет/src/backend` — без обмена кодами VK,
но с проверкой whitelist.

Бэкенд:
```
POST /api/auth/dev-login
```
- Берёт первый ID из `VK_ALLOWED_IDS`
- Создаёт/получает пользователя с именем "Dev Tester"
- Возвращает `{access_token: "...", token_type: "bearer"}`
- Если `APP_ENV != dev` — возвращает 404 (роут не активен на проде)
- Если `VK_ALLOWED_IDS` пуст — возвращает 500

```python
# config.py
APP_ENV = os.getenv("APP_ENV", "production").strip().lower()
DEV_LOGIN_ENABLED = (APP_ENV == "dev")

# routes/auth.py
@router.post("/dev-login")
def dev_login(db: Session = Depends(get_db)):
    if not DEV_LOGIN_ENABLED:
        raise HTTPException(status_code=404)
    allowed = get_allowed_vk_ids()
    if not allowed:
        raise HTTPException(status_code=500, detail="VK_ALLOWED_IDS пуст")
    vk_id = sorted(allowed)[0]
    user = get_or_create_user(db, vk_id, "Dev", "Tester")
    token = create_access_token(data={"sub": str(user.vk_id)})
    return {"access_token": token, "token_type": "bearer"}
```

Фронтенд:
- При загрузке Login.tsx вызывает `GET /api/auth/config` → получает `dev_login_enabled`
- Если `true` — под основной кнопкой VK ID появляется разделитель и кнопка «Войти локально (тест)»
- При клике: POST `/api/auth/dev-login` → получает токен → setToken → navigate('/')

### Фронтенд

React-компоненты (в `frontend/src/`):

```
context/
  AuthContext.tsx    — user, token, setToken, logout, isAuthenticated
                      токен в localStorage, axios default header
pages/
  Login.tsx          — кнопка "Войти через VK ID", обработка ?token=
components/
  ProtectedRoute.tsx — обёртка: если !isAuthenticated → /admin/login
```

**Поток:**
1. Пользователь → `/admin/login` → кнопка "Войти через VK ID"
2. GET `/api/auth/vk-login` → `{url: "https://id.vk.com/authorize?...&code_challenge=...&state=..."}`
3. window.location.href = url → VK авторизация
4. VK редирект → `/api/auth/vk-callback?code=...&state=...`
5. Бэкенд проверяет PKCE → обменивает code → VK user_info → проверяет whitelist
6. Создаёт JWT → редирект на `{FRONTEND_URL}/admin/login?token={jwt}`
7. Login.tsx читает `?token=` → AuthContext.setToken → navigate('/admin/dashboard')
8. Все защищённые роуты обёрнуты в `<ProtectedRoute>`

## 4. Страницы и маршруты

```
/admin/login              → Login.tsx (без защиты)
/admin/dashboard          → Dashboard.tsx
/admin/dragons            → DragonsList.tsx
/admin/dragons/new        → DragonForm.tsx
/admin/dragons/:id/edit   → DragonForm.tsx
/admin/dragons/:id/steps  → StepsEditor.tsx
/admin/grid               → GridEditor.tsx
/admin/pins               → PinManager.tsx
/admin/users              → UsersList.tsx
```

Общий layout: `AdminLayout.tsx` — сайдбар (навигация) + `<Outlet/>`.

### Сайдбар (навигация)

```
📊 Дашборд
🐉 Драконы
📐 Сетка
🔑 PIN-коды
👥 Игроки
```

VKUI компоненты: `SplitLayout`, `SplitCol`, `PanelHeader`, `Tabbar`/`Cell`.

## 5. Секции админки — что видишь и зачем

### 5.1 📊 Дашборд (`/admin/dashboard`)

**Зачем:** точка входа после логина. Первый экран с общей картиной игры.
Без дашборда админ начинает работать вслепую — не знает, сколько
драконов создано, сколько PIN выдано, сколько игроков активно.

**Что видит админ:**
- 6 карточек-счётчиков в сетке 3×2:
  - 🐉 Всего драконов / активно
  - 🔑 PIN: всего / активно / использовано
  - 👥 Игроков зарегистрировано
  - ⭐ Выращено драконов (сумма по всем игрокам)
- Каждая карточка — крупная цифра + подпись
- При клике на карточку — переход в соответствующую секцию

**Действия:** только просмотр. Это read-only экран.

**API:** `GET /api/admin/stats`

```json
{
  "dragons_total": 50,
  "dragons_active": 45,
  "pins_total": 200,
  "pins_active": 50,
  "pins_used": 120,
  "users_total": 15,
  "dragons_collected_total": 30
}
```

### 5.2 🐉 Драконы (`/admin/dragons`)

**Зачем:** управление контентом игры. Дракон — центральная сущность.
Пока дракон не создан в системе — его нельзя выращивать, привязать PIN,
разместить в сетке коллекции. Это фундамент всего.

**Что видит админ:**
- Список всех драконов: таблица с колонками
  - ID, Название, Редкость (1-4), Тип яйца, Активен?, Шагов
  - Каждая строка — ссылка на редактирование
- Кнопка «+ Создать дракона» над таблицей
- Кнопка «Редактировать» → форма с предзаполненными полями
- Кнопка «Удалить» → диалог подтверждения
- Фильтр: «показать только активные»

**Форма создания/редактирования:**
- Поле: **Название** (Input). Скрыто от игрока до финала.
- Поле: **Редкость** (Select: Обычный/Редкий/Эпический/Легендарный).
  Редкость — это только уровень дракона, без привязки к числу шагов.
- Поле: **Тип яйца** (Input). Например «голубое яйцо с ледяными узорами».
  Это единственное, что игрок видит до раскрытия дракона.
- Поле: **Описание** (Textarea). Текст для финальной карточки.
- Поле: **Изображение** (file upload). Полная картинка дракона.
- Поле: **Силуэт** (file upload). Теневое изображение для Mini App до раскрытия.
- Чекбокс: **Активен** (доступен для игры).

**Что происходит при создании:**
1. Сохраняется запись в `dragons`, `steps_count = 0`
2. Изображения сохраняются в `images/dragons/{id}.png` и `images/dragons/{id}_silhouette.png`
3. Шагов изначально нет — админ добавляет их вручную в Steps Editor

**Шаги — отдельно от создания дракона:**
- В форме создания дракона поля «кол-во шагов» нет
- Админ создаёт дракона → переходит в Steps Editor → добавляет шаги кнопкой «+ Добавить шаг»
- Шагов может быть сколько угодно (нет ограничения 2–5)
- `dragon.steps_count` обновляется автоматически при добавлении/удалении шагов

**Почему это важно:** без драконов игра не существует.
Админ создаёт дракона → наполняет шаги → размещает в сетке → генерирует PIN.
Это первый шаг цепочки.

**API:**
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/dragons` | Список |
| GET | `/api/admin/dragons/{id}` | Один дракон |
| POST | `/api/admin/dragons` | Создать (multipart: image, silhouette, json) |
| PUT | `/api/admin/dragons/{id}` | Обновить |
| DELETE | `/api/admin/dragons/{id}` | Удалить (каскадно: шаги, ячейки, PIN) |

### 5.3 📝 Шаги выращивания (`/admin/dragons/{id}/steps`)

**Зачем:** наполнить дракона смыслом. Шаги — это задания, которые игрок
будет выполнять в боте. Без них дракон — просто картинка в сетке.
Шаги определяют геймплей: сколько вышивать, на какую тему,
с каким магическим контекстом. Количество шагов не ограничено —
админ добавляет столько, сколько нужно для сюжета дракона.

**Что видит админ:**
- Заголовок: «Дракон: Ледяной Ветер — 3 шага»
- Список шагов. Каждый шаг — карточка:
  - Номер шага (1, 2, 3...)
  - Ручка перетаскивания (слева, для drag & drop)
- Поле **MagicAction**: «Положи яйцо на снег»
   - Поле **Задание**: «Вышей 300 крестиков белыми/голубыми нитками»
   - Поле **Ключевое слово** (опционально): «лёд» — бот будет проверять его наличие
     в сообщении с фотоотчётом
   - Поле **Подсказка** (опционально): «Подойдёт любой зимний сюжет»
  - Кнопка 🗑 удалить шаг
- Кнопка «+ Добавить шаг» — добавляет новый шаг в конец (нет ограничения на количество)
- Кнопка «Сохранить» (PUT всего списка)
- При удалении шага — оставшиеся перенумеровываются, `dragon.steps_count` обновляется
- Блок **Предпросмотр**: как это увидит игрок в боте —
  «Твоё яйцо хочет полежать на снегу! Для этого тебе нужно вышить 300 крестиков белыми или голубыми нитками. Когда закончишь, пришли ДВА фото (до и после) и напиши слово "вышито".»

**Drag & drop:** админ перетаскивает шаги меняя их порядок.
Шаг 1 ↔ Шаг 3 — задания меняются местами в игровом процессе.
При сохранении `step_number` перезаписывается по новому порядку.

**Почему это важно:** это творческая часть. Админ придумывает сюжетную линию
выращивания для каждого дракона. Шаги читаются ботом динамически из БД —
их можно менять даже когда игроки уже в процессе.

**API:**
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/dragons/{id}/steps` | Все шаги |
| PUT | `/api/admin/dragons/{id}/steps` | Сохранить список (с новыми номерами) |
| POST | `/api/admin/dragons/{id}/steps` | Добавить шаг |
| DELETE | `/api/admin/dragons/{id}/steps/{step_id}` | Удалить шаг |

### 5.4 📐 Сетка (`/admin/grid`)

**Зачем:** управлять визуальным расположением драконов в Mini App.
Сетка — это то, что игрок видит когда открывает свою коллекцию.
Админ решает: кто где стоит, какие драконы рядом, как выглядит раскладка.

**Что видит админ:**

При первом входе (сетка не создана):
- Кнопка «Создать сетку» → модалка: ввести кол-во колонок × строк
  (например 10×5 = 50 ячеек для 50 драконов)
- После создания — система генерирует ячейки в таблице `collection_grid`

После создания сетки:
- Слева: **панель неразмещённых драконов** (drag source)
  - Карточки драконов не привязанных к ячейкам
  - Каждая карточка: мини-изображение (силуэт) + название + редкость
  - Можно перетаскивать
- Справа: **интерактивная сетка** (CSS Grid)
  - Ячейки, уже занятые драконом: зелёная рамка, имя, мини-изображение
    Можно «вытащить» обратно в панель (drag out → ячейка очищается)
  - Пустые ячейки: серый контур с «+»
    Можно «бросить» дракона из панели → ячейка заполняется
  - Сетка масштабируется: если 10×5, то 10 колонок в ширину
- Кнопка «Сохранить» — применяет все изменения
- Кнопка «Расширить сетку» — добавить строку/колонку (новые пустые ячейки)

**Почему это важно:** сетка определяет UX коллекции для всех игроков.
Админ может группировать драконов по редкости, по стихиям, по цвету яиц —
создавая визуально приятную и логичную раскладку.

**API:**
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/grid` | Все ячейки (включая пустые) |
| POST | `/api/admin/grid/create` | Создать сетку `{"columns": 10, "rows": 5}` |
| PUT | `/api/admin/grid/cell/{id}` | Назначить дракона в ячейку |
| DELETE | `/api/admin/grid/cell/{id}` | Очистить ячейку |
| PUT | `/api/admin/grid` | Массовое сохранение |

### 5.5 🔑 PIN-коды (`/admin/pins`)

**Зачем:** сводная таблица всех драконов и их PIN-кодов. PIN — это ключ,
который игрок получает физически (в яйце) и вводит в боте для старта игры.
Каждый дракон имеет ровно один 4-значный PIN-код, генерируемый при создании.

**Что видит админ:**
- Таблица: Дракон | PIN-код (4 цифры) | Редкость | Тип яйца | Шагов | Активен

**Особенности:**
- PIN-код создаётся автоматически при создании дракона (нельзя задать вручную)
- Код уникален, 4 цифры (например `4729`)
- Привязка PIN к игроку будет добавлена позже

**API:**
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/pins` | Список драконов с PIN-кодами |

### 5.6 👥 Игроки (`/admin/users`)

**Зачем:** учёт игроков и выданных им PIN-кодов. Админ должен видеть
связку «физическое яйцо → PIN → игрок», чтобы отвечать на вопросы:
«какой PIN ушёл этому игроку?», «кто активировал PIN X7F9-K3M2?»,
«какие яйца уже выданы, а какие ещё лежат на складе?».
Плюс техподдержка — скип шага, сброс прогресса.

**Что видит админ:**

**Таблица игроков:**
  - VK ID
  - Имя (из VK: Иван Петров)
  - Дата регистрации
  - PIN-кодов активировано (число — сколько яиц открыл)
  - Последний PIN: «X7F9-K3M2 → Ледяной Ветер» или «—»
  - Текущий дракон: «яйцо (Ледяной Ветер) на шаге 2 из 4» или «—»
  - Статус: 🟢 выращивает / ⚪ idle / ✅ завершил последнего
  - Колонка «Выращено»: 3 из 50

**При клике на строку → деталка игрока** (модальное окно или отдельная страница `/admin/users/:vk_id`):

Секция 1 — **Активированные PIN-коды** (связка «физическое яйцо → цифра»):
  - Таблица: PIN-код | Дракон | Тип яйца | Дата активации | Статус
  - Пример строки:
    ```
    X7F9-K3M2 | Ледяной Ветер | голубое с ледяными узорами | 01.07.2026 | ✅ выращен
    A1B2-C3D4 | Огненный Шёпот | оранжевое с искрами | 15.07.2026 | 🌱 шаг 1 из 3
    ```
  - Это отвечает на вопрос: «какие PIN-коды отправлены этому человеку и что с ними происходит?»
  - Если игрок потерял карточку — админ видит код и может продублировать

Секция 2 — **Все драконы в коллекции**:
  - Сетка/список: 🔒 не начат / 🌱 в процессе с % / ⭐ выращен
  - Не начатые — серый силуэт, не кликабельные
  - В процессе — имя яйца, прогресс-бар, текущее задание
  - Выращенные — полное имя, изображение, дата завершения

Секция 3 — **Действия**:
  - Кнопка **«Скип шага»** — принудительно завершает текущий шаг.
    Игрок получает следующее задание.
    Когда: фото не отправляется, баг, ошибка игрока.
  - Кнопка **«Сбросить дракона»** — полный сброс прогресса по текущему дракону.
    Игрок начинает заново с шага 1.
    Когда: критическая ошибка, нужен перезапуск.

**Почему это важно:** это единое окно техподдержки и учёта.
Админ видит всю историю игрока: когда зарегистрировался,
какие PIN получил, каких драконов вырастил, на каком шаге застрял.
Связка PIN → игрок критична для логистики физических яиц:
админ знает кому что отправлено и может отследить путь каждого яйца.

**API:**
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/users` | Список (с last_pin, pins_count, dragons_collected) |
| GET | `/api/admin/users/{vk_id}` | Деталка: профиль + все PIN + все драконы |
| POST | `/api/admin/users/{vk_id}/skip-step` | Скип шага |
| POST | `/api/admin/users/{vk_id}/reset-dragon` | Сброс дракона |

Формат деталки `GET /api/admin/users/{vk_id}`:
```json
{
  "vk_id": 123456789,
  "first_name": "Иван",
  "last_name": "Петров",
  "registered_at": "2026-07-01T12:00:00",
  "pins_activated": 3,
  "pins": [
    {"code": "X7F9-K3M2", "dragon_name": "Ледяной Ветер", "egg_type": "голубое с узорами",
     "status": "completed", "activated_at": "2026-07-01T12:05:00"},
    {"code": "A1B2-C3D4", "dragon_name": "Огненный Шёпот", "egg_type": "оранжевое с искрами",
     "status": "growing", "activated_at": "2026-07-15T09:30:00", "current_step": "1 из 3"}
  ],
  "dragons": [
    {"dragon_id": 5, "name": null, "egg_type": "голубое с узорами",
     "status": "completed", "completed_at": "2026-07-05T00:00:00"},
    {"dragon_id": 12, "name": null, "egg_type": "оранжевое с искрами",
     "status": "growing", "progress_pct": 33, "current_step": 1, "steps_total": 3}
  ],
  "dragons_collected": 1,
  "dragons_total": 50
}
```

## 6. Структура файлов

```
frontend/src/
├── App.tsx                    # роутинг
├── context/
│   └── AuthContext.tsx        # user, token, isAuthenticated, logout
├── pages/
│   ├── Login.tsx              # кнопка VK ID
│   ├── AdminLayout.tsx        # сайдбар + <Outlet>
│   ├── admin/
│   │   ├── Dashboard.tsx
│   │   ├── DragonsList.tsx    # таблица драконов
│   │   ├── DragonForm.tsx     # создание/редактирование
│   │   ├── StepsEditor.tsx    # drag & drop шагов
│   │   ├── GridEditor.tsx     # drag & drop ячеек
│   │   ├── PinManager.tsx     # генерация/экспорт
│   │   └── UsersList.tsx      # таблица игроков + деталка
├── components/
│   ├── ProtectedRoute.tsx     # проверка isAuthenticated
│   ├── FileUpload.tsx         # загрузка изображений
│   └── ConfirmDialog.tsx      # подтверждение удаления/скипа
└── api/
    └── client.ts              # axios instance с Bearer-токеном

api/
├── auth.py                    # PKCE, JWT, whitelist, get_current_admin
├── config.py                  # SECRET_KEY, VK_CLIENT_ID, VK_ALLOWED_IDS
├── models.py                  # SQLAlchemy модели (для Alembic)
├── alembic.ini                # конфиг Alembic
├── alembic/
│   ├── env.py                 # target_metadata = Base.metadata
│   ├── script.py.mako         # шаблон миграций
│   └── versions/              # файлы миграций (*.py)
├── routes/
│   ├── auth.py                # /api/auth/*
│   └── admin.py               # /api/admin/* (dragons, grid, pins, users, stats)
├── services/
│   ├── dragon_service.py      # CRUD + image save
│   ├── grid_service.py        # CRUD grid, create grid
│   ├── pin_service.py         # генерация, экспорт CSV
│   ├── step_service.py        # CRUD + reorder steps
│   └── user_service.py        # get users, progress, skip/reset
├── db.py                      # общий доступ к SQLite (WAL)
├── backups/                   # папка с бэкапами (*.bak.*)
└── main.py                    # FastAPI app, mount CORS, include routers

deploy/
├── deploy.sh                  # деплой (бэкап → миграции → сборка → рестарт → health-check)
├── backup.sh                  # ежедневный бэкап (cron)
├── dragons-api.service        # systemd: gunicorn FastAPI
└── dragons-bot.service        # systemd: python bot
```

## 7. Резервное копирование, миграции и деплой

### 7.1 Инструменты

| Инструмент | Назначение |
|---|---|
| **Alembic** | Миграции БД (версионирование схемы, upgrade/downgrade) |
| **SQLAlchemy** | ORM-модели (регистрируются в `Base.metadata` для автогенерации миграций) |
| **deploy.sh** | Деплой-скрипт (бэкап → миграции → сборка → рестарт → health-check) |
| **backup.sh** | Ежедневный бэкап через cron |

Alembic подключается к SQLite через `DATABASE_URL` из `.env`.
Модели SQLAlchemy описывают актуальную схему БД, Alembic генерирует
миграции автоматически (`--autogenerate`).
**Важно:** для SQLite используется Alembic batch mode (ALTER TABLE recreate),
так как SQLite не поддерживает DROP COLUMN и ALTER COLUMN напрямую.
Модели SQLAlchemy описывают актуальную схему БД, Alembic генерирует
миграции автоматически (`--autogenerate`). Все изменения БД — только через миграции.

### 7.2 Структура миграций

Файлы в `api/`:
```
api/
├── alembic.ini              # конфиг Alembic (sqlalchemy.url из .env)
├── alembic/
│   ├── env.py               # target_metadata = Base.metadata, DATABASE_URL
│   ├── script.py.mako       # шаблон миграции
│   └── versions/
│       ├── 001_initial.py   # создание всех таблиц
│       ├── 002_add_egg_type.py  # ALTER TABLE dragons ADD COLUMN egg_type
│       └── ...
└── models.py                # SQLAlchemy модели (единый источник истины)
```

**minimal models.py:**
```python
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Dragon(Base):
    __tablename__ = "dragons"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    egg_type = Column(String, default="")
    rarity = Column(Integer, nullable=False)
    steps_count = Column(Integer, nullable=False)
    image_path = Column(String, default="")
    silhouette_path = Column(String, default="")
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
# ... остальные таблицы
```

**Команды Alembic:**
```bash
# Создать новую миграцию (автоматически из изменений в models.py)
python -m alembic revision --autogenerate -m "add dragon egg_type"

# Применить все неприменённые миграции
python -m alembic upgrade head

# Откатить на одну миграцию назад
python -m alembic downgrade -1

# Посмотреть текущую ревизию
python -m alembic current

# Посмотреть историю миграций
python -m alembic history
```

### 7.3 Резервное копирование

**Ежедневный бэкап (cron):**
```bash
# /etc/cron.d/dragons-backup — каждый день в 03:00
0 3 * * * root /opt/dragons/deploy/backup.sh
```

**backup.sh:**
```bash
#!/bin/bash
DB_FILE="/opt/dragons/api/dragons.db"
BACKUP_DIR="/opt/dragons/api/backups"
BACKUPS_TO_KEEP=10

mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
cp "$DB_FILE" "$BACKUP_PATH"

# Ротация: держим последние 10
ls -1t "$BACKUP_DIR"/dragons.db.bak.* | tail -n +$((BACKUPS_TO_KEEP + 1)) | xargs rm -f
```

**Бэкап перед деплоем (в deploy.sh):**
- Фиксируется текущая ревизия Alembic (точка отката)
- Создаётся копия БД **до** миграции
- При ошибке миграции — откат через `alembic downgrade`, при неудаче — восстановление из копии

### 7.4 Деплой-скрипт (`deploy/deploy.sh`)

По образцу `D:\Боты\Учет\deploy.sh`. 7 этапов, откат при любой ошибке:

```bash
#!/bin/bash
set -euo pipefail

APP_DIR="/opt/dragons"
API_DIR="$APP_DIR/api"
FRONTEND_DIR="$APP_DIR/frontend"
DB_FILE="$API_DIR/dragons.db"
BACKUP_DIR="$API_DIR/backups"
BACKUPS_TO_KEEP=10
HEALTH_URL="https://domain.ru/api/"
LOG_FILE="$API_DIR/deploy.log"

PREV_REV=""
FRESH_DEPLOY=0
BACKUP_PATH=""
MIGRATION_RAN=0
SERVICE_RESTARTED=0

mkdir -p "$BACKUP_DIR"

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
    log "ОТКАТ: нужен ручной разбор."
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

# 1. Фиксация текущей ревизии
log "=== 1. Текущая ревизия ==="
cd "$API_DIR" && source venv/bin/activate
PREV_REV=$(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)
[ -z "$PREV_REV" ] && FRESH_DEPLOY=1 || log "Ревизия: $PREV_REV"

# 2. Бэкап ДО миграции
log "=== 2. Бэкап ==="
if [ -f "$DB_FILE" ]; then
    BACKUP_PATH="$BACKUP_DIR/dragons.db.bak.$(date '+%Y%m%d_%H%M%S')"
    cp "$DB_FILE" "$BACKUP_PATH"
    log "Бэкап: $BACKUP_PATH"
    ls -1t "$BACKUP_DIR"/dragons.db.bak.* | tail -n +$((BACKUPS_TO_KEEP+1)) | xargs rm -f
else
    log "БД не найдена — новая установка."
fi

# 3. git pull
log "=== 3. git pull ==="
cd "$APP_DIR" && git pull

# 4. Миграции
log "=== 4. Миграции ==="
cd "$API_DIR" && source venv/bin/activate
python -m alembic upgrade head
MIGRATION_RAN=1
log "Текущая ревизия: $(python -m alembic current 2>/dev/null | awk '{print $1}' | head -n1)"

# 5. Сборка фронта
log "=== 5. Сборка фронта ==="
cd "$FRONTEND_DIR"
rm -rf dist && npm install && npm run build

# 6. Перезапуск сервисов
log "=== 6. Перезапуск ==="
systemctl restart dragons-api
systemctl restart dragons-bot
SERVICE_RESTARTED=1
sleep 3
systemctl is-active dragons-api dragons-bot

# 7. Health-check
log "=== 7. Health-check ==="
for i in 1 2 3 4 5; do
    curl -fsS -o /dev/null "$HEALTH_URL" && break
    log "Попытка $i/5..."
    sleep 3
done && log "=== Деплой успешен ===" || { log "Health-check провален."; false; }
```

**systemd-сервисы:**
```
/etc/systemd/system/dragons-api.service   # gunicorn FastAPI
/etc/systemd/system/dragons-bot.service   # python bot/main.py
```

### 7.5 Порядок работы с миграциями при разработке

1. Изменил `models.py` → добавил/убрал поле, таблицу
2. `python -m alembic revision --autogenerate -m "описание"` → создал файл в `versions/`
3. Проверил сгенерированный `upgrade()` и `downgrade()` — поправил если нужно
4. `python -m alembic upgrade head` → применил локально
5. Закоммитил и запушил вместе с кодом
6. На проде `deploy.sh` сам применит миграцию перед перезапуском

## 8. Порядок реализации

### Шаг 1 — Auth
- [ ] `api/config.py` — VK_*, SECRET_KEY, DATABASE_URL, APP_ENV, DEV_LOGIN_ENABLED
- [ ] `api/models.py` — SQLAlchemy модели всех таблиц (единый источник для Alembic)
- [ ] `api/auth.py` — PKCE (code_verifier, code_challenge), JWT, whitelist, get_current_admin, get_or_create_user
- [ ] `api/routes/auth.py` — vk-login, vk-callback, me, config, **dev-login**
- [ ] `frontend` — Login.tsx (VK ID + локальный вход), AuthContext.tsx, ProtectedRoute.tsx
- [ ] Проверка: вход через VK → JWT в localStorage → /admin/dashboard
- [ ] Проверка локального входа: `APP_ENV=dev` → кнопка «Войти локально» → токен → dashboard

### Шаг 1.5 — Alembic и начальная миграция (делается сразу после models.py)
- [ ] `api/alembic.ini` — скопирован, `sqlalchemy.url` переопределён через `.env`
- [ ] `api/alembic/env.py` — target_metadata = Base.metadata, DATABASE_URL из config
- [ ] `python -m alembic revision --autogenerate -m "initial"` → первая миграция
- [ ] `python -m alembic upgrade head` → создаёт все таблицы в SQLite
- [ ] Проверка: `python -m alembic current` → показывает ревизию

### Шаг 2 — Dashboard
- [ ] `api/routes/admin.py` — GET /api/admin/stats
- [ ] `frontend` — Dashboard.tsx + AdminLayout.tsx с сайдбаром
- [ ] Проверка: статистика обновляется

### Шаг 3 — Dragons CRUD
- [ ] `api/services/dragon_service.py` — CRUD + загрузка изображений
- [ ] `api/routes/admin.py` — dragons CRUD эндпоинты (multipart)
- [ ] `frontend` — DragonsList.tsx, DragonForm.tsx, FileUpload.tsx
- [ ] Проверка: создать дракона → редактировать → удалить

### Шаг 4 — Steps Editor
- [ ] `api/services/step_service.py` — CRUD, reorder
- [ ] `api/routes/admin.py` — steps эндпоинты
- [ ] `frontend` — StepsEditor.tsx (drag & drop)
- [ ] Проверка: создать/удалить/переставить шаги

### Шаг 5 — Grid Editor
- [ ] `api/services/grid_service.py` — create grid, CRUD cells
- [ ] `api/routes/admin.py` — grid эндпоинты
- [ ] `frontend` — GridEditor.tsx (drag source: драконы, drop target: ячейки)
- [ ] Проверка: создать сетку → перетащить драконов → сохранить

### Шаг 6 — PIN Manager
- [ ] `api/services/pin_service.py` — генерация, экспорт CSV
- [ ] `api/routes/admin.py` — pins эндпоинты
- [ ] `frontend` — PinManager.tsx (фильтры, таблица, генерация, экспорт)
- [ ] Проверка: сгенерировать 10 PIN → экспорт CSV → сменить статус

### Шаг 7 — Users
- [ ] `api/services/user_service.py` — get users, progress, skip/reset
- [ ] `api/routes/admin.py` — users эндпоинты
- [ ] `frontend` — UsersList.tsx + деталка с кнопками skip/reset
- [ ] Проверка: список игроков → деталка → скип шага → сброс

### Шаг 8 — Бэкап и деплой
- [ ] `deploy/backup.sh` — ежедневный бэкап + ротация
- [ ] `deploy/deploy.sh` — 7-этапный деплой с откатом (по образцу `Учет/deploy.sh`)
- [ ] `deploy/dragons-api.service` — systemd gunicorn
- [ ] `deploy/dragons-bot.service` — systemd python bot
- [ ] cron-задача: `0 3 * * * root /opt/dragons/deploy/backup.sh`
- [ ] Проверка: `./deploy.sh` → бэкап → миграции → сборка → health-check OK

## 9. Риски

| Риск | Смягчение |
|---|---|
| VK OAuth PKCE сложность | Копируем рабочий код из `Учет/src/backend/auth.py` |
| Файловая загрузка изображений | multipart через FastAPI `UploadFile`, лимит 5MB |
| Drag & drop (Steps и Grid) | `@dnd-kit/core` — лёгкая, активно поддерживается, работает с VKUI |
| CORS между фронтом и API | FastAPI `CORSMiddleware` разрешает `FRONTEND_URL` + VK домены |
| **Миграция сломала БД на проде** | Бэкап ДО миграции + alembic downgrade + восстановление копии файла при отказе |
| **SQLite не поддерживает DROP COLUMN** | Alembic batch mode (ALTER TABLE recreate) |
| **Расхождение models.py и реальной схемы** | `alembic check` в CI, автогенерация только из models.py |
