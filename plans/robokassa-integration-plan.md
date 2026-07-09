# Robokassa + Магазин: Покупка наборов драконов

## Бизнес-логика

### Модель ценообразования

1. **Базовая стоимость одного дракона** (1 яйцо / 1 PIN) — задаётся в админке, хранится в БД (`PricingConfig`)
2. **DragonSet** (набор) — создаётся через админку:
   - название, количество (int), `discount_percent` (скидка для всех), `donor_discount_percent` (скидка для дона)
3. **Расчёт цены набора**:
   - Обычный: `количество × базовая_цена × (100 − скидка_всем) / 100`
   - Дон: `количество × базовая_цена × (100 − скидка_дона) / 100`
   - Скидка дона **заменяет** обычную скидку (не суммируется)
4. **Частичная покупка** (когда драконов меньше, чем в наборе):
   - `цена_за_пин = базовая_цена × (100 − скидка_всем) / 100`
   - `частичная_цена = доступно × цена_за_пин`

---

## 1. База данных — новые / изменяемые таблицы (`api/models.py`)

### `PricingConfig` — синглтон-строка

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | PK Integer, default=1 | синглтон (проверка в коде) |
| `base_price_per_dragon` | Integer | цена в **копейках** (100₽ = 10000) |
| `updated_at` | String | ISO datetime |

### `DragonSet`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | PK autoincrement | |
| `name` | String(100) | "5 драконов" и т.п. |
| `quantity` | Integer | |
| `discount_percent` | Integer, default=0 | % скидки для всех |
| `donor_discount_percent` | Integer, default=0 | % скидки для дона (заменяет `discount_percent`) |
| `is_active` | Boolean, default=True | |
| `created_at` | String | ISO datetime |

### `PaymentOrder`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | PK autoincrement | **используется как InvId для Robokassa** |
| `vk_id` | Integer, FK → users | |
| `set_id` | Integer, FK → dragon_sets | |
| `amount_rub` | Integer | сколько реально заплатил (копейки) |
| `quantity` | Integer | сколько драконов куплено |
| `price_per_pin` | Integer | цена за 1 PIN (копейки) |
| `robokassa_inv_id` | Integer, nullable | ID транзакции от Robokassa |
| `status` | String(20) | `pending` / `success` / `fail` |
| `dragon_ids` | Text(JSON) | `[id1, id2, ...]` — назначенные драконы |
| `notified` | Boolean, default=False | отправлены ли PIN через VK |
| `created_at` | String | |
| `completed_at` | String, nullable | |

### `User` — добавить колонку

| Колонка | Тип | Описание |
|---------|-----|----------|
| `is_donor` | Boolean, default=False | выставляется внешним ботом-аналитиком |

### Примечания

- `source` на `UserDragon` **не нужен** — `PaymentOrder.dragon_ids` уже аудит
- `invoice_id` удалён — `PaymentOrder.id` используется как `InvId` Robokassa (автоинкремент, подходит)

---

## 2. Admin API — новые эндпоинты (`api/routes/admin.py`)

| Метод | Путь | Назначение |
|-------|------|------------|
| `GET` | `/admin/pricing` | получить базовую цену `{base_price_rub}` |
| `PUT` | `/admin/pricing` | обновить `{base_price_rub}` |
| `GET` | `/admin/sets` | список всех наборов |
| `POST` | `/admin/sets` | создать набор |
| `PUT` | `/admin/sets/{id}` | обновить набор |
| `DELETE` | `/admin/sets/{id}` | `is_active=False` |

---

## 3. Фронтенд админки — две новые страницы

### `/admin/shop/pricing`

- Одно поле: "Стоимость одного яйца (₽)" — ввод целого числа (рубли)
- Кнопка "Сохранить"
- Паттерн как у `FamiliesForm.tsx` (простая карточка)

### `/admin/shop/sets`

- Таблица: #, название, кол-во, скидка %, скидка дона %, активно
- Кнопка "Добавить" → модалка или отдельная форма
- Редактирование по клику на строку
- Удаление = `is_active=False`

### Боковое меню (`AdminLayout.tsx`)

```tsx
{ path: '/admin/shop/pricing', label: 'Цена яйца', icon: '💰' },
{ path: '/admin/shop/sets',    label: 'Наборы',     icon: '📦' },
```

### App.tsx routes

```tsx
<Route path="shop/pricing" element={<PricingConfig />} />
<Route path="shop/sets"    element={<DragonSets />} />
```

---

## 4. Интеграция с Robokassa — техническая спецификация

### 4.1. Учётные данные (`.env` → `config.py`)

```
ROBOKASSA_MERCHANT_LOGIN="your_login"
ROBOKASSA_PASSWORD1="password_for_payment_link"
ROBOKASSA_PASSWORD2="password_for_result_callback"
ROBOKASSA_TEST_MODE="1"
SITE_URL="https://belovolovhome.ru/dragons"
```

### 4.2. Формирование ссылки на оплату

**URL:** `https://auth.robokassa.ru/Merchant/Index.aspx` (единый для теста и боя, режим переключается `IsTest`)

**Параметры POST-формы:**

| Параметр | Значение |
|----------|----------|
| `MerchantLogin` | из конфига |
| `OutSum` | `"{total_коп/100:.2f}"` (например `"299.00"`) |
| `InvId` | `payment_order.id` (integer) |
| `Description` | `"Набор «5 драконов»"` |
| `SignatureValue` | `md5(MerchantLogin:OutSum:InvId:Shp_vk_id=vk_id:Password1)` |
| `IsTest` | `1` если тестовый режим |
| `Shp_vk_id` | `vk_id` пользователя (возвращается в ResultURL) |
| `SuccessUrl2` | `{SITE_URL}/api/payment/success?order_id={id}` |
| `SuccessUrl2Method` | `GET` |
| `FailUrl2` | `{SITE_URL}/api/payment/fail?order_id={id}` |
| `FailUrl2Method` | `GET` |
| `Culture` | `ru` |
| `Encoding` | `utf-8` |

**Подпись с `Shp_` параметрами** — согласно документации Robokassa: Shp_* сортируются по алфавиту и добавляются как `:Shp_key=value`. Итог: `md5(MerchantLogin:OutSum:InvId:Shp_vk_id=vk_id:Password1)`.

### 4.3. ResultURL (серверный callback) — `POST /api/payment/result`

**Robokassa отправляет** (UTF-8 POST):

| Параметр | Описание |
|----------|----------|
| `OutSum` | строка суммы `"299.00"` |
| `InvId` | `payment_order.id` (integer) |
| `SignatureValue` | `md5(OutSum:InvId:Shp_vk_id=vk_id:Password2)` |
| `Shp_vk_id` | пользовательский параметр (проброшен) |
| `IsTest` | `1` если тест |

**Обработка на сервере (по порядку):**

1. **Разобрать параметры**: `OutSum`, `InvId`, `SignatureValue`, `Shp_vk_id`
2. **Проверить подпись**: вычислить `md5(OutSum:InvId:Shp_vk_id=...:Password2)` и сравнить с `SignatureValue`. Не совпала → лог, ответ `HTTP 400`, не обрабатывать.
3. **Идемпотентность**: найти `PaymentOrder` по `InvId` (т.е. `id`). Если `status == "success"` → ответить `OK{InvId}`, остановиться.
4. **Найти пользователя**: сверить `vk_id` из `Shp_vk_id` и `PaymentOrder.vk_id`. Должны совпадать.
5. **Проверить сумму**: `OutSum * 100` должна примерно равняться `order.amount_rub` (погрешность 1 копейка).
6. **Обработать в транзакции БД**:
   - `order.status = "success"`, `order.completed_at = now`
   - `select_dragons(vk_id, order.quantity, db)` → список Dragon
   - `generate_pins(dragons, db)` → `{dragon_id: pin}`
   - `order.dragon_ids = json.dumps([d.id for d in dragons])`
   - Commit
7. **Отправить VK-сообщение** (вне транзакции, может упасть независимо):
   - Собрать текст с именами драконов и PIN-кодами
   - Вызвать `_notify_user(vk_id, message)` (та же функция из `admin.py`)
   - Если успех → `order.notified = True`. Если нет → `order.notified = False`, залоггировать.
8. **Ответить** `OK{InvId}` (только тело, без JSON). Этим сообщаем Robokassa, что уведомление получено.

**Сценарий отказа**: Если VK-сообщение не отправилось, `notified = False`. При следующем обращении в бота (`handle_my_pins` или `handle_shop`) бот проверяет непереданные заказы и повторяет отправку.

### 4.4. SuccessURL / FailURL — `GET /api/payment/success`, `GET /api/payment/fail`

Это пользовательские редиректы после оплаты. Получают `InvId` и `Culture` от Robokassa (через GET).

- `success`: простая HTML-страница "Оплата прошла успешно! PIN-коды придут в бота." (или редирект в VK Mini App).
- `fail`: "Оплата не прошла. Попробуйте снова в боте."

Параметр `?order_id={id}` передаётся через `SuccessUrl2`/`FailUrl2`. Найти заказ, отрендерить страницу.

---

## 5. Payment Service (`api/services/payment_service.py`)

```python
def get_base_price(db) -> int:
    """Вернуть базовую цену за дракона в копейках."""

def calc_set_price(set: DragonSet, user: User, db) -> tuple[int, int]:
    """Вернуть (полная_цена_коп, цена_за_пин_коп)."""
    base = get_base_price(db)
    discount = set.donor_discount_percent if user.is_donor else set.discount_percent
    total = set.quantity * base * (100 - discount) // 100
    price_per_pin = base * (100 - discount) // 100
    return total, price_per_pin

def count_available(vk_id: int, db) -> int:
    """
    Посчитать доступных драконов для покупки:
    - Исключить уже owned (UserDragon)
    - Исключить уже купленных-но-не-активированных (PaymentOrder.success / dragon_ids)
    - Только is_active == True
    """

def select_dragons(vk_id: int, count: int, db) -> list[Dragon]:
    """
    Выбрать `count` случайных драконов, стараясь из разных семейств:
    1. Получить всех доступных (не owned, не купленных, is_active)
    2. Сгруппировать по family_id
    3. Взять по 1 случайному из каждой семьи → разнообразный пул
    4. Перемешать разнообразный пул, взять сколько нужно
    5. Если не хватило: добить оставшимися из уже использованных семей
    6. Если всё ещё не хватает: вернуть сколько есть
    """

def generate_pins(dragons: list[Dragon], db) -> dict[int, str]:
    """Для каждого дракона без pin_code сгенерировать уникальный 5-символьный PIN (A-Z + 0-9)."""
```

### Детали выбора драконов

- Доступные = `Dragon.is_active == True` AND id NOT IN `UserDragon(user_id=vk_id).dragon_id` AND id NOT IN `PaymentOrder(vk_id=vk_id, status='success').dragon_ids`
- Алгоритм:
  1. Сгруппировать доступных по `family_id` (NULL → группа 0)
  2. Из каждой группы взять 1 случайного → первичный пул (каждый из своей семьи)
  3. Если первичный пул < `count`: из групп, где ещё есть драконы, добирать случайных
  4. Если всё ещё < `count`: вернуть всех (сколько есть)
  5. Иначе → вернуть `count` случайных из пула

---

## 6. Бот — раздел «Купить яйца» (`bot/handlers/payment.py`)

### 6.1. Общая схема взаимодействия

```
[Главное меню] → нажатие «🛒 Купить яйца»
    → handle_shop()
    → сообщение с описанием сетов
    → динамическая клавиатура: кнопка на каждый сет + «◀ Назад»

[Кнопка сета (buy_set:N)] 
    → handle_buy_set()
    → POST /api/payment/create-order
    → если успех: ссылка на Robokassa + кнопки «🔗 Оплатить» и «❌ Отменить»
    → если частично: сообщение с предложением частичной покупки
    → если ошибка: сообщение об ошибке

[Кнопка «🔗 Оплатить»] → открывается Robokassa в браузере
[Оплата прошла] → Robokassa → ResultURL → PIN-коды в VK

[Кнопка «❌ Отменить» (cancel_order:N)]
    → handle_cancel_order()
    → PaymentOrder.status = "fail"
    → возврат в магазин

[Кнопка «◀ Назад» (back_to_menu)]
    → handle_back_to_menu()
    → отправка клавиатуры по текущему состоянию (idle/growing)
```

### 6.2. FSM — изменений не требуется

Магазин не требует новых состояний. Всё работает через команды и payload-кнопки.
- Если у пользователя есть `pending`-заказ, бот на любой вход проверяет это в начале `handle_shop` и показывает кнопку отмены.
- `cancel_order` не меняет FSM-состояние — только статус заказа.

### 6.3. Сообщения бота — полные шаблоны

**Шаг 1: Показ магазина (`handle_shop`)**

```
🛒 Магазин яиц

Выбери набор для покупки:

━━━━━━━━━━━━━━━━━━━━━
📦 НАБОР «5 ДРАКОНОВ»
   5 яиц из разных семейств
   💰 Цена: 475₽ (скидка 5%)
   🏷 ~95₽ за яйцо
━━━━━━━━━━━━━━━━━━━━━
📦 НАБОР «10 ДРАКОНОВ»
   10 яиц из разных семейств
   💰 Цена: 900₽ (скидка 10%)
   🏷 ~90₽ за яйцо
━━━━━━━━━━━━━━━━━━━━━

Нажми на набор, чтобы перейти к оплате
```

(если пользователь дон — вместо «скидка X%» писать «скидка дона X%»)

**Динамическая клавиатура магазина:**

```python
def shop_keyboard(sets: list[DragonSet], user: User):
    """Сгенерировать клавиатуру: кнопка на каждый сет + назад."""
    buttons = []
    for s in sets:
        discount = s.donor_discount_percent if user.is_donor else s.discount_percent
        price = get_set_price(s, user)  # вычисленная цена
        label = f"✅ {s.name} — {price//100}₽"
        buttons.append(row((label, f"buy_set:{s.id}")))
    buttons.append(row(("◀ Назад", "back_to_menu")))
    return _keyboard(buttons)
```

**Шаг 2: Создание заказа (`handle_buy_set`) — успех**

Если API вернул `payment_url`:

```
✅ Набор «5 драконов» за 475₽

Для оплаты нажми на кнопку ниже.
После оплаты PIN-коды придут в этот чат.

Ссылка действительна 60 минут.
```

**Клавиатура после создания заказа:**

```python
def payment_keyboard(url: str, order_id: int):
    return _keyboard([
        [{
            "action": {
                "type": "open_link",
                "label": "🔗 Оплатить",
                "link": url,
            },
            "color": "primary",
        }],
        row(("❌ Отменить заказ", f"cancel_order:{order_id}")),
    ])
```

**Шаг 2б: Частичная покупка**

Если `count_available()` < `set.quantity`:

```
⚠ Внимание!

Доступно только 3 дракона из 5 в наборе.
Ты можешь купить их со скидкой пропорционально:

  3 яйца × 95₽ = 285₽

[✅ Купить 3 за 285₽]   (payload: buy_partial:1)
[◀ Назад в магазин]      (back_to_menu)
```

**Шаг 2в: Ошибка**

```
❌ К сожалению, сейчас нет доступных драконов для покупки.
Все драконы уже собраны. Загляни позже — появятся новые!
```

или

```
❌ У тебя уже есть незавершённый заказ.
Заверши или отмени его, чтобы создать новый.
```

**Шаг 3: Отмена заказа (`handle_cancel_order`)**

```
❌ Заказ отменён.
```

→ возврат в магазин (`handle_shop`)

**Шаг 4: Возврат в меню (`handle_back_to_menu`)**

→ бот отправляет клавиатуру по текущему состоянию (`idle_keyboard` или `growing_keyboard`) и приветственное сообщение

### 6.4. Команды и триггеры

| Триггер | Обработчик | Описание |
|---------|------------|----------|
| `"магазин"`, `"shop"`, `"купить"`, `"купить яйца"` | `handle_shop` | Показать магазин |
| `"мои pin"`, `"мои пин"` | `handle_my_pins` | Показать неактивированные PIN-коды |
| `buy_set:N` (payload) | `handle_buy_set` | Купить сет N |
| `buy_partial:N` (payload) | `handle_buy_set` | Купить частично сет N |
| `cancel_order:N` (payload) | `handle_cancel_order` | Отменить заказ N |
| `back_to_menu` (payload) | `handle_back_to_menu` | Вернуться в главное меню |

### 6.5. Распознавание команд (`bot/main.py` — `extract_cmd`)

```python
# Приоритет: payload → точные совпадения → ключевые слова

if "купить яйца" in t or "магазин" in t or "shop" in t or "купить" in t:
    return "shop"
if "мои pin" in t or "мои пин" in t:
    return "my_pins"
if "назад" in t or "меню" in t:
    return "back_to_menu"
```

Порядок проверки важен: `"назад"` проверять после всех специфичных команд, чтобы не перехватить `"назад в магазин"` из текста.

### 6.6. Клавиатура (`bot/keyboard.py`)

**Новые функции:**
```python
def shop_keyboard(sets: list, user) -> str   # динамическая, см. выше

def payment_keyboard(url: str, order_id: int) -> str

def partial_keyboard(set_id: int) -> str      # buy_partial + back

def cancel_keyboard(order_id: int) -> str     # отмена заказа
```

**Изменения в существующих клавиатурах:**

`idle_keyboard`:
```
[🐉 Добавить дракона]  [🛒 Купить яйца]
[🔄 Сменить дракона]   [❓ Помощь]
[📖 Мой Бестиарий]
```

`growing_keyboard`:
```
[📋 Статус]
[🔄 Сменить дракона]  [❓ Помощь]
[🛒 Купить яйца]
[📖 Мой Бестиарий]
```

`waiting_keyboard` — без изменений (пользователь в процессе выращивания, кнопка магазина может отвлекать — добавить по желанию).

### 6.7. Обработка pending-заказа

В начале `handle_shop` проверять:
```python
pending = db.query(PaymentOrder).filter(
    PaymentOrder.vk_id == user.vk_id,
    PaymentOrder.status == "pending"
).first()
if pending:
    # Показать сообщение "У вас есть незавершённый заказ"
    # + payment_keyboard(pending) с кнопкой отмены
    return
```

Также при любом входящем сообщении от пользователя (в catch-all блоке `main.py`) можно проверять наличие `pending`-заказа и напоминать о нём:
```python
# После всех cmd-проверок, если сообщение не обработано:
pending = db.query(PaymentOrder).filter(
    PaymentOrder.vk_id == user_id,
    PaymentOrder.status == "pending"
).first()
if pending and not cmd:
    # "У тебя есть незавершённый заказ. Оплати или отмени."
```

### 6.8. Обработка `my_pins`

```
🔑 Твои неактивированные PIN-коды:

📦 Заказ №3 от 05.07.2026 (Набор «5 драконов»):
  🥚 Дракон «Огненный» — PIN: AB12C
  🥚 Дракон «Ледяной» — PIN: XY34Z
  🥚 Дракон «Каменный» — PIN: 7K9M1
  🥚 Дракон «Грозовой» — PIN: QW56R
  🥚 Дракон «Теневой» — PIN: 3DF4G

Введи любой код в боте командой «дракона [PIN]», чтобы начать выращивание.
```

Если `notified=False` для какого-то заказа — сначала отправить PIN-коды в ЛС (через `_notify_user`), потом показать.

### 6.9. Диспетчеризация в главном цикле (`bot/main.py`)

```python
from bot.handlers.payment import (
    handle_shop, handle_buy_set, handle_my_pins,
    handle_cancel_order, handle_back_to_menu,
)

# В цепочке elif cmd ==:
elif cmd == "shop":
    handle_shop(user, db, send_message)
elif cmd == "my_pins":
    handle_my_pins(user, db, send_message)
elif cmd == "back_to_menu":
    handle_back_to_menu(user, db, send_message)

# Для payload-команд (проверять по префиксу cmd, как switch_to):
elif payload_cmd == "buy_set":
    handle_buy_set(user, db, send_message, set_id=payload_id)
elif payload_cmd == "buy_partial":
    handle_buy_set(user, db, send_message, set_id=payload_id, accept_partial=True)
elif payload_cmd == "cancel_order":
    handle_cancel_order(user, db, send_message, order_id=payload_id)
```

Бот читает сеты и цены напрямую из БД (не через HTTP к API), так как у них общая база.

### 6.10. Итоговый список изменений в bot/

| Файл | Изменение |
|------|-----------|
| `bot/handlers/payment.py` | **СОЗДАТЬ** — 5 функций: `handle_shop`, `handle_buy_set`, `handle_my_pins`, `handle_cancel_order`, `handle_back_to_menu` |
| `bot/keyboard.py` | **ИЗМЕНИТЬ** — новые функции `shop_keyboard`, `payment_keyboard`, `partial_keyboard`, `cancel_keyboard`. Изменить `idle_keyboard` и `growing_keyboard`. |
| `bot/main.py` | **ИЗМЕНИТЬ** — импорт обработчиков, новые условия в `extract_cmd`, диспетчеризация payload + команд |
| `bot/fsm.py` | **НЕ ТРОГАТЬ** — новых состояний не нужно |

---

## 7. Конфиг (`api/config.py`)

```python
ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN", "")
ROBOKASSA_PASSWORD1 = os.getenv("ROBOKASSA_PASSWORD1", "")
ROBOKASSA_PASSWORD2 = os.getenv("ROBOKASSA_PASSWORD2", "")
ROBOKASSA_TEST_MODE = os.getenv("ROBOKASSA_TEST_MODE", "1")
SITE_URL = os.getenv("SITE_URL", "https://belovolovhome.ru/dragons")
```

Добавить в `.env` при необходимости.

---

## 8. Полный поток данных — End to End

```
1. Админ устанавливает базовую цену + создаёт DragonSet("5 драконов", qty=5, скидка=5, скидка_дона=15)

2. Пользователь пишет "магазин" в боте
   → Бот читает БД: активные сеты + user.is_donor + PricingConfig
   → Отправляет: "🛒 Магазин\n1️⃣ 5 драконов — 475₽\n2️⃣ 10 драконов — 950₽"

3. Пользователь нажимает "Купить" на сете 1
   → Бот вызывает POST /api/payment/create-order {vk_id, set_id: 1}
   → API:
       a. Проверить нет pending-заказа
       b. count_available() → 7 драконов доступно
       c. calc_set_price() → total=47500 коп. (475₽), per_pin=9500 коп. (95₽)
       d. Создать PaymentOrder(status=pending)
       e. Собрать Robokassa URL с подписью
       f. Вернуть {payment_url}
   → Бот отправляет: "🔗 Ссылка для оплаты" + open_link button

4. Пользователь оплачивает на странице Robokassa (тестовая карта)

5. Robokassa вызывает POST /api/payment/result
   → API проверяет md5(OutSum:InvId:Shp_vk_id:Password2)
   → Находит PaymentOrder по InvId (= order.id)
   → Транзакция:
       - status = success, completed_at = now
       - select_dragons(vk_id, 5) → 5 случайных драконов
       - generate_pins(dragons) → назначает PIN-коды
       - dragon_ids = [3, 7, 12, 15, 21]
   → Отправляет VK-сообщение через _notify_user():
       "🎉 Покупка набора «5 драконов» прошла успешно!\n\n..."
   → Если VK успех: notified = True
   → Отвечает OK{InvId}

6. Пользователь получает PIN-коды в VK, вводит их вручную
   → Обычный PIN-флоу: /pin → ввести код → активация → начало выращивания
```

---

## 9. Миграции

| # | Имя | Изменения |
|---|-----|-----------|
| `0014` | `add_is_donor_to_users` | `ALTER TABLE users ADD is_donor BOOLEAN DEFAULT 0` |
| `0015` | `create_pricing_config` | новая таблица + INSERT строки по умолчанию (цена=10000 = 100₽) |
| `0016` | `create_dragon_sets` | новая таблица |
| `0017` | `create_payment_orders` | новая таблица |

---

## 10. Крайние случаи и сценарии отказа

| Сценарий | Обработка |
|----------|-----------|
| **Robokassa повторяет ResultURL** (до 5 раз) | Идемпотентно: если `PaymentOrder.status == "success"`, ответить `OK{InvId}`, без изменений |
| **VK-сообщение не отправилось** | `order.notified = False`; бот повторяет при `handle_my_pins` или при следующем сообщении |
| **Покупка того же дракона из двух сетов** | `select_dragons` исключает драконов из ВСЕХ `PaymentOrder.success.dragon_ids` этого пользователя |
| **Драконов меньше, чем в сете** | Вернуть `{error: "partial", available, partial_price}`. Бот предлагает "Купить X за Y₽" с `buy_partial` |
| **Нет доступных драконов** | `count_available()` возвращает 0 → ошибка "Все драконы уже собраны" |
| **Нет активных сетов** | `handle_shop` → "Магазин временно закрыт" |
| **Есть незавершённый заказ** | `create-order` → "У вас уже есть незавершённый заказ". Ждать или написать в поддержку. |
| **Не совпала подпись Robokassa** | Лог, ответ `HTTP 400`, не обрабатывать |
| **Shp_vk_id не совпадает с PaymentOrder.vk_id** | Ошибка безопасности, лог, ответ 400 |
| **Пользователь вводит купленный PIN повторно** | `activate_pin` возвращает False → "⚠️ Ты уже активировал этого дракона." (существующее поведение) |
| **Транзакция SQLite в ResultURL** | Использовать `db.commit()` в конце. Если что-то падает — откат всей операции. |

---

## 11. Безопасность

- `Password1` используется для формирования ссылки — только на сервере
- `Password2` используется для проверки ResultURL — никогда не раскрывается
- `Shp_vk_id` включён в подпись — подделка ломает хеш
- ResultURL не должен быть публично доступен без проверки подписи
- `VK_GROUP_TOKEN` для отправки сообщений уже в конфиге (существующий `_notify_user`)

---

## 12. Файлы — создать / изменить

| Действие | Файл | Что |
|----------|------|-----|
| **ИЗМЕНИТЬ** | `api/models.py` | +`PricingConfig`, +`DragonSet`, +`PaymentOrder`, +`User.is_donor` |
| **СОЗДАТЬ** | `api/services/payment_service.py` | логика цен, выбор драконов, генерация PIN |
| **СОЗДАТЬ** | `api/routes/payment.py` | эндпоинты Robokassa |
| **ИЗМЕНИТЬ** | `api/routes/admin.py` | CRUD цен + наборов |
| **ИЗМЕНИТЬ** | `api/main.py` | зарегистрировать `payment_router` |
| **ИЗМЕНИТЬ** | `api/config.py` | Robokassa env vars |
| **СОЗДАТЬ** | `bot/handlers/payment.py` | shop / buy / my_pins |
| **ИЗМЕНИТЬ** | `bot/main.py` | новые обработчики, команды, диспетчеризация |
| **ИЗМЕНИТЬ** | `bot/keyboard.py` | кнопка магазина |
| **СОЗДАТЬ** | `frontend/src/pages/admin/PricingConfig.tsx` | форма базовой цены |
| **СОЗДАТЬ** | `frontend/src/pages/admin/DragonSets.tsx` | CRUD наборов |
| **ИЗМЕНИТЬ** | `frontend/src/App.tsx` | новые роуты |
| **ИЗМЕНИТЬ** | `frontend/src/pages/admin/AdminLayout.tsx` | пункты меню |
| **СОЗДАТЬ** | Миграция `0014` | is_donor |
| **СОЗДАТЬ** | Миграция `0015` | pricing_config |
| **СОЗДАТЬ** | Миграция `0016` | dragon_sets |
| **СОЗДАТЬ** | Миграция `0017` | payment_orders |
| **СОЗДАТЬ** | `api/tests/test_payment_service.py` | unit-тесты |
| **СОЗДАТЬ** | `api/tests/test_payment_routes.py` | тесты маршрутов |
| **СОЗДАТЬ** | `bot/tests/test_payment_handler.py` | тесты обработчиков бота |

---

## 13. Тесты

- `test_get_base_price` — возвращает текущую из БД
- `test_calc_set_price_normal` — 5 × 10000 × (100-5)/100 = 47500
- `test_calc_set_price_donor` — 5 × 10000 × (100-15)/100 = 42500
- `test_count_available_excludes_owned`
- `test_count_available_excludes_purchased`
- `test_select_dragons_prefers_different_families`
- `test_select_dragons_fills_from_same_family` — добирает из той же семьи, если не хватило
- `test_select_dragons_fewer_available` — возвращает все доступные
- `test_generate_pins_new_and_existing`
- `test_create_order_success`
- `test_create_order_partial_rejection` — возвращает `{error: "partial"}`
- `test_create_order_partial_acceptance` — создаёт с уменьшенным количеством
- `test_robokassa_signature_payment_link` — (mock) проверить формат md5
- `test_robokassa_signature_verification` — верная подпись проходит, неверная нет
- `test_robokassa_result_callback_success` — полный поток
- `test_robokassa_result_callback_idempotent` — повторный вызов без изменений
- `test_robokassa_result_callback_signature_mismatch` — 400
- `test_handle_shop` — вывод бота с ценами (обычная / дон)
- `test_handle_shop_with_pending_order` — показывает кнопку отмены вместо выбора сета
- `test_handle_shop_no_sets` — "магазин временно закрыт"
- `test_handle_buy_set_success` — создаёт заказ, возвращает payment_url
- `test_handle_buy_set_partial` — частичная покупка, кнопка buy_partial
- `test_handle_buy_set_error` — ошибка создания заказа
- `test_handle_cancel_order` — отмена pending-заказа, возврат в магазин
- `test_handle_back_to_menu` — возврат idle/growing клавиатуры
- `test_handle_my_pins` — показывает неактивированные PIN-коды
- `test_handle_my_pins_retry` — повторная отправка при `notified=False`
- `test_shop_keyboard_dynamic` — кнопка на каждый сет + назад
- `test_payment_keyboard` — open_link + cancel
- `test_notified_flag` — сбой VK выставляет `notified=False`, повтор работает

---

## 14. Соответствие документации Robokassa (проверено)

Сверено с актуальной докой: https://docs.robokassa.ru/ru/notifications-and-redirects
и https://docs.robokassa.ru/ru/pay-interface

| Требование доки | Реализация | Статус |
|-----------------|------------|--------|
| URL оплаты `https://auth.robokassa.ru/Merchant/Index.aspx` | `ROBOKASSA_URL` в `routes/payment.py` | ✅ |
| Подпись ссылки `MerchantLogin:OutSum:InvId:Пароль#1:Shp_*` (Пароль **перед** Shp_) | `build_payment_url` | ✅ |
| Подпись ResultURL `OutSum:InvId:Пароль#2:Shp_*` | `verify_result_signature` | ✅ |
| `Shp_*` сортируются по алфавиту, регистр важен | один параметр `Shp_vk_id` | ✅ |
| Сырая строка `OutSum` для подписи (тест — 2 знака, бой — 6 знаков) | подпись считается по полученной строке; сумма сверяется через `round(float*100)` ±1 коп. | ✅ |
| Ответ ровно `OK{InvId}` | `PlainTextResponse(f"OK{inv_id}")` | ✅ |
| ResultURL приходит **GET или POST** (зависит от настроек ЛК) | `@router.api_route("/result", methods=["GET","POST"])`, читаем query + form | ✅ |
| Идемпотентность повторных ResultURL (до 5 раз) | при `status=="success"` сразу `OK{InvId}` | ✅ |
| `IsTest=1` в тестовом режиме | из `ROBOKASSA_TEST_MODE` | ✅ |

### Осознанные отклонения от исходного плана

1. **Статус дона** — берётся из существующей таблицы `DonorCache.is_don` (синхронизируется внешним ботом), а НЕ из новой колонки `User.is_donor`. Колонка `is_donor` и миграция `0014` **не создавались**.
2. **PIN** — используются существующие `Dragon.pin_code` (генерируются при создании дракона). Функция `generate_pins` **не реализована** — покупка резервирует драконов через `PaymentOrder.dragon_ids` и шлёт их готовые PIN.
3. **Подпись ссылки** — в исходном плане Пароль#1 стоял *после* `Shp_vk_id`; по живой доке это ошибка (Пароль всегда перед `Shp_*`). Исправлено.
4. **Success/Fail** — задаются в ЛК Robokassa (стандартные SuccessURL/FailURL), а НЕ через `SuccessUrl2`/`FailUrl2` в форме. Это убирает необходимость включать их в подпись ссылки (в плане это усложняло формулу). Эндпоинты `/api/payment/success` и `/api/payment/fail` реализованы как простые HTML-страницы.
5. **Префикс роутов** — фактически `/api/payment/*` и `/api/admin/*` (в плане местами `/admin/*`, `/api/payment/*`).
6. **Миграция** — одна ревизия `d4e5f6a7b8c9` (down_revision `c3d4e5f6a7b8`) создаёт 3 таблицы + сид `pricing_config`. Hash-ревизия, не номер `0015-0017`.
7. **ExpirationDate** — параметр срока действия ссылки НЕ добавлен (ссылка без ограничения). Текст «действительна 60 минут» появится только при реализации бота; при необходимости добавить `ExpirationDate` в `build_payment_url`.

### Требуется вне кода (боевой запуск)

- [ ] В «Технические настройки» магазина Robokassa указать:
  - ResultURL = `https://belovolovhome.ru/dragons/api/payment/result` (GET или POST)
  - SuccessURL = `https://belovolovhome.ru/dragons/api/payment/success`
  - FailURL = `https://belovolovhome.ru/dragons/api/payment/fail`
  - Алгоритм хэша = **MD5**
- [ ] Заполнить `.env`: `ROBOKASSA_MERCHANT_LOGIN`, `ROBOKASSA_PASSWORD1`, `ROBOKASSA_PASSWORD2`, `ROBOKASSA_TEST_MODE`, `SITE_URL`. В тесте — тестовая пара паролей (иначе ошибка 29).
- [ ] Проксировать `/dragons/api/payment/*` через nginx на API.
- [ ] Если есть фильтрация входящих — добавить IP Robokassa в белый список: `185.59.216.65`, `185.59.217.65`.
- [ ] Прогнать 1 тестовый и 1 боевой платёж (чек-лист доки).

---

## 15. Чеклист внедрения

### ✅ Сделано (фаза 1 — бэкенд)

- [x] Модели `PricingConfig`, `DragonSet`, `PaymentOrder` (`api/models.py`)
- [x] Robokassa env-переменные (`api/config.py`)
- [x] `api/services/payment_service.py`: `get_base_price`, `set_base_price`, `is_donor` (через `DonorCache`), `calc_set_price`, `count_available`, `select_dragons`
- [x] `api/routes/payment.py`: `create-order`, `result` (подпись + идемпотентность + сверка суммы/vk_id + отправка PIN в VK), `success`, `fail`
- [x] Admin CRUD (`api/routes/admin.py`): `GET/PUT /pricing`, `GET/POST/PUT/DELETE /sets`
- [x] Регистрация роутера в `api/main.py`
- [x] Миграция `d4e5f6a7b8c9` (3 таблицы + сид), применена (`stamp` + сид дефолтной цены)
- [x] Тесты: `api/tests/test_payment_service.py` (11), `api/tests/test_payment_routes.py` (20)
- [x] Полный прогон: **238 passed** (`api/tests` + `bot/tests`)

### ❌ Не сделано

**Фаза 2 — бот (`bot/`)**
- [ ] `bot/handlers/payment.py`: `handle_shop`, `handle_buy_set`, `handle_my_pins`, `handle_cancel_order`, `handle_back_to_menu`
- [ ] `bot/keyboard.py`: `shop_keyboard`, `payment_keyboard`, `partial_keyboard`, `cancel_keyboard`; кнопка «🛒 Купить яйца» в `idle_keyboard`/`growing_keyboard`
- [ ] `bot/main.py`: импорт обработчиков, распознавание команд (`shop`/`my_pins`/`back_to_menu`), диспетчеризация payload (`buy_set`/`buy_partial`/`cancel_order`)
- [ ] Напоминание о `pending`-заказе в catch-all
- [ ] Повторная отправка PIN при `notified=False`
- [ ] Тесты: `bot/tests/test_payment_handler.py`

**Фаза 3 — фронтенд админки (`frontend/`)**
- [x] `frontend/src/pages/admin/PricingConfig.tsx` (форма базовой цены)
- [x] `frontend/src/pages/admin/DragonSets.tsx` (CRUD наборов + расчёт цены/цены дона)
- [x] Роуты в `frontend/src/App.tsx` (`shop/pricing`, `shop/sets`)
- [x] Пункты меню в `frontend/src/pages/AdminLayout.tsx` (💰 Цена яйца, 📦 Наборы)
- [x] Типизация `tsc -b` проходит

**Прочее (опционально)**
- [ ] `ExpirationDate` в ссылке оплаты (срок действия)
- [ ] Настройка ЛК Robokassa + nginx + `.env` (см. раздел 14)

