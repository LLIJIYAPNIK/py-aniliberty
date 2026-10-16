# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/). Entries are generated from
[Conventional Commits](https://www.conventionalcommits.org/) messages by `cliff.toml` +
`.github/workflows/changelog.yml`, which regenerates this whole file and pushes it to
`main` whenever a GitHub Release is published — don't hand-edit released sections, fix the
underlying commit message instead and let the next release regenerate this file.

## [0.4.0] - 2026-10-16

### Added

- Send a session token from HttpClient (token, with_token, discard_cookie)
- Add client.auth and AniLiberty(token=...) / client.token
- Add client.me.profile() returning UserProfile
- Add client.me.favorites (ids, add, remove, releases, references)
- Add client.me.collections (ids, add, remove, releases, references)
- Add client.me.views, client.releases.timecodes(), client.episodes.timecode()
- Add client.releases.ratings (get, set, remove the user's own score)

### Fixed

- Take the error message from the "error" field when there is no "message"
- Map empty text/html responses by status instead of as an anti-bot page

## [0.3.0] - 2026-10-16

### Added

- Add client.schedule (now, week) and the ScheduledRelease model
- Add client.genres (list, get, random, releases, iter_releases)
- Add client.franchises (list, get, random, for_release)
- Add HttpClient.request_raw() and stream() for non-JSON responses
- Add client.torrents (list, get, for_release, file, download, RSS)
- Add client.teams (list, roles, users)
- Add client.media (promotions, videos)

## [0.2.0] - 2026-10-16

### Added

- Add client.catalog.references (genres, types, seasons, years, ratings, statuses, sorting)
- Add Literal types for catalog filter values from the spec enums
- Add client.catalog.releases() and iter_releases() with validated filters

## [0.1.0] - 2026-10-16

### Added

- Add exception hierarchy
- Add HttpClient with JSON decoding and status-to-exception mapping
- Add AniLiberty client with client.app.status()
- Retry 429/5xx/network errors with backoff, pace requests and bound concurrency
- Add max_concurrency to AniLiberty
- Add query-string serialization for list and nested filters
- Add ValueDescription and Image models with absolute image URLs
- Add Page[T] and the iterate_pages helper
- Serialize params and resolve image URLs against the client's host in resources
- Add Release, ReleaseMember and Genre models
- Add client.releases (latest, random, recommended, list, get, members)
- Add Episode model and episodes inside Release
- Add client.episodes.get()
- Add client.app.search_releases()

### Changed

- Add GitHub Actions workflow
- Build docs in CI and deploy them to GitHub Pages
- Publish to PyPI from GitHub Releases via Trusted Publishing
- Regenerate CHANGELOG.md with git-cliff when a release is published

[0.4.0]: https://github.com/LLIJIYAPNIK/py-aniliberty/compare/v0.3.0..v0.4.0
[0.3.0]: https://github.com/LLIJIYAPNIK/py-aniliberty/compare/v0.2.0..v0.3.0
[0.2.0]: https://github.com/LLIJIYAPNIK/py-aniliberty/compare/v0.1.0..v0.2.0
[0.1.0]: https://github.com/LLIJIYAPNIK/py-aniliberty/tree/v0.1.0

