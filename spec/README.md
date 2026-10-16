# OpenAPI spec snapshot

`openapi.json` is a snapshot of the official AniLibria API v1 OpenAPI spec. It is the source of
truth for paths, parameters, and models in this SDK.

- **Source:** `https://aniliberty.top/storage/api/docs/v1?aniliberty-api-v1-docs.json` — the URL
  the Swagger UI at <https://aniliberty.top/api/docs/v1> loads (the `url:` option of
  `SwaggerUIBundle(...)` in that page's HTML).
- **Downloaded:** 2026-10-16. OpenAPI `3.0.0`, `info.version` `1.0.0`, 71 paths / 80 operations.
- **Format:** re-serialized with `indent=2` and sorted keys, so the file is stable between runs
  and diffs stay readable. Content is otherwise unchanged.

## Updating

```bash
uv run python scripts/update_spec.py
```

The script overwrites `openapi.json` and prints the operations added (`+`) or removed (`-`)
compared with the previous snapshot. Commit the update on its own as
`chore(spec): update openapi snapshot`, with that list in the PR description. A changed set of
operations will fail the spec-coverage test once it exists — that is the intended signal.

Use `--url` to download from a mirror (e.g. `anilibria.top`) if the main domain is unavailable.

## Known quirks

The spec is not perfectly accurate (e.g. a global bearer `security` that public endpoints do
not actually require, missing `nullable` flags, undocumented response fields). Deviations
confirmed against the live API are recorded in [`docs/api-notes.md`](../docs/api-notes.md).
