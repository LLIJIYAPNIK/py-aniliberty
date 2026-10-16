"""Completeness of the documentation (roadmap step 5.2).

- every public name has an entry in docs/reference.md;
- every public method is shown in at least one example or guide;
- every row of docs/endpoints.md says which SDK method covers it, or why none does;
- docs/examples.md lists the same examples, with the same descriptions, as examples/README.md.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Iterator
from pathlib import Path

import aniliberty
import aniliberty.models
import aniliberty.resources
from aniliberty import AniLiberty
from aniliberty.resources._base import BaseResource

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- docs/reference.md ----------------------------------------------------------------------

_DIRECTIVE = re.compile(r"^::: (aniliberty[\w.]*)\n((?:    .*\n|\n)*)", re.MULTILINE)
_MEMBER = re.compile(r"^        - (\w+)$", re.MULTILINE)


def documented_names() -> set[str]:
    """Names rendered by docs/reference.md: ``::: aniliberty.X`` and module ``members:``."""
    names = set()
    for match in _DIRECTIVE.finditer(read(DOCS / "reference.md")):
        target, options = match.groups()
        members = _MEMBER.findall(options)
        if members:
            names.update(members)
        else:
            names.add(target.rsplit(".", 1)[-1])
    return names


def test_every_public_name_has_a_reference_entry() -> None:
    public = (
        (set(aniliberty.__all__) - {"__version__"})
        | set(aniliberty.models.__all__)
        | set(aniliberty.resources.__all__)
    )

    missing = sorted(public - documented_names())

    assert not missing, f"add these to docs/reference.md: {missing}"


# --- examples and guides --------------------------------------------------------------------

_ALIAS = re.compile(r"^\s*(\w+) = (\w+)\.((?:\w+\.)*\w+)\s*$", re.MULTILINE)


def public_methods() -> Iterator[str]:
    """``"me.favorites.add"`` and so on, for every public method reachable from a client."""

    def walk(obj: object, prefix: str) -> Iterator[str]:
        for name, value in vars(obj).items():
            if isinstance(value, BaseResource):
                path = f"{prefix}{name}"
                for method, _ in inspect.getmembers(type(value), predicate=inspect.isfunction):
                    if not method.startswith("_"):
                        yield f"{path}.{method}"
                yield from walk(value, f"{path}.")

    yield from walk(AniLiberty(), "")


def calls_in(text: str) -> str:
    """The text with simple aliases expanded: ``refs = client.catalog.references`` makes
    ``refs.genres(`` read as ``client.catalog.references.genres(``."""
    for alias, _root, path in _ALIAS.findall(text):
        text = re.sub(rf"\b{alias}\.", f"client.{path}.", text)
    return text


def test_every_public_method_is_shown_in_an_example_or_guide() -> None:
    sources = [*sorted((ROOT / "examples").glob("[0-9][0-9]_*.py"))]
    sources += [*sorted((DOCS / "guides").glob("*.md")), DOCS / "quickstart.md"]
    text = "\n".join(calls_in(read(path)) for path in sources)

    # A client may be called anything (client, tv, phone, ...): match from the namespace on.
    missing = [m for m in public_methods() if not re.search(rf"\.{re.escape(m)}\(", text)]

    assert not missing, f"show these in an example or a guide: {missing}"


# --- docs/endpoints.md ----------------------------------------------------------------------

_ROW = re.compile(r"^\| `(?P<method>[A-Z]+)` \| `(?P<path>[^`]+)` \|(?P<rest>.*)\|\s*$")


def test_every_endpoint_row_says_how_it_is_covered() -> None:
    empty = []
    for line in read(DOCS / "endpoints.md").splitlines():
        match = _ROW.match(line)
        if match:
            sdk_cell = match["rest"].split("|")[4].strip()
            if not sdk_cell:
                empty.append(f"{match['method']} {match['path']}")

    assert not empty, f"fill in the SDK method column: {empty}"


# --- docs/examples.md -----------------------------------------------------------------------

_EXAMPLE_ROW = re.compile(r"^\| \[`(\d\d_\w+\.py)`\]\([^)]*\) \| (.*) \|$", re.MULTILINE)


def test_docs_examples_page_matches_examples_readme() -> None:
    readme = dict(_EXAMPLE_ROW.findall(read(ROOT / "examples" / "README.md")))
    page = dict(_EXAMPLE_ROW.findall(read(DOCS / "examples.md")))

    assert page == readme
