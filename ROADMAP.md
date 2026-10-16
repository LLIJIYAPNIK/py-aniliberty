# ROADMAP

План реализации `py-aniliberty`. Один пункт ≈ один PR (если не сказано иное).
Отмечать `[x]` в том же PR, где пункт закрыт. Детали решений — в `CLAUDE.md`,
находки про API — в `docs/api-notes.md`.

Версии — ориентир: `0.x` пока покрыт не весь публичный API, `1.0.0` — когда покрыты все
неаккаунтные эндпоинты и публичный контракт стабилен.

---

## Фаза 0 — фундамент (`0.0.x`, не публикуется)

- [x] **0.1 Scaffolding.** `uv init --lib`, `pyproject.toml` (метаданные, classifiers,
      dependency groups `dev`/`docs`, ruff/mypy/pytest/coverage-конфиги как в ranobelib),
      `src/aniliberty/` с `__init__.py` и `py.typed`, `.python-version`, `.gitignore`,
      заготовка `README.md` (`LICENSE` — MIT — уже есть в репозитории, не трогать), пустые `tests/`, `docs/`, `examples/`.
      Без функционала, без CI.
- [x] **0.2 Снапшот OpenAPI-спеки.** Найти реальный URL JSON-спеки за Swagger UI
      `https://anilibria.top/api/docs/v1`, `scripts/update_spec.py`, `spec/openapi.json`,
      `spec/README.md`. По спеке **переписать раздел «Предварительная карта» в
      `CLAUDE.md`** на проверенную таблицу и создать `docs/endpoints.md` со всеми путями
      (колонка «метод SDK» пока пустая). Ответить на вопросы из раздела «Что НЕ проверено»
      в `CLAUDE.md`, которые можно закрыть по спеке и 3–5 живыми запросами, — итог в
      `docs/api-notes.md`.

## Фаза 1 — ядро (`0.1.0`, первый релиз на PyPI)

- [x] **1.1 HTTP-ядро + первый эндпоинт.** `_http.py` (`HttpClient`: httpx, маппинг ошибок,
      `AccessBlockedError` для HTML), `exceptions.py`, `client.py` (`AniLiberty` как async
      context manager), `resources/_base.py`, `client.app.status()`. VCR-инфраструктура
      в `conftest.py`. **Первый функциональный PR → добавить `ci.yml`.**
- [x] **1.2 Retry, пейсинг, конкурентность.** Семафор, `request_delay`, экспоненциальный
      backoff, `Retry-After`, инъекция `sleep`/`clock`, unit-тесты на `MockTransport`.
- [x] **1.3 Общие модели и пагинация.** `models/common.py` (`ValueDescription`, постер/
      изображения, абсолютные URL), `pagination.py` (`Page[T]`, хелпер для `iter_*`),
      `_query.py` (сериализация фильтров) — по формату, установленному в 0.2.
- [x] **1.4 Релизы.** `client.releases.*`: `latest`, `random`, `recommended`, `list`,
      `get(id_or_alias)`, `members` — по факту спеки. Модель `Release`.
- [x] **1.5 Эпизоды.** `client.episodes.get(...)`, модель `Episode` (HLS 480/720/1080,
      `Release.latest_episode` из `latest()` и `Release.episodes` из `get()`/`list()` —
      в 1.4 эти поля пока не разбираются;
      превью, opening/ending, длительность), эпизоды внутри `Release`.
- [x] **1.6 Быстрый поиск.** `client.app.search_releases(query)`.
- [x] **1.7 Документация.** `mkdocs.yml`, `docs/index.md`, `quickstart.md`,
      `reference.md`, `endpoints.md`, `api-notes.md` в `nav`, `docs.yml` (Pages, cancel-in-
      progress, timeouts), джоба `docs` в `ci.yml`. Напомнить пользователю включить Pages.
- [x] **1.8 Примеры 01–05** (quickstart, latest/random, детали релиза, эпизоды и HLS,
      поиск) + `examples/README.md`. Каждый прогнан против живого API.
- [x] **1.9 Публикация.** `release.yml` (Trusted Publishing), `cliff.toml` +
      `changelog.yml`, бейджи в README (PyPI, license, Python versions, CI, coverage,
      docs). Инструкция пользователю по настройке pending publisher на pypi.org и
      environment `pypi`. Bump до `0.1.0`.

## Фаза 2 — каталог и справочники (`0.2.0`)

- [x] **2.1 Справочники каталога.** `client.catalog.references.*` (жанры, типы, сезоны,
      годы, возрастные рейтинги, статусы публикации/производства, сортировки).
- [x] **2.2 Каталог с фильтрами.** `client.catalog.releases(...)` → `Page[Release]`,
      `client.catalog.iter_releases(...)` → `AsyncIterator[Release]`. Все фильтры из спеки,
      типизированные параметры. Гайд `docs/guides/catalog-filters.md`.
- [x] **2.3 Гайд по пагинации** + `docs/guides/pagination.md`.
- [x] **2.4 Примеры 06–08** (фильтры, пагинация `Page` vs `iter_*`, справочники).

## Фаза 3 — остальной публичный контент (`0.3.0`)

- [x] **3.1 Расписание.** `client.schedule.now()`, `client.schedule.week()` + пример 09.
- [x] **3.2 Жанры.** `client.genres.*` (список, `get`, `random`, релизы жанра с
      пагинацией) + пример 10.
- [x] **3.3 Франшизы.** `client.franchises.*` (список, `get`, `random`, франшиза релиза)
      + пример 11.
- [x] **3.4 Торренты.** `client.torrents.*` (список, `get`, `for_release`, RSS) и
      `download(hash_or_id, path=...)` — потоковая запись `.torrent` на диск через
      `httpx` stream (async-файловый I/O не тянуть отдельной зависимостью без нужды —
      обсудить в PR) + пример 12.
- [x] **3.5 Команды.** `client.teams.*` (команды, роли, участники).
- [x] **3.6 Медиа.** `client.media.*` (промо, видео). `GET /media/vasts` и
      `/media/manifest.xml` лежат под `/media`, но это реклама (тег `Реклама.Vasts`) — не делаем.
- [x] **3.7 Гайды и примеры 13–15**: конкурентность (`asyncio.gather`/`TaskGroup` и лимиты
      SDK), обработка ошибок, свой `httpx.AsyncClient` и зеркала.
- [x] **3.8 Тест покрытия спеки.** `tests/test_spec_coverage.py` + список
      `NOT_IMPLEMENTED` с причинами. Все неаккаунтные пути — реализованы или явно
      исключены.

## Фаза 4 — аккаунт (`0.4.0` … `0.9.0`, только после явного «да» пользователя)

- [x] **4.1 Исследование авторизации.** Схема (Bearer/cookie), время жизни токена, тела
      ошибок 401/403 — в `docs/api-notes.md`. Тестовый аккаунт даёт пользователь;
      учётные данные — только через переменные окружения, в кассетах вычищаются.
- [x] **4.2 Логин/логаут.** `client.auth.login(...)`/`logout()`, `AniLiberty(token=...)` и
      `client.token`; весь тег авторизации: `client.auth.otp.*` (вход по одноразовому коду),
      `client.auth.social.*`, `client.auth.password.*`. Защищённые методы без токена получают
      403 от API → `AuthRequiredError` (без предпроверки на клиенте). Пример — в 4.8.
- [x] **4.3 Профиль.** `client.me.profile()` → `UserProfile` (passkey — вне `repr`). Пример — в 4.8.
- [x] **4.4 Избранное.** `client.me.favorites.*`: `ids()`, `add()`/`remove()`, `releases()`/
      `iter_releases()` с фильтрами, `references.*`. Пример — в 4.8.
- [x] **4.5 Коллекции.** `client.me.collections.*`: `ids()` → `CollectionItem`,
      `add(..., to=...)`/`remove()`, `releases(collection, ...)`/`iter_releases()`,
      `references.*`. Пример — в 4.8.
- [x] **4.6 Таймкоды и история просмотра.** `client.me.views.*` (`timecodes()`,
      `save_timecodes()`, `delete_timecodes()`, `history()`/`iter_history()`),
      `client.releases.timecodes()`, `client.episodes.timecode()`. Пример — в 4.8.
- [x] **4.7 Оценки релизов.** `client.releases.ratings.get()`/`set(score=...)`/`remove()`
      → `UserRating`. Пример — в 4.8.
- [ ] **4.8 Примеры и гайд по авторизации.**

## Фаза 5 — стабилизация (`1.0.0`)

- [ ] **5.1 Ревизия публичного API** — имена, сигнатуры, единообразие `get`/`list`/`iter_*`,
      докстринги; список ломающих изменений относительно `0.x`.
- [ ] **5.2 Полнота документации** — каждая публичная сущность в reference, каждая фича
      с гайдом или примером, `endpoints.md` без пустых строк.
- [ ] **5.3 Classifier `Development Status :: 5 - Production/Stable`**, релиз `1.0.0`.

## Возможные расширения (не планируются, только по запросу)

- Простой TTL-кэш справочников в памяти.
- Хелпер выбора лучшего доступного качества HLS.
- Синхронная обёртка (противоречит решению «только async» — только по явному запросу).
- Скачивание эпизодов через ffmpeg (вне SDK — скорее пример, чем фича).

## Вне скоупа

- Рекламные эндпоинты (VAST и т.п.).
- CLI.
- Парсинг HTML сайта.
