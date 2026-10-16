# CLAUDE.md

Инструкции для Claude Code при работе над репозиторием **py-aniliberty**.

## О проекте

Асинхронный Python SDK для публичного API AniLibria (v1): релизы, эпизоды (HLS-ссылки),
каталог с фильтрами, расписание, франшизы, жанры, торренты, команды, медиа — и, на поздних
этапах, аккаунтные эндпоинты (избранное, коллекции, таймкоды просмотра).

- Документация API (Swagger UI): `https://anilibria.top/api/docs/v1#/`
- Базовый URL API: `https://anilibria.top/api/v1` (зеркала домена существуют —
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
    base_url="https://anilibria.top/api/v1",   # дефолт; можно зеркало
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

### Предварительная карта (НЕ ПРОВЕРЕНО — составлена по памяти, сверить со спекой)

Эта карта нужна только для ориентира при планировании. **Перед реализацией любого
ресурса сверить его со `spec/openapi.json` и исправить эту таблицу**, если спека
говорит иначе. Ничего из этой таблицы не хардкодить без проверки.

| Тег (ориентировочно) | Эндпоинты (ориентировочно) | Фаза |
|---|---|---|
| App | `GET /app/status`, `GET /app/search/releases` | MVP |
| Anime: Releases | `GET /anime/releases/latest`, `/random`, `/recommended`, `/list`, `/{idOrAlias}`, `/{id}/members` | MVP |
| Anime: Episodes | `GET /anime/releases/episodes/{id}` | MVP |
| Anime: Catalog | `GET`/`POST /anime/catalog/releases`, `GET /anime/catalog/references/{genres,types,seasons,years,age-ratings,publish-statuses,production-statuses,sorting}` | MVP |
| Anime: Schedule | `GET /anime/schedule/now`, `/week` | MVP |
| Anime: Genres | `GET /anime/genres`, `/{id}`, `/random`, `/{id}/releases` | MVP |
| Anime: Franchises | `GET /anime/franchises`, `/{id}`, `/random`, `/release/{releaseId}` | MVP |
| Anime: Torrents | `GET /anime/torrents`, `/{hashOrId}`, `/{hashOrId}/file`, `/release/{releaseId}`, `/rss`, `/rss/release/{releaseId}` | MVP |
| Teams | `GET /teams`, `/teams/roles`, `/teams/users` | после MVP |
| Media | `GET /media/promotions`, `/media/videos` | после MVP |
| Accounts: Auth | `POST /accounts/users/auth/login`, `/logout`, OTP, соц. логин, сброс пароля | поздняя фаза |
| Accounts: Me | профиль, избранное, коллекции, таймкоды/история просмотра | поздняя фаза |
| Ads | VAST и т.п. | **не делаем** |

### Проверено вручную

_(пусто — заполняется по мере работы; формат как в ranobelib: что запросили, что пришло,
какой вывод, дата. Подробности — в `docs/api-notes.md`.)_

### Что НЕ проверено и требует исследования перед реализацией (не гадать)

- Точный путь до JSON-спеки за Swagger UI `/api/docs/v1` (искать `url:`/`urls:` в
  инициализаторе Swagger UI в HTML страницы).
- Формат мета-пагинации и максимальный `limit`.
- Формат массивов в query-фильтрах каталога (`f[...]`), разница между `GET` и `POST`
  `/anime/catalog/releases`.
- Форма ошибок (тело 404/422/429/5xx), есть ли `Retry-After` на 429.
- Есть ли защита от ботов (WAF/DDoS-Guard) и нужен ли браузерный `User-Agent` — из
  облачной песочницы сайт отдаёт 403 на CONNECT, с машины пользователя не проверено.
- Абсолютные или относительные URL у постеров/HLS (нужен ли префикс домена/CDN).
- Аутентификация: Bearer-токен или cookie, срок жизни, refresh.

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
  (×2 за попытку), `Retry-After` уважается на 429. Ретраятся 429, 5xx, сетевые таймауты;
  4xx (кроме 429) — нет. `sleep`/`clock` инъектируются для тестов без реального ожидания.
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
  `docs/<кратко>`, `ci/<кратко>`.
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
