# План: Подключение VK Mini App к серверу

## 1. Суть

VK Mini App — это обычная веб-страница (React + VKUI SPA). VK открывает её
в двух режимах:
- в **WebView** внутри мобильного приложения VK;
- в **iframe** в десктопной веб-версии VK.

VK не делает магии: он просто загружает ваш URL и прокидывает в него
**параметры запуска (launch params)** — в том числе `vk_user_id` и
криптографическую подпись `sign`. Ваша страница через HTTP обращается к вашему
FastAPI, и FastAPI по подписи понимает, кто пришёл. Никаких паролей, сессий VK
или токенов пользователя для базового сценария не требуется.

## 2. Что VK передаёт при запуске

Launch params попадают в Mini App двумя способами (надёжнее использовать оба):

1. **В URL** — как query/hash параметры:
   `https://ваш-сервер.ru/?vk_user_id=12345&vk_app_id=6789&sign=AbC...&ts=1700000000&vk_language=ru&...`
2. **Через VK Bridge** — метод `VKWebAppGetLaunchParams` возвращает тот же
   набор структурированно.

Ключевые параметры:

| Параметр | Что это |
|---|---|
| `vk_user_id` | ID игрока (то, что нужно нам) |
| `vk_app_id` | ID вашего Mini App |
| `vk_is_app_user` | Установил ли игрок Mini App |
| `vk_language` | Язык (`ru`, `en`...) |
| `vk_ref` | Источник перехода (для аналитики) |
| `vk_group_id` | Группа, из которой запустили (бот живёт в группе) |
| `ts` | Unix-время запуска |
| `sign` | **HMAC-SHA256 подпись всех `vk_*` параметров** — способ отличить настоящего игрока от подделки |

## 3. Как проверяется подпись `sign` (алгоритм VK)

Это сердце всей безопасности. Алгоритм строго задокументирован VK:

1. Взять **все** параметры, ключ которых начинается с `vk_` (включая
   `vk_user_id`, `vk_app_id`, `vk_language` и т.д. — **но не `sign` и не `ts`**,
   это отдельные поля).
2. Отсортировать их по ключу в алфавитном порядке.
3. Склеить в query-строку:
   `vk_app_id=6789&vk_is_app_user=1&vk_language=ru&vk_user_id=12345`.
4. Вычислить `HMAC-SHA256` от этой строки, используя **защищённый ключ
   приложения** (protected client secret из настроек приложения на
   `vk.com/editapp`).
5. Закодировать результат в **base64url без padding** (символы `+/=`
   заменяются).
6. Сравнить с присланным `sign`. Если совпадает — параметры подлинные,
   `vk_user_id` можно доверять.

Защищённый ключ **никогда не должен попадать во фронтенд** — он живёт только на
FastAPI в `.env`.

## 4. Полный поток для проекта «Коллекция драконов»

```
┌─────────────────────────────────────────────────────────────────┐
│  VK (мобайл/веб)                                                │
│  Игрок открывает Mini App из сообщения бота или меню группы     │
└──────────────────────────────┬──────────────────────────────────┘
                               │ VK загружает ваш URL и прокидывает
                               │ launch params: vk_user_id, sign, ts...
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  React+VKUI (Mini App, браузер игрока)                          │
│                                                                 │
│  1. vkBridge.send('VKWebAppInit')                               │
│  2. params = vkBridge.send('VKWebAppGetLaunchParams')           │
│     → { vk_user_id, sign, ts, vk_app_id, ... }                 │
│  3. Для каждого запроса к API шлёт эти params в заголовке        │
│     X-VK-Sign или теле запроса                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP fetch с params + sign
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI (ваш сервер)                                           │
│                                                                 │
│  verify_launch_params(sign, vk_params, VK_APP_SECRET)           │
│  → пересчитывает HMAC-SHA256, сравнивает с sign                 │
│  → если ок: достаёт vk_user_id, выполняет запрос к SQLite       │
│  → если нет: 401                                                │
│                                                                 │
│  Важно: vk_id НЕ берётся из query — только из проверенных params│
└─────────────────────────────────────────────────────────────────┘
```

## 5. Пример проверки подписи на FastAPI (Python)

Эту функцию кладём в `api/auth.py` рядом с OAuth-кодом для админки:

```python
import hmac
import hashlib
import base64
from urllib.parse import urlencode
from config import VK_APP_SECRET  # защищённый ключ из .env


def verify_launch_params(query_params: dict) -> int | None:
    """
    Проверяет подпись launch params VK Mini App.
    Возвращает vk_user_id, если подпись верна, иначе None.
    query_params — dict всех параметров запроса (request.query_params).
    """
    if "sign" not in query_params:
        return None

    sign = query_params["sign"]

    # 1. Берём только vk_* параметры, сортируем по ключу
    vk_params = {
        k: v for k, v in query_params.items()
        if k.startswith("vk_")
    }
    sorted_params = dict(sorted(vk_params.items()))

    # 2. Склеиваем в query string
    query_string = urlencode(sorted_params)

    # 3. HMAC-SHA256 секретом приложения
    digest = hmac.new(
        VK_APP_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # 4. base64url без padding
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")

    # 5. Сравнение в constant-time (защита от timing-атак)
    if hmac.compare_digest(computed, sign):
        return int(vk_params["vk_user_id"])
    return None
```

Использование в роутах:

```python
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


@router.get("/api/collection")
async def get_collection(request: Request):
    vk_user_id = verify_launch_params(dict(request.query_params))
    if vk_user_id is None:
        raise HTTPException(status_code=401, detail="Invalid signature")
    # дальше — обычная логика, vk_user_id теперь доверенный
    return await build_collection(vk_user_id)
```

## 6. Что нужно настроить в VK (чек-лист)

1. **Зарегистрировать приложение** на `vk.com/editapp` → тип
   «Мини-приложение» (или через `dev.vk.com` → «Мои приложения»). Получите:
   - `App ID` (он же `vk_app_id`)
   - **Защищённый ключ** (protected client secret) → в `.env` как
     `VK_APP_SECRET`
   - `Сервисный ключ доступа` (service token) — пригодится для VK API

2. **Указать URL приложения** в настройках:
   - Основной URL: `https://ваш-домен.ru/` (где лежит собранная React+VKUI)
   - Для разработки — staging URL
   - Домен должен быть **HTTPS** — VK не открывает http Mini Apps в проде.

3. **Привязать к сообществу** (бот живёт в группе): в настройках Mini App →
   «Сообщество». Тогда игрок сможет открыть коллекцию из меню группы и из
   сообщения бота по ссылке `https://vk.com/app{app_id}`.

4. **Запросить права (scope)** только если нужны VK API-вызовы от имени игрока
   (фото на стену, сообщения и т.д.). Для коллекции права **не нужны** —
   достаточно launch params.

5. **Пройти модерацию**, если будете в каталоге VK. Для закрытого запуска по
   прямой ссылке — можно работать и без каталога.

## 7. Разделение двух потоков авторизации

В проекте **два разных механизма** — не путать:

| | Mini App (игрок) | Admin Panel (админ) |
|---|---|---|
| **Кто** | Любой игрок, открывший Mini App | Только владелец (whitelist по VK ID) |
| **Механизм** | Проверка подписи launch params (HMAC) | VK OAuth PKCE (`id.vk.com`) |
| **Секрет** | Protected key приложения | Client ID + Secret + PKCE |
| **Сессия** | Stateless — проверка при каждом запросе | JWT в localStorage |
| **Готовый код** | Новый (алгоритм выше) | Переиспользуется из `Учет/src/backend/auth.py` |

Админка НЕ использует launch params — она отдельная страница `/admin`,
авторизуется через полноценный OAuth. Mini App использует только launch params
— там OAuth избыточен и неудобен для игрока.

## 8. VK Bridge — что нужно на фронте

`@vkontakte/vk-bridge` — единственный «мост» между React и нативными
возможностями VK. Для коллекции понадобится минимум:

- `VKWebAppInit` — обязательный первый вызов при загрузке (сигнализирует VK,
  что апп готов).
- `VKWebAppGetLaunchParams` — надёжно получить `vk_user_id` + `sign` (лучше,
  чем парсить URL: на некоторых платформах URL-парсинг ненадёжен).
- `VKWebAppGetUserInfo` — имя и аватар игрока (для приветствия в шапке
  коллекции). Возвращает публичные данные, не требует прав.

Пример на фронте:

```ts
import vkBridge from '@vkontakte/vk-bridge';

vkBridge.send('VKWebAppInit');

const { vk_user_id, sign, ts } = await vkBridge.send('VKWebAppGetLaunchParams');

// каждый запрос к API несёт launch params
fetch(`/api/collection?${new URLSearchParams({ vk_user_id, sign, ts, /*+vk_* */ })}`);
```

## 9. Риски и нюансы

| Нюанс | Решение |
|---|---|
| **Секрет в `.env`** | Защищённый ключ только на сервере. Если утечёт — перевыпустить в `vk.com/editapp`. |
| **`ts` устаревает** | VK ставит `ts` при запуске. На долгих сессиях проверять, что `ts` не старше N минут, иначе перезапросить launch params через `VKWebAppGetLaunchParams`. |
| **CORS** | FastAPI `CORSMiddleware` должен разрешать домены VK (`*.vk.com`, ваш фронт-домен). |
| **HTTPS обязательно** | VK не откроет Mini App по http в проде. nginx + Let's Encrypt. |
| **HTTPS-сертификат и iframe** | X-Frame-Options должен разрешать `https://vk.com` (иначе VK не встроит апп в iframe). |

## 10. Резюме решения

Mini App подключается к серверу так:

1. Игрок открывает Mini App → VK загружает ваш React+VKUI и прокидывает launch
   params (`vk_user_id` + `sign` + `ts`).
2. Фронт берёт launch params через `VKWebAppGetLaunchParams` (VK Bridge) и шлёт
   их с каждым запросом к FastAPI.
3. FastAPI пересчитывает HMAC-SHA256 с защищённым ключом приложения, сверяет с
   `sign`, и только при совпадении доверяет `vk_user_id`.
4. `vk_user_id` идёт в SQLite → отдаёт коллекцию игрока.

Админка работает по другому — через готовый VK OAuth PKCE из проекта «Учет»
(whitelist по VK ID + JWT).

Это полностью соответствует обновлённому `plan.md` (разделы 4, 5, 12): vk_id
берётся из подписанных launch params, бэкенд не доверяет значению из URL.

## 11. Источники

- [Мини-приложения — Обзор (dev.vk.com)](https://dev.vk.com/ru/mini-apps/overview)
- [Параметры запуска (dev.vk.com)](https://dev.vk.com/ru/mini-apps/development/launch-params)
- [Подпись параметров запуска (dev.vk.com)](https://dev.vk.com/ru/mini-apps/development/launch-params-sign)
- [VK Bridge — VKWebAppGetLaunchParams](https://dev.vk.com/ru/bridge/get-launch-params)
- [Проверка подписи на Node.js (практический разбор алгоритма)](https://vk.com/@m0rg0t-vk-mini-apps-proverka-podpisi-i-nodejs)
- [vk-launch-params — референс-реализация проверки подписи](https://github.com/kravetsone/vk-launch-params)
