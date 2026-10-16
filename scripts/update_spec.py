"""Download the AniLibria OpenAPI spec into ``spec/openapi.json``.

Usage::

    uv run python scripts/update_spec.py
    uv run python scripts/update_spec.py --url https://<mirror>/storage/api/docs/v1?aniliberty-api-v1-docs.json

The file is written pretty-printed with sorted keys, so that re-running the script against an
unchanged spec produces no diff and a changed spec produces a readable one. After writing, the
script prints which ``METHOD /path`` operations were added or removed compared with the
previous snapshot — paste that into the ``chore(spec): update openapi snapshot`` PR.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

# The Swagger UI at https://anilibria.top/api/docs/v1 loads its spec from this URL
# (see the `url:` option of `SwaggerUIBundle(...)` in that page's HTML).
DEFAULT_URL = "https://anilibria.top/storage/api/docs/v1?aniliberty-api-v1-docs.json"
SPEC_PATH = Path(__file__).resolve().parent.parent / "spec" / "openapi.json"
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})


def fetch_spec(url: str) -> dict[str, Any]:
    """Download the spec and make sure it is an OpenAPI 3 JSON document."""
    response = httpx.get(url, timeout=60.0, follow_redirects=True)
    response.raise_for_status()
    spec = response.json()
    if not isinstance(spec, dict) or not str(spec.get("openapi", "")).startswith("3."):
        raise SystemExit(f"{url} did not return an OpenAPI 3 document")
    return spec


def operations(spec: dict[str, Any]) -> set[str]:
    """Return every operation of the spec as a ``"METHOD /path"`` string."""
    return {
        f"{method.upper()} {path}"
        for path, item in spec.get("paths", {}).items()
        for method in item
        if method in HTTP_METHODS
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL, help="spec URL (default: %(default)s)")
    args = parser.parse_args()

    spec = fetch_spec(args.url)
    old_ops: set[str] = set()
    if SPEC_PATH.exists():
        old_ops = operations(json.loads(SPEC_PATH.read_text(encoding="utf-8")))

    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    SPEC_PATH.write_text(text, encoding="utf-8", newline="\n")

    new_ops = operations(spec)
    print(f"Wrote {SPEC_PATH} (OpenAPI {spec['openapi']}, {len(new_ops)} operations)")
    for op in sorted(new_ops - old_ops):
        print(f"  + {op}")
    for op in sorted(old_ops - new_ops):
        print(f"  - {op}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
