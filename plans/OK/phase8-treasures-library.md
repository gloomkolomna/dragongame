# Фаза 8 — Сокровища и Библиотека

> **Базовый план:** [expansion-plan.md](./expansion-plan.md)

## Назначение документа

Фаза 8 вводит явную семантику редкостей драконов и две новые сущности —
**сокровища** (награда от редких драконов) и **Библиотеку легенд** (вынесенный
раздел мини-аппа). Документ самодостаточен, но перекрёстно ссылается на
`expansion-plan.md`.

**Контекст:** в `expansion-plan.md` зафиксированное решение **#2** ошибочно
описывало концепцию как «наград за редкость нет, сокровищ нет». Фаза 8
**отменяет** эту ошибку — сокровища вводятся как награда за редких драконов.
См. перекрёстную таблицу в конце документа.

- **Зависимости:** Фаза 1 (копилка / `complete_dragon`).
- **Сложность:** 🟡 средняя.
- **Граф:** самостоятельная фаза, не блокирует и не блокируется Фазами эпика.

---

## 1. Контекст — что меняется в концепции

Три редкости драконов получают явную семантику награды при завершении:

| Редкость | Награда при завершении |
|----------|------------------------|
| **Обычный (rarity=1)** | крестики в копилку |
| **Редкий (rarity=2)** | крестики + **сокровище** (карточка в Пещеру) |
| **Легендарный (rarity=3)** | крестики + **легенда** (в Библиотеке) |

Сокровище — это карточка-коллекция (фото + название + описание), без
геймплейных эффектов. Альбом собранных сокровищ = раздел «Пещера» мини-аппа.

### Перекрёстные пометки
- `expansion-plan.md` → **Зафиксированные решения #2** («наград за редкость нет,
  сокровищ нет») → **отменяется Фазой 8**.
- `expansion-plan.md` → **Что НЕ входит** (строка «сокровища и любые награды за
  редкость») → **отменяется Фазой 8**.
- `expansion-plan.md` → **Решение #16** (`rarity` остаётся 1–3, rarity 4 не
  вводится) → **подтверждается**.

---

## 2. Зафиксированные решения Фазы 8

Продолжают нумерацию `expansion-plan.md` (#27–#34).

- **#27 Сокровище = жёсткая привязка** к редкому дракону. Таблица `treasures`
  с FK→`dragons`, связь **1:1** (один дракон — одно сокровище).
  *Отменяет `expansion-plan.md` #2.*
- **#28 Форма сокровища — отдельная**, доступна у редкого дракона (rarity=2).
  Ровно **3 поля: фото + название + описание**. Поля «категория» НЕТ.
- **#29 Выдача один раз** в `complete_dragon`, idempotent по паре (user, dragon).
  Если у редкого дракона форма сокровища не заполнена → игрок получает только
  крестики в копилку.
- **#30 Сообщение бота в финале редкого** = текст «💎 Вы получили сокровище:
  {name}!» + **описание** + **прикреплённое фото** сокровища
  (через `upload_image`).
- **#31 Сброс/удаление только админом** → сокровище изымается
  (`reset_dragon`, `delete_user_dragon`). Игрок не может сбросить дракона сам.
- **#32 Библиотека = индекс легенд** всех легендарных (rarity=3) с прогрессом.
  В карточке дракона (`DragonDetail`) остаётся **превью + ссылка**
  «Открыть в Библиотеке».
- **#33 Навигация мини-аппа — 5 вкладок:** Бестиарий `/` · Пещера `/cave`
  (сокровища) · Библиотека `/library` (легенды) · Гнездо `/nest` (эпик, бывший
  `/cave`) · Лавка `/shop`.
  *Расширяет `expansion-plan.md` Фаза 7 (3 вкладки → 5).*
- **#34 Пещера = единая галерея:** собранные — цветные карточки
  (фото + название + описание), не собранные — затемнённые силуэты с `?`;
  общий счётчик «Собрано N из M».

---

## 3. Модель данных

### Новые таблицы

```python
class Treasure(Base):
    __tablename__ = "treasures"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    image_path = Column(String, default="")
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)


class UserTreasure(Base):
    __tablename__ = "user_treasures"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    treasure_id = Column(Integer, ForeignKey("treasures.id", ondelete="CASCADE"), nullable=False)
    acquired_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    UniqueConstraint("user_id", "treasure_id")
```

### Применяемые сквозные решения (`expansion-plan.md` → «Сквозные архитектурные решения»)
- **Время:** строковый подход (`acquired_at` — ISO-строка).
- **Идемпотентность:** повторная выдача не дублирует запись (Unique user+treasure).
- **Обратная совместимость:** новые таблицы с дефолтами, не ломают существующие.

### Миграция
- Новая ревизия, `down_revision = "b1c2d3e4f5a6"` (текущий head `expansion-plan.md`).
- Idempotent через `sa.inspect` (по образцу `b1c2d3e4f5a6`).
- Создаёт `treasures` и `user_treasures`.

---

## 4. Бизнес-логика

### `grow_service.award_treasure(db, vk_id, dragon_id)`
- Срабатывает при `dragon.rarity == 2` и наличии активного `Treasure` по FK.
- Если у пользователя уже есть это сокровище (`user_treasures`) → ничего не
  делает (idempotent).
- Иначе вставляет `UserTreasure`, возвращает `Treasure | None`.
- Ссылка: `expansion-plan.md` → «Сквозные: Идемпотентность».

### Интеграция в `complete_dragon`
- Единственная точка завершения выращивания
  (`expansion-plan.md` → Фаза 1, `_handle_crosses_check`/`complete_dragon`).
- `complete_dragon` должен вызывать `award_treasure` и возвращать сокровище
  наверх, чтобы бот мог его показать.

### Сброс / удаление (только админ)
- `reset_dragon` (`admin.py`) → удалить `user_treasures` где `treasure.dragon_id`
  совпадает.
- `delete_user_dragon` (`admin.py`) → то же.
- Игрок не имеет UI сброса — решение #31.

---

## 5. API

### Админ-CRUD сокровищ
| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/admin/treasures` | список всех сокровищ |
| GET | `/admin/dragons/{dragon_id}` | дополняется полем `treasure` (если есть) |
| POST | `/admin/dragons/{dragon_id}/treasure` | создать/обновить сокровище дракона (3 поля) |
| PUT | `/admin/treasures/{treasure_id}` | правка |
| DELETE | `/admin/treasures/{treasure_id}` | удалить |

- **Отдельная форма** `POST /admin/dragons/{id}/treasure` принимает ровно 3 поля:
  `name`, `description`, `image` (multipart). Загрузка фото через существующий
  `POST /admin/upload-image` (`expansion-plan.md` → Фаза 0).
- Сокровище может быть только у rarity=2 (валидируется на бэке).

### Коллекция (read-only)
| Метод | Путь | Возвращает |
|-------|------|------------|
| GET | `/collection/{vk_id}/treasures` | `{collected[{id,name,description,image}], total, uncollected[{id,silhouette}]}` |
| GET | `/collection/{vk_id}/legends` | индекс легендарных: `[{dragon_id,name,cover,fragments_opened,fragments_total}]` |

- `GET /collection/{vk_id}/legend/{dragon_id}` — детальный просмотр отрывков
  (без изменений, `expansion-plan.md` → Фаза 3).
- Эти эндпоинты добавляются в «Сводку всех новых эндпоинтов» `expansion-plan.md`.

---

## 6. Бот

### Финал редкого (`grow.py`, после `complete_dragon`)
Если `complete_dragon` вернул сокровище:
```python
treasure = complete_dragon(...)  # теперь возвращает Treasure | None
if treasure:
    msg += f"\n\n💎 Вы получили сокровище: {treasure.name}!\n{treasure.description}"
    if upload_image and treasure.image_path:
        filepath = os.path.join(_IMAGES, os.path.basename(treasure.image_path))
        if os.path.isfile(filepath):
            attachment = upload_image(filepath, peer_id=user.vk_id)
            send_message(msg, attachment=attachment, ...)
```

### Легендарный
Существующее приглашение легенды (`expansion-plan.md` → Фаза 3) дополняется
упоминанием Библиотеки мини-аппа.

---

## 7. Мини-апп

### Навигация — 5 вкладок (`MiniAppShell.tsx`)
*Отменяет `expansion-plan.md` Фаза 7 (3 вкладки → 5).*

```ts
const TABS = [
  { path: '/',         label: '🥚 Бестиарий' },
  { path: '/cave',     label: '💎 Пещера' },      // сокровища редких
  { path: '/library',  label: '📖 Библиотека' },   // легенды легендарных
  { path: '/nest',     label: '🐉 Гнездо' },       // эпик (бывший /cave)
  { path: '/shop',     label: '🛒 Лавка' },
];
```

### Новые страницы
- **`/cave` → `Treasures.tsx`** — единая галерея: собранные карточки
  (фото+название+описание), не собранные — силуэты с `?`; счётчик «N из M».
  Эндпоинт: `GET /collection/{vk}/treasures`.
- **`/library` → `Library.tsx`** — индекс легенд (обложка + прогресс отрывков),
  клик → детальный просмотр. Эндпоинты: `GET /collection/{vk}/legends` +
  `GET /collection/{vk}/legend/{dragon_id}`.

### Переименование эпика `/cave` → `/nest`
- `Cave.tsx` → переименовать в `Nest.tsx` (или оставить файл, сменить путь +
  label на «🐉 Гнездо»).
- `App.tsx`: роут `/cave` → перепривязать к `Treasures.tsx`; новый роут `/nest`
  → эпик-компонент.
- **⚠ Риск:** переименование ломает хардкод URL `app54663330`/`/cave` в боте и
  уведомлениях — проверить все места
  (`expansion-plan.md` → «Риски и точки внимания»).

### `DragonDetail.tsx`
Блок «📖 Легенда» → **превью** (обложка + счётчик открытых отрывков) +
ссылка «📖 Открыть в Библиотеке» → `/library`.
*Корректирует `expansion-plan.md` Фаза 7 (ветка «Легенды» в DragonDetail).*

---

## 8. Админка

- Новая вкладка/раздел **«Сокровища»** — список всех сокровищ + форма
  (фото/название/описание) с привязкой к редкому дракону.
- Форма доступна **из карточки редкого дракона** (кнопка «💎 Сокровище»).
- Поля формы: загрузка фото, название, описание — ничего больше
  (решение #28).

---

## 9. Чеклист Фазы 8

- [ ] Модели `Treasure`, `UserTreasure` + миграция (ревизия после `b1c2d3e4f5a6`).
- [ ] `grow_service.award_treasure` + вызов в `complete_dragon` (возврат `Treasure | None`).
- [ ] Сброс/удаление → удаление `user_treasures` (`reset_dragon`, `delete_user_dragon`).
- [ ] CRUD `/admin/treasures` + отдельная форма `POST /admin/dragons/{id}/treasure`.
- [ ] `GET /collection/{vk}/treasures`, `GET /collection/{vk}/legends`.
- [ ] Бот: фото + описание + название сокровища в финале редкого (`grow.py`).
- [ ] 5 вкладок в `MiniAppShell`; эпик `/cave` → `/nest`.
- [ ] `Treasures.tsx`, `Library.tsx`.
- [ ] `DragonDetail.tsx` → превью легенды со ссылкой в Библиотеку.
- [ ] Тесты: выдача idempotent; нет сокровища → только копилка; сброс удаляет;
      эндпоинты коллекции; CRUD админки; бот-сообщение с фото.

---

## 10. Валидация

```powershell
api\venv\Scripts\python.exe -m pytest api/tests bot/tests -v --tb=short
cd frontend; npx vitest run
cd api; .\venv\Scripts\python.exe -m alembic upgrade head
```

---

## 11. Перекрёстная таблица с `expansion-plan.md`

| Пункт `expansion-plan.md` | Действие Фазы 8 |
|---------------------------|-----------------|
| Решение #2 («сокровищ нет») | **Отменяется** — вводятся сокровища (#27) |
| «Что НЕ входит»: сокровища и награды за редкость | **Отменяется** |
| Фаза 7: 3 вкладки мини-аппа | **Расширяется до 5** (#33) |
| Фаза 7: ветка «Легенды» в `DragonDetail` | **Превью + ссылка** в Библиотеку (#32) |
| Решение #16 (`rarity` 1–3, rarity 4 не вводится) | **Подтверждается** |
| Фаза 1: `complete_dragon` | Расширяется вызовом `award_treasure` |
| Фаза 3: легенды легендарных | Библиотека переиспользует существующие `legend`-эндпоинты + новый `/legends` |

---

## Что НЕ входит в Фазу 8

- **Блоки выбора характера** на стадиях эпика (выбор типа питания,
  воспитательной программы, черт 2+/1−) — вырезаны в `expansion-plan.md`
  решением #14. Возвращение этой механики — возможная **Фаза 9**, обсуждается
  отдельно после Фазы 8.
- Реальные платежи, Donut, rarity 4 — остаются за пределами проекта.
