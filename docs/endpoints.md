# Endpoints

Every operation of the AniLibria API v1 spec ([`spec/openapi.json`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/spec/openapi.json),
snapshot of 2026-10-16: 71 paths, 80 operations) and the SDK method that covers it.

- **Path** is relative to the API base URL, `https://aniliberty.top/api/v1` by default.
- **Tag** is the operation's tag in the spec, as-is (the spec's tags are in Russian).
- **Auth** is `yes` when the operation declares its own bearer `security` in the spec. The spec
  also has a global bearer requirement, but the public endpoints work without a token — see
  [API notes](api-notes.md).
- **SDK method** is filled in by the PR that implements the endpoint.
- **Phase** is the step in [`ROADMAP.md`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/ROADMAP.md)
  that implements the endpoint.

| Method | Path | Tag | Description | Auth | SDK method | Phase |
|---|---|---|---|---|---|---|
| `GET` | `/app/search/releases` | Приложение.Поиск | Quick release search |  | `client.app.search_releases()` | 1.6 |
| `GET` | `/app/status` | Приложение.Статус | API status |  | `client.app.status()` | 1.1 |
| `GET` | `/anime/catalog/releases` | Аниме.Каталог | Catalog releases with filters (query string, paginated) |  | `client.catalog.releases()`, `client.catalog.iter_releases()` | 2.2 |
| `POST` | `/anime/catalog/releases` | Аниме.Каталог | Catalog releases with filters (JSON body, paginated) |  | — (same as `GET`; the SDK uses `GET`) | 2.2 |
| `GET` | `/anime/catalog/references/age-ratings` | Аниме.Каталог.Справочники | Catalog reference: age ratings |  | `client.catalog.references.age_ratings()` | 2.1 |
| `GET` | `/anime/catalog/references/genres` | Аниме.Каталог.Справочники | Catalog reference: genres |  | `client.catalog.references.genres()` | 2.1 |
| `GET` | `/anime/catalog/references/production-statuses` | Аниме.Каталог.Справочники | Catalog reference: production (dubbing) statuses |  | `client.catalog.references.production_statuses()` | 2.1 |
| `GET` | `/anime/catalog/references/publish-statuses` | Аниме.Каталог.Справочники | Catalog reference: publish (airing) statuses |  | `client.catalog.references.publish_statuses()` | 2.1 |
| `GET` | `/anime/catalog/references/seasons` | Аниме.Каталог.Справочники | Catalog reference: seasons |  | `client.catalog.references.seasons()` | 2.1 |
| `GET` | `/anime/catalog/references/sorting` | Аниме.Каталог.Справочники | Catalog reference: sorting options |  | `client.catalog.references.sorting()` | 2.1 |
| `GET` | `/anime/catalog/references/types` | Аниме.Каталог.Справочники | Catalog reference: release types |  | `client.catalog.references.types()` | 2.1 |
| `GET` | `/anime/catalog/references/years` | Аниме.Каталог.Справочники | Catalog reference: years |  | `client.catalog.references.years()` | 2.1 |
| `GET` | `/anime/franchises` | Аниме.Франшизы | All franchises |  | `client.franchises.list()` | 3.3 |
| `GET` | `/anime/franchises/random` | Аниме.Франшизы | Random franchises |  | `client.franchises.random()` | 3.3 |
| `GET` | `/anime/franchises/release/{releaseId}` | Аниме.Франшизы | Franchises a release belongs to |  | `client.franchises.for_release()` | 3.3 |
| `GET` | `/anime/franchises/{franchiseId}` | Аниме.Франшизы | A single franchise |  | `client.franchises.get()` | 3.3 |
| `GET` | `/anime/genres` | Аниме.Жанры | All genres |  | `client.genres.list()` | 3.2 |
| `GET` | `/anime/genres/random` | Аниме.Жанры | Random genres |  | `client.genres.random()` | 3.2 |
| `GET` | `/anime/genres/{genreId}` | Аниме.Жанры | A single genre |  | `client.genres.get()` | 3.2 |
| `GET` | `/anime/genres/{genreId}/releases` | Аниме.Жанры | Releases of a genre (paginated) |  | `client.genres.releases()`, `client.genres.iter_releases()` | 3.2 |
| `GET` | `/anime/releases/latest` | Аниме.Релизы | Latest releases, each with its latest episode |  | `client.releases.latest()` | 1.4 |
| `GET` | `/anime/releases/list` | Аниме.Релизы | Releases by a list of IDs/aliases (paginated) |  | `client.releases.list()`, `client.releases.iter_list()` | 1.4 |
| `GET` | `/anime/releases/random` | Аниме.Релизы | Random releases |  | `client.releases.random()` | 1.4 |
| `GET` | `/anime/releases/recommended` | Аниме.Релизы | Recommended releases |  | `client.releases.recommended()` | 1.4 |
| `GET` | `/anime/releases/{idOrAlias}` | Аниме.Релизы | A single release by ID or alias |  | `client.releases.get()` | 1.4 |
| `GET` | `/anime/releases/{idOrAlias}/episodes/timecodes` | Аниме.Релизы | User's watch timecodes for a release's episodes | yes |  | 4.6 |
| `GET` | `/anime/releases/{idOrAlias}/members` | Аниме.Релизы | Team members who worked on a release |  | `client.releases.members()` | 1.4 |
| `GET` | `/anime/releases/episodes/{releaseEpisodeId}` | Аниме.Релизы.Эпизоды | A single episode (HLS links) |  | `client.episodes.get()` | 1.5 |
| `GET` | `/anime/releases/episodes/{releaseEpisodeId}/timecode` | Аниме.Релизы.Эпизоды | User's watch timecode for an episode | yes |  | 4.6 |
| `DELETE` | `/anime/releases/{releaseId}/rating` | Аниме.Релизы.Оценки | Remove the user's rating of a release | yes |  | 4.7 |
| `GET` | `/anime/releases/{releaseId}/rating` | Аниме.Релизы.Оценки | User's own rating of a release | yes |  | 4.7 |
| `POST` | `/anime/releases/{releaseId}/rating` | Аниме.Релизы.Оценки | Rate a release (score up to 10) | yes |  | 4.7 |
| `GET` | `/anime/schedule/now` | Аниме.Релизы.РасписаниеРелизов | Release schedule for today |  | `client.schedule.now()` | 3.1 |
| `GET` | `/anime/schedule/week` | Аниме.Релизы.РасписаниеРелизов | Release schedule for the current week |  | `client.schedule.week()` | 3.1 |
| `GET` | `/anime/torrents` | Аниме.Торренты | Latest torrents (paginated) |  | `client.torrents.list()`, `client.torrents.iter_list()` | 3.4 |
| `GET` | `/anime/torrents/release/{releaseId}` | Аниме.Торренты | Torrents of a release |  | `client.torrents.for_release()` | 3.4 |
| `GET` | `/anime/torrents/rss` | Аниме.Торренты | RSS feed of the latest torrents (XML) |  | `client.torrents.rss()` | 3.4 |
| `GET` | `/anime/torrents/rss/release/{releaseId}` | Аниме.Торренты | RSS feed of a release's torrents (XML) |  | `client.torrents.rss_for_release()` | 3.4 |
| `GET` | `/anime/torrents/{hashOrId}` | Аниме.Торренты | A single torrent by hash or ID |  | `client.torrents.get()` | 3.4 |
| `GET` | `/anime/torrents/{hashOrId}/file` | Аниме.Торренты | The .torrent file by hash or ID |  | `client.torrents.file()`, `client.torrents.download()` | 3.4 |
| `GET` | `/media/promotions` | Медиа.Промо | Promotional materials |  |  | 3.6 |
| `GET` | `/media/videos` | Медиа.Видеоконтент | Video content |  |  | 3.6 |
| `GET` | `/teams/` | Команды | All AniLibria teams |  | `client.teams.list()` | 3.5 |
| `GET` | `/teams/roles` | Команды | Team roles |  | `client.teams.roles()` | 3.5 |
| `GET` | `/teams/users` | Команды | Team members |  | `client.teams.users()` | 3.5 |
| `POST` | `/accounts/otp/accept` | Аккаунты.ОдноразовыеПароли | Attach the current user to an issued OTP | yes |  | 4.2 |
| `POST` | `/accounts/otp/get` | Аккаунты.ОдноразовыеПароли | Request a one-time password (OTP) |  |  | 4.2 |
| `POST` | `/accounts/otp/login` | Аккаунты.ОдноразовыеПароли | Log in with an OTP |  |  | 4.2 |
| `POST` | `/accounts/users/auth/login` | Аккаунты.Пользователи.Авторизация | Log in |  |  | 4.2 |
| `POST` | `/accounts/users/auth/logout` | Аккаунты.Пользователи.Авторизация | Log out | yes |  | 4.2 |
| `GET` | `/accounts/users/auth/social/authenticate` | Аккаунты.Пользователи.Авторизация.СоциальныеСети | Complete social-network login |  |  | 4.2 |
| `GET` | `/accounts/users/auth/social/{provider}/login` | Аккаунты.Пользователи.Авторизация.СоциальныеСети | Start social-network login |  |  | 4.2 |
| `POST` | `/accounts/users/auth/password/forget` | Аккаунты.Пользователи.Авторизация.Пароль | Request a password reset |  |  | 4.2 |
| `POST` | `/accounts/users/auth/password/reset` | Аккаунты.Пользователи.Авторизация.Пароль | Reset and set a new password |  |  | 4.2 |
| `GET` | `/accounts/users/me/collections/references/age-ratings` | Аккаунты.Пользователи.Мое.Коллекции.Справочники | Age ratings present in the user's collections | yes |  | 4.5 |
| `GET` | `/accounts/users/me/collections/references/genres` | Аккаунты.Пользователи.Мое.Коллекции.Справочники | Genres present in the user's collections | yes |  | 4.5 |
| `GET` | `/accounts/users/me/collections/references/types` | Аккаунты.Пользователи.Мое.Коллекции.Справочники | Release types present in the user's collections | yes |  | 4.5 |
| `GET` | `/accounts/users/me/collections/references/years` | Аккаунты.Пользователи.Мое.Коллекции.Справочники | Years present in the user's collections | yes |  | 4.5 |
| `DELETE` | `/accounts/users/me/collections` | Аккаунты.Пользователи.Мое.Коллекции | Remove releases from collections | yes |  | 4.5 |
| `POST` | `/accounts/users/me/collections` | Аккаунты.Пользователи.Мое.Коллекции | Add releases to collections | yes |  | 4.5 |
| `GET` | `/accounts/users/me/collections/ids` | Аккаунты.Пользователи.Мое.Коллекции | IDs of releases in the user's collections | yes |  | 4.5 |
| `GET` | `/accounts/users/me/collections/releases` | Аккаунты.Пользователи.Мое.Коллекции | Releases in a collection (query-string filters) | yes |  | 4.5 |
| `POST` | `/accounts/users/me/collections/releases` | Аккаунты.Пользователи.Мое.Коллекции | Releases in a collection (JSON-body filters) | yes |  | 4.5 |
| `GET` | `/accounts/users/me/favorites/references/age-ratings` | Аккаунты.Пользователи.Мое.Избранное.Справочники | Age ratings present in the user's favorites | yes |  | 4.4 |
| `GET` | `/accounts/users/me/favorites/references/genres` | Аккаунты.Пользователи.Мое.Избранное.Справочники | Genres present in the user's favorites | yes |  | 4.4 |
| `GET` | `/accounts/users/me/favorites/references/sorting` | Аккаунты.Пользователи.Мое.Избранное.Справочники | Sorting options for the user's favorites | yes |  | 4.4 |
| `GET` | `/accounts/users/me/favorites/references/types` | Аккаунты.Пользователи.Мое.Избранное.Справочники | Release types present in the user's favorites | yes |  | 4.4 |
| `GET` | `/accounts/users/me/favorites/references/years` | Аккаунты.Пользователи.Мое.Избранное.Справочники | Years present in the user's favorites | yes |  | 4.4 |
| `DELETE` | `/accounts/users/me/favorites` | Аккаунты.Пользователи.Мое.Избранное | Remove releases from favorites | yes |  | 4.4 |
| `POST` | `/accounts/users/me/favorites` | Аккаунты.Пользователи.Мое.Избранное | Add releases to favorites | yes |  | 4.4 |
| `GET` | `/accounts/users/me/favorites/ids` | Аккаунты.Пользователи.Мое.Избранное | IDs of releases in the user's favorites | yes |  | 4.4 |
| `GET` | `/accounts/users/me/favorites/releases` | Аккаунты.Пользователи.Мое.Избранное | Releases in the user's favorites (query-string filters) | yes |  | 4.4 |
| `POST` | `/accounts/users/me/favorites/releases` | Аккаунты.Пользователи.Мое.Избранное | Releases in the user's favorites (JSON-body filters) | yes |  | 4.4 |
| `GET` | `/accounts/users/me/profile` | Аккаунты.Пользователи.Мое.Профиль | Profile of the authenticated user | yes |  | 4.3 |
| `GET` | `/accounts/users/me/views/history` | Аккаунты.Пользователи.Мое.Просмотры | Watch history (episodes) | yes |  | 4.6 |
| `DELETE` | `/accounts/users/me/views/timecodes` | Аккаунты.Пользователи.Мое.Просмотры | Delete watch-progress timecodes | yes |  | 4.6 |
| `GET` | `/accounts/users/me/views/timecodes` | Аккаунты.Пользователи.Мое.Просмотры | Watch-progress timecodes | yes |  | 4.6 |
| `POST` | `/accounts/users/me/views/timecodes` | Аккаунты.Пользователи.Мое.Просмотры | Update watch-progress timecodes | yes |  | 4.6 |
| `GET` | `/media/manifest.xml` | Реклама.Vasts | VAST XML ad chain |  |  | out of scope (ads) |
| `GET` | `/media/vasts` | Реклама.Vasts | List of VAST ads |  |  | out of scope (ads) |
