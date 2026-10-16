# CLAUDE.md

Инструкции для Claude Code при работе над репозиторием **py-aniliberty**.

## О проекте

Асинхронный Python SDK для публичного API AniLibria (v1): релизы, эпизоды (HLS-ссылки),
каталог с фильтрами, расписание, франшизы, жанры, торренты, команды, медиа — и, на поздних
этапах, аккаунтные эндпоинты (избранное, коллекции, таймкоды просмотра).

- Документация API (Swagger UI): `https://aniliberty.top/api/docs/v1#/` (то же на `anilibria.top`)
- Базовый URL API: `https://aniliberty.top/api/v1` — основной сервер по спеке и `/app/status`
  (решение пользователя 2026-10-16; `anilibria.top` работает как зеркало —
  `base_url` настраиваемый, см. ниже)

- Репозиторий: `https://github.com/LLIJIYAPNIK/py-aniliberty`
- Документация SDK (GitHub Pages): `https://llijiyapnik.github.io/py-aniliberty/`

Пакет публикуется на PyPI как `py-aniliberty` (на 2026-10-16 имя свободно —
`https://pypi.org/pypi/py-aniliberty/json` → 404), импортируется как `aniliberty`
(`from aniliberty import AniLiberty`). Репозиторий и PyPI-имя совпадают:
`LLIJIYAPNIK/py-aniliberty` — использовать его в `pyproject.toml` (`project.urls`),
`mkdocs.yml` (`site_url`, `repo_url`, `repo_name`), бейджах README и `release.yml`.

Проект — «брат» `ranobelib-python-sdk` того же автора
(`https://github.com/LLIJIYAPNIK/ranobelib-python-sdk`). Тулинг, CI, релизы, документация,
структура примеров и git workflow **повторяют его один в один**; если здесь что-то не
описано — смотреть, как сделано там, и делать так же.

Код, докстринги, комментарии, README, `examples/` и публичная документация — **на
английском** (OSS-пакет на PyPI). `CLAUDE.md`, `ROADMAP.md`, issue/PR-описания и общение с
пользователем — на русском.

## Ключевые технические решения (зафиксированы, не пересматривать без явного запроса)

| Область | Решение |
|---|---|
| Асинхронность | **только async**: `httpx.AsyncClient`, без sync-обёртки, без `asyncio.run` внутри библиотеки |
| Модели данных | pydantic v2, `model_config = ConfigDict(extra="ignore", frozen=True)` |
| Источник правды об API | OpenAPI-спека, сохранённая в репозиторий (`spec/openapi.json`), а не память модели и не догадки |
| Модели | пишутся **вручную** по спеке (не генерируются `datamodel-code-generator`) — ради читаемого публичного API и докстрингов |
| Менеджер пакетов | `uv` (никаких pip/poetry/pipenv в проекте), build-backend `uv_build` |
| Python | `>=3.11`, CI-матрица 3.11 / 3.12 / 3.13 / 3.14 |
| Авторизация | не в MVP. Аккаунтные эндпоинты — отдельная поздняя фаза (см. ROADMAP) |
| CLI | не делаем, только библиотека |
| Скачивание видео | не делаем (HLS → mp4 — задача ffmpeg, не SDK). SDK отдаёт ссылки на HLS-плейлисты; скачивание `.torrent`-файла — делаем |
| Тесты API | VCR-кассеты: `pytest-recording` + `vcrpy`, `record_mode="once"` |
| Покрытие | ≥95%, `fail_under = 95` в `pyproject.toml` + флаг в CI |
| Линт/формат | `ruff` (lint + format), `line-length = 100` |
| Типизация | `mypy --strict`, пакет с `py.typed` |
| Документация | `mkdocs-material` + `mkdocstrings[python]`, деплой на GitHub Pages через Actions |
| Релизы | GitHub Release → `release.yml` → `uv publish` через PyPI Trusted Publishing (OIDC) |
| CHANGELOG | `git-cliff` (`cliff.toml`) + `changelog.yml`, Conventional Commits |
| Retry/rate limit | ручная реализация в клиенте (семафор + пейсинг + экспоненциальный backoff, `Retry-After`), без `tenacity` — как в ranobelib |
| Логирование | стандартный `logging` (`logging.getLogger("aniliberty")`), без `print`/`rich` |
| Лицензия | MIT |
| Git workflow | одна фича — одна ветка — один PR, атомарные коммиты, merge — вручную пользователем |

## Публичный API (контракт SDK)

В отличие от ranobelib (где точка входа привязана к одному тайтлу), API AniLibria —
широкий ресурсный API. Поэтому одна точка входа, клиент `AniLiberty`, и **ресурсные
неймспейсы** как атрибуты, повторяющие теги OpenAPI-спеки:

```python
from aniliberty import AniLiberty

async with AniLiberty(
    base_url="https://aniliberty.top/api/v1",  # дефолт; можно зеркало (anilibria.top)
    timeout=30.0,
    max_concurrency=5,
    headers=None,                              # доп. заголовки поверх дефолтных (User-Agent SDK)
) as client:
    status = await client.app.status()

    latest = await client.releases.latest(limit=10)                    # list[Release]
    release = await client.releases.get("naruto")                      # id ИЛИ alias
    episode = await client.episodes.get(release.episodes[0].id)
    print(episode.hls_1080 or episode.hls_720)

    found = await client.app.search_releases("frieren")                # быстрый поиск

    page = await client.catalog.releases(                              # Page[Release]
        genres=[1, 5], types=["TV"], year_from=2020, sorting="FRESH_AT_DESC", page=1, limit=25,
    )
    async for r in client.catalog.iter_releases(genres=[1]):           # авто-пагинация
        ...

    week = await client.schedule.week()
    franchise = await client.franchises.get(...)
    torrents = await client.torrents.for_release(release.id)
    await client.torrents.download(torrents[0].hash, path="ep.torrent")
```

Правила контракта:

1. **Имена неймспейсов и методов** выводятся из тегов и путей спеки, но в питоничном виде
   (`client.releases.latest()`, а не `client.get_anime_releases_latest()`). Таблица
   «эндпоинт → метод SDK» ведётся в `docs/endpoints.md` и обновляется в каждом PR.
2. **Каждый публичный метод возвращает pydantic-модель** (или `list[...]`/`Page[...]`),
   никогда не сырой `dict`. Сырой ответ доступен только через низкоуровневый
   `client.http.request(...)` — escape hatch для эндпоинтов, ещё не покрытых SDK.
3. **Пагинация**: эндпоинты со списком страниц возвращают `Page[T]` (`items`, `page`,
   `limit`, `total`, `total_pages`, `has_next_page`) и имеют парный `iter_*()` —
   `AsyncIterator[T]`, сам листающий страницы. Точная форма мета-пагинации — из спеки,
   не угадывать.
4. **«Значение + описание»**: поля вида `{"value": "...", "description": "..."}` (тип релиза,
   сезон, возрастной рейтинг и т.п.) — общая модель `Labeled[T]`/`ValueDescription`,
   а не строки и не дублирующиеся модели на каждое поле. Проверить по спеке, что такие
   поля действительно так устроены.
5. **Параметры фильтров** принимают питоничные типы (`list[int]`, `str`/`Enum`) и сами
   сериализуются в формат query-строки, который ждёт API (массивы в `f[genres]=1,5` или
   `f[genres][]=1` — **проверить по спеке и живым запросом**, зафиксировать в
   `docs/api-notes.md`).
6. Справочники каталога (жанры, типы, сезоны, годы, сортировки, возрастные рейтинги,
   статусы) — отдельные методы `client.catalog.references.*()`; enum-ы в коде **не
   хардкодить**, если API отдаёт их справочником. Литерал/Enum в типах допустим только для
   значений, явно перечисленных в спеке (`enum:`), с комментарием-ссылкой на спеку.
7. Все методы принимают ключевые аргументы (`*` после позиционных идентификаторов).
8. Обратная совместимость: до `1.0.0` публичный API может меняться, но каждое ломающее
   изменение — `feat!:`/`BREAKING CHANGE:` в коммите и отдельная строка в PR.

## Что известно про API

### Карта эндпоинтов (проверено по `spec/openapi.json` от 2026-10-16)

Спека: OpenAPI 3.0.0, 71 путь / 80 операций / 25 тегов / 132 схемы. Теги в спеке —
по-русски, через точку. Полная таблица (метод, путь, описание, метод SDK, шаг) — в
`docs/endpoints.md`; здесь — сводка. «Шаг» — пункт `ROADMAP.md`. 🔒 — у операции в спеке
свой `security: sessionToken` (bearer).

| Тег спеки | Операции | Шаг |
|---|---|---|
| `Приложение.Статус` | `GET /app/status` | 1.1 |
| `Приложение.Поиск` | `GET /app/search/releases` (`query`) | 1.6 |
| `Аниме.Релизы` | `GET /anime/releases/latest`, `/random`, `/recommended`, `/list` (пагинация, `ids`/`aliases`), `/{idOrAlias}`, `/{idOrAlias}/members` | 1.4 |
| `Аниме.Релизы` 🔒 | `GET /anime/releases/{idOrAlias}/episodes/timecodes` | 4.6 |
| `Аниме.Релизы.Эпизоды` | `GET /anime/releases/episodes/{releaseEpisodeId}` (id — UUID-строка) | 1.5 |
| `Аниме.Релизы.Эпизоды` 🔒 | `GET /anime/releases/episodes/{releaseEpisodeId}/timecode` | 4.6 |
| `Аниме.Релизы.Оценки` 🔒 | `GET`/`POST`/`DELETE /anime/releases/{releaseId}/rating` | 4.7 |
| `Аниме.Каталог` | `GET`/`POST /anime/catalog/releases` (пагинация) | 2.2 |
| `Аниме.Каталог.Справочники` | `GET /anime/catalog/references/{age-ratings,genres,production-statuses,publish-statuses,seasons,sorting,types,years}` | 2.1 |
| `Аниме.Релизы.РасписаниеРелизов` | `GET /anime/schedule/now`, `/week` | 3.1 |
| `Аниме.Жанры` | `GET /anime/genres`, `/{genreId}`, `/random`, `/{genreId}/releases` (пагинация) | 3.2 |
| `Аниме.Франшизы` | `GET /anime/franchises`, `/{franchiseId}`, `/random`, `/release/{releaseId}` | 3.3 |
| `Аниме.Торренты` | `GET /anime/torrents` (пагинация), `/{hashOrId}`, `/{hashOrId}/file`, `/release/{releaseId}`, `/rss`, `/rss/release/{releaseId}` (RSS — XML) | 3.4 |
| `Команды` | `GET /teams/` (со слэшем в спеке), `/teams/roles`, `/teams/users` | 3.5 |
| `Медиа.Промо`, `Медиа.Видеоконтент` | `GET /media/promotions`, `/media/videos` | 3.6 |
| `Аккаунты.ОдноразовыеПароли` | `POST /accounts/otp/get`, `/otp/login`, `/otp/accept` 🔒 | 4.2 |
| `Аккаунты.Пользователи.Авторизация[.СоциальныеСети/.Пароль]` | `POST /accounts/users/auth/login`, `/logout` 🔒; `GET .../social/{provider}/login`, `.../social/authenticate`; `POST .../password/forget`, `.../password/reset` | 4.2 |
| `Аккаунты.Пользователи.Мое.Профиль` 🔒 | `GET /accounts/users/me/profile` | 4.3 |
| `Аккаунты.Пользователи.Мое.Избранное[.Справочники]` 🔒 | `GET .../me/favorites/ids`, `GET`/`POST .../favorites/releases`, `POST`/`DELETE .../me/favorites`, `GET .../favorites/references/{age-ratings,genres,sorting,types,years}` | 4.4 |
| `Аккаунты.Пользователи.Мое.Коллекции[.Справочники]` 🔒 | `GET .../me/collections/ids`, `GET`/`POST .../collections/releases`, `POST`/`DELETE .../me/collections`, `GET .../collections/references/{age-ratings,genres,types,years}` | 4.5 |
| `Аккаунты.Пользователи.Мое.Просмотры` 🔒 | `GET .../me/views/history`, `GET`/`POST`/`DELETE .../me/views/timecodes` | 4.6 |
| `Реклама.Vasts` | `GET /media/vasts`, `GET /media/manifest.xml` (лежат под `/media`!) | **не делаем** |

Количество операций по группам: приложение 2, релизы/эпизоды/оценки 12, каталог 2 +
справочники 8, расписание 2, жанры 4, франшизы 4, торренты 6, команды 3, медиа 2, реклама 2,
аккаунты 33.

### Проверено вручную

Подробности (запрос → ответ → вывод) — в `docs/api-notes.md`. Кратко, 2026-10-16, запросы
без авторизации с `python-httpx`/`curl` User-Agent:

- **Спека**: `https://aniliberty.top/storage/api/docs/v1?aniliberty-api-v1-docs.json`
  (query-строка — часть URL; это `url:` из `SwaggerUIBundle` на `/api/docs/v1`).
- **Хосты**: спека называет основным сервером `https://aniliberty.top/api/v1`;
  `GET /app/status` отдаёт `available_api_endpoints: ["https://aniliberty.top"]`.
  Оба хоста отвечают одинаково (статус, JSON-404, `/storage/...`-картинки, та же спека).
  Дефолтный `base_url` SDK — `https://aniliberty.top/api/v1`, `anilibria.top` — зеркало.
- **User-Agent/WAF**: особый UA, Referer, cookie не нужны. Всё за Cloudflare
  (`server: cloudflare`), челленджей не встречено.
- **`Accept: application/json` обязателен**: без него 404 приходит HTML-страницей Laravel,
  с ним — `{"message": "No query results for model [...]"}`. SDK шлёт этот заголовок всегда;
  тогда HTML-ответ действительно означает WAF/CDN → `AccessBlockedError`.
- **422**: `{"errors": {"<param>": ["<сообщение по-русски>", ...]}}` (как в спеке).
- **Пагинация**: `{"data": [...], "meta": {"pagination": {total, count, per_page,
  current_page, total_pages, links: {previous, next}}}}`, страницы с 1. Максимальный
  `limit` каталога — **50** (больше → 422, не обрезка). Непагинируемые списки (`latest`,
  `random`, `recommended`) — голый JSON-массив.
- **Массивы в фильтрах**: через запятую в одном параметре (`f[types]=WEB,MOVIE`,
  `ids=1,2`) — спека (`style: form, explode: false`) + живой запрос; значения одного
  фильтра объединяются по ИЛИ. Годы — `f[years][from_year]`/`f[years][to_year]`.
  `POST /anime/catalog/releases` — те же фильтры JSON-телом (живьём не вызывался).
- **«Значение + описание»**: `type`, `season`, `publish_day` (`value` — число дня недели!),
  `age_rating` — `{value, description}`; у `age_rating` ещё `label`, `is_adult` (нет в спеке).
- **URL**: картинки — относительные пути от корня сайта (`/storage/...`, резолвятся от
  origin из `base_url` — проверено на обоих хостах, не от `/api/v1`); HLS — абсолютные на `cache.libria.fun` с
  query-параметрами (`countryIso`, `isAuthorized`, ...), отдавать как есть. У постера есть
  недокументированное поле `src`.
- **Пустые «значение + описание»**: `season` бывает `{"value": null, "description": null}`
  (расписание) → такие поля аннотируются `EMPTY_VALUE_AS_NONE`. Отсутствующая картинка —
  не `null`, а объект со всеми путями `null`. Абсолютных путей картинок в выборке из 574
  объектов не встретилось.
- **Опциональность**: `required` в схемах нет вообще, `nullable` — на 13 полях, при этом
  живые `null` есть и в «не-nullable» полях (`notification`, `external_player`,
  `rutube_id`, `youtube_id`). Спеке в этом не доверять — сверять с кассетами.
- **Авторизация (по спеке)**: bearer `sessionToken`, объявлен **глобально**, но 49 операций
  его не переопределяют, а публичные эндпоинты работают без токена — глобальное требование
  считаем артефактом спеки.

### Что НЕ проверено и требует исследования перед реализацией (не гадать)

- Тело и заголовки настоящего 429. Разовая проверка 2026-10-16 (300 запросов к
  `/app/status`: 120 последовательно + пачками по 10 параллельно) 429 не вызвала, заголовков
  лимитов нет ни в одном ответе. Дальше не давили; ретраи сделаны по общему правилу
  (`Retry-After` секундами или HTTP-датой, иначе backoff). Подробности — `docs/api-notes.md`.
- Тело 5xx — не встречалось.
- Как выглядит челлендж Cloudflare (статус, заголовки) — с машины пользователя не
  воспроизводится.
- Максимальный `limit` у остальных пагинируемых/лимитируемых эндпоинтов (кроме каталога).
- Аутентификация: срок жизни токена, refresh, тела 401/403 (шаг 4.1).

Каждый пункт закрывается коротким ручным исследованием **до** продакшен-кода фичи, итог —
в `docs/api-notes.md` и в этом файле.

## Структура репозитория

```
py-aniliberty/
├── src/
│   └── aniliberty/
│       ├── __init__.py          # публичный экспорт: AniLiberty, модели, исключения, __version__
│       ├── py.typed
│       ├── client.py            # AniLiberty — фасад; держит HttpClient и ресурсы
│       ├── _http.py             # HttpClient: httpx, семафор, пейсинг, retry, маппинг ошибок
│       ├── _query.py            # сериализация фильтров/массивов в query-строку API
│       ├── pagination.py        # Page[T], iter_pages-хелпер
│       ├── exceptions.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── common.py        # ValueDescription, Image/Poster, Page meta, ...
│       │   ├── release.py
│       │   ├── episode.py
│       │   ├── catalog.py       # справочники каталога
│       │   ├── schedule.py
│       │   ├── franchise.py
│       │   ├── genre.py
│       │   ├── torrent.py
│       │   └── team.py
│       └── resources/
│           ├── __init__.py
│           ├── _base.py         # BaseResource (ссылка на HttpClient)
│           ├── app.py
│           ├── releases.py
│           ├── episodes.py
│           ├── catalog.py
│           ├── schedule.py
│           ├── genres.py
│           ├── franchises.py
│           ├── torrents.py
│           ├── teams.py
│           └── media.py
├── spec/
│   ├── openapi.json             # снапшот OpenAPI-спеки (коммитится)
│   └── README.md                # откуда и когда скачана, как обновить
├── scripts/
│   └── update_spec.py           # скачивает актуальную спеку в spec/openapi.json
├── tests/
│   ├── conftest.py
│   ├── cassettes/
│   ├── unit/
│   ├── integration/             # поверх VCR-кассет
│   └── test_spec_coverage.py    # каждый путь спеки либо реализован, либо в явном skip-листе
├── docs/
│   ├── index.md
│   ├── quickstart.md
│   ├── guides/                  # pagination.md, catalog-filters.md, errors.md, ...
│   ├── reference.md             # mkdocstrings
│   ├── endpoints.md             # таблица эндпоинт → метод SDK
│   └── api-notes.md             # находки о поведении API
├── examples/
│   ├── README.md                # индекс: файл → фича
│   ├── 01_quickstart.py
│   └── ...                      # NN_<фича>.py, см. раздел "Примеры"
├── .github/workflows/
│   ├── ci.yml
│   ├── docs.yml
│   ├── release.yml
│   └── changelog.yml
├── cliff.toml
├── mkdocs.yml
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── ROADMAP.md
├── LICENSE
└── CLAUDE.md
```

## OpenAPI-спека и покрытие эндпоинтов

- `spec/openapi.json` — снапшот, коммитится в репозиторий. Обновляется только скриптом
  `uv run python scripts/update_spec.py` и отдельным коммитом `chore(spec): update openapi
  snapshot` с кратким диффом путей в описании PR.
- `tests/test_spec_coverage.py` парсит снапшот и проверяет, что каждая пара
  `(method, path)` либо реализована (реестр в `resources/` — например атрибут
  `ENDPOINTS` на каждом ресурсе), либо явно перечислена в `NOT_IMPLEMENTED` с причиной
  (`"auth: phase 4"`, `"ads: out of scope"`). Новый эндпоинт в спеке → тест падает → это
  сигнал, а не шум.
- `docs/endpoints.md` генерировать не нужно — поддерживается вручную, но тест может
  сверять его с реестром, если это несложно.

## HTTP-клиент, rate limiting, ошибки

- `HttpClient` в `_http.py` — единственное место с сетевыми настройками:
  `max_concurrency=5`, `request_delay=0.1s`, `max_retries=3`, `retry_base_delay=1.0s`
  (×2 за попытку), `Retry-After` уважается на 429 (секунды или HTTP-дата; больше
  `max_retry_after=60s` — не ждём, сразу `RateLimitError`). 429 ретраится для любого метода,
  5xx и сетевые ошибки/таймауты — только для идемпотентных (`GET`/`HEAD`/`OPTIONS`/`PUT`/
  `DELETE`); остальные 4xx и HTML-блок — никогда. `sleep`/`clock` инъектируются для тестов
  без реального ожидания.
- Каждый JSON-запрос шлёт `Accept: application/json` — без него Laravel отдаёт ошибки
  HTML-страницей (см. `docs/api-notes.md`).
- `AniLiberty` пробрасывает только `base_url`, `timeout`, `max_concurrency`, `headers`,
  `http_client` (готовый `httpx.AsyncClient` пользователя — тогда SDK его не закрывает).
- Клиент — async context manager; повторный `__aenter__` после закрытия → понятная ошибка.
  Использование без `async with` разрешено, но с явным `await client.aclose()`.
- Исключения (`exceptions.py`):
  `AniLibertyError` (база) → `APIError` (есть `status_code`, `message`, `payload`)
  → `NotFoundError` (404), `ValidationError` (422; не путать с pydantic — экспортировать
  под этим именем, но в доке оговорить), `RateLimitError` (429 после исчерпания ретраев,
  с `retry_after`), `ServerError` (5xx), `AuthRequiredError` (401/403 JSON),
  `AccessBlockedError` (HTML-ответ вместо JSON — WAF/антибот, не ретраится);
  `TransportError` (сеть/таймаут после ретраев); `ResponseParseError` (ответ не лёг в
  модель — содержит сырой payload, чтобы пользователь не терял данные).
- Маппинг статусов в исключения — по реальным телам ошибок из `docs/api-notes.md`, не
  по догадкам.

## Модели

- Одна модель — один смысл; имена полей — питоничные `snake_case`, при расхождении с API
  — `Field(alias=...)`, `populate_by_name=True`.
- Даты → `datetime` (с таймзоной, если API её отдаёт), URL → `str` (не `HttpUrl`: API может
  отдавать относительные пути — решить после проверки; если относительные — модель
  отдаёт абсолютный URL через вычисляемое свойство, сырой путь остаётся доступен).
- Опциональность полей — строго по спеке (`nullable`/`required`), плюс правка по реальным
  кассетам, если спека врёт (зафиксировать в `docs/api-notes.md`).
- Модели неизменяемые (`frozen=True`).

## Примеры (`examples/`)

Как в ranobelib (шаг 19 там): по одному самодостаточному файлу на фичу верхнего уровня,
префикс `NN_` задаёт порядок чтения. Каждый файл:

- полностью рабочий скрипт: импорты, `async def main()`, `if __name__ == "__main__":
  asyncio.run(main())`;
- **подробно закомментирован** — не «что делает вызов», а зачем этот параметр/паттерн,
  какие нюансы и подводные камни; читается как мини-туториал;
- в конце — комментарный блок `# Expected output (real run against the live API, YYYY-MM-DD):`
  с реальным выводом;
- **прогоняется по-настоящему** против живого API перед коммитом. Не придумывать вывод.

Ориентировочный список: `01_quickstart`, `02_latest_and_random_releases`,
`03_release_details`, `04_episodes_and_hls_links`, `05_quick_search`,
`06_catalog_filters`, `07_catalog_pagination` (`Page` vs `iter_*`),
`08_catalog_references`, `09_schedule`, `10_genres`, `11_franchises`,
`12_torrents_and_download`, `13_concurrency_gather` (параллельные запросы через
`asyncio.gather`/`TaskGroup` и как SDK ограничивает конкурентность),
`14_error_handling`, `15_custom_http_client_and_mirrors`, далее — teams/media/auth.

`examples/README.md` — таблица «файл → фича» со ссылками. В основном `README.md` примеров
нет — только раздел «Examples» со ссылкой на папку и коротким quickstart.

## Документация (GitHub Pages)

- Google-style докстринги у всех публичных классов/методов, с разделами `Args`, `Returns`,
  `Raises`, `Example` (короткий async-пример).
- `mkdocs.yml` — тема material (светлая/тёмная), `mkdocstrings[python]`
  (`docstring_style: google`, `merge_init_into_class: true`), `navigation.sections`,
  `content.code.copy`, `pymdownx.superfences`, `admonition`.
- Страницы: Home (`index.md`), Quickstart, Guides (pagination, catalog filters, errors &
  retries, concurrency, using mirrors / custom httpx client), API reference
  (`reference.md`), Endpoints (`endpoints.md`), API notes (`api-notes.md`), Changelog
  (включить `CHANGELOG.md` через `pymdownx.snippets` или ссылкой).
- `docs.yml`: деплой через `actions/upload-pages-artifact` + `actions/deploy-pages`,
  `concurrency: {group: pages, cancel-in-progress: true}`, `timeout-minutes` на джобах
  (урок из инцидента в ranobelib). `mkdocs build --strict` и в CI-джобе `docs`.
- **Важно**: Pages нужно один раз включить вручную (Settings → Pages → Source: GitHub
  Actions) — Claude Code это сделать не может, только напомнить пользователю.

## Git workflow

- Одна фича — одна ветка — один PR. Ветки: `feature/<кратко>`, `fix/<кратко>`,
  `docs/<кратко>`, `ci/<кратко>`; для шагов ROADMAP — с номером шага:
  `feature/1.1-http-core`. Ответвляться можно от несмерженной ветки предыдущего шага —
  base PR = она, зависимость указать в описании (решение пользователя 2026-10-16).
- Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`, `ci:`,
  `perf:`), коммиты атомарные.
- **Никогда не мержить и не пушить в `main` напрямую.** PR оставляется пользователю на
  ревью и ручной мерж. Исключение — только `changelog.yml` (бот регенерирует
  `CHANGELOG.md` после релиза).
- Если фича зависит от несмерженного PR — спросить пользователя, от какой ветки
  продолжать, либо ответвиться от ветки зависимости и указать это в описании PR.
- Перед PR локально: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, `uv run pytest --cov`, `uv run --group docs mkdocs build --strict`.
  Не открывать PR с падающими проверками.
- Каждый PR с фичей включает: код, тесты (покрытие ≥95%), докстринги, пример в
  `examples/` (если фича пользовательская), строки в `docs/endpoints.md`, при
  необходимости — `docs/api-notes.md`, отметку в `ROADMAP.md`.

## CI (GitHub Actions)

Копия подхода ranobelib:

- `ci.yml` (`pull_request` + `push` в `main`), появляется с **первым функциональным PR**:
  `lint` (ruff check + format --check), `typecheck` (mypy), `test` (матрица 3.11–3.14,
  `pytest --cov=aniliberty --cov-fail-under=95 --record-mode=none`, Coveralls — только с
  одной ноги, через пакет `coveralls`), `build` (`uv build`), `docs`
  (`mkdocs build --strict`). `astral-sh/setup-uv` с `enable-cache: true`.
- `release.yml`: `on: release: types: [published]`, environment `pypi`,
  `permissions: id-token: write`, `uv build` + `uv publish --trusted-publishing automatic`.
  Trusted Publisher на pypi.org настраивает пользователь вручную (pending publisher можно
  завести до первого релиза).
- `changelog.yml`: на тот же релиз — `orhun/git-cliff-action`, коммит `CHANGELOG.md` в
  `main` от `github-actions[bot]`.
- Версия пакета — в `pyproject.toml` (`version = "..."`), `aniliberty.__version__` читается
  через `importlib.metadata`. Bump версии — отдельный коммит `chore: bump version to X.Y.Z`
  в PR перед релизом.

## Тестирование

- `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`).
- Тесты поверх живых ответов — VCR-кассеты `tests/cassettes/<test_name>.yaml`
  (`record_mode="once"`, перезапись только вручную `--record-mode=rewrite`). Из кассет
  вычищать заголовки авторизации и cookie (`filter_headers` в `vcr_config`).
- Unit-тесты без сети через `httpx.MockTransport`: retry/backoff (с фейковым `sleep`),
  маппинг статусов в исключения, HTML-вместо-JSON, сериализация фильтров (`_query.py`),
  пагинация `iter_*` (несколько страниц, пустая страница, последняя страница), модели на
  кривом JSON.
- Обязательно покрыть error-paths: 404, 422, 429 с ретраями и `Retry-After`, 5xx, таймаут,
  антибот-HTML.
- Покрытие ≥95% честными тестами, без массовых `# pragma: no cover`.

## Порядок работы

Пошаговый план с чекбоксами — в `ROADMAP.md`. Это ориентир, не жёсткий протокол, но не
перескакивать через незакрытые зависимости. После завершения шага — отметить его в
`ROADMAP.md` в том же PR.
