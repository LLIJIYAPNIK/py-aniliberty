"""Every operation of the spec snapshot is either implemented by the SDK or explicitly skipped.

"Implemented" means listed in ``ENDPOINTS`` of a resource reachable from ``AniLiberty``;
"skipped" means listed in ``NOT_IMPLEMENTED`` below, with the reason. A new operation in
``spec/openapi.json`` (after ``scripts/update_spec.py``) fails ``test_every_operation_is_covered``
— that's the signal to implement it or to add it here.

``docs/endpoints.md`` is checked against the same registry, so the table can't drift from the
code: same operations, the right auth flag, and SDK methods that exist on the resource that
declares the endpoint.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from aniliberty import AniLiberty
from aniliberty.resources._base import BaseResource

ROOT = Path(__file__).parent.parent
SPEC: dict[str, Any] = json.loads((ROOT / "spec" / "openapi.json").read_text(encoding="utf-8"))
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

Operation = tuple[str, str]

_AUTH_45 = "auth: roadmap 4.5 (collections)"
_AUTH_46 = "auth: roadmap 4.6 (timecodes and watch history)"
_AUTH_47 = "auth: roadmap 4.7 (release ratings)"
_ADS = "ads: out of scope"

NOT_IMPLEMENTED: dict[Operation, str] = {
    ("POST", "/anime/catalog/releases"): "same as GET /anime/catalog/releases, which the SDK uses",
    ("POST", "/accounts/users/me/favorites/releases"): (
        "same as GET /accounts/users/me/favorites/releases, which the SDK uses"
    ),
    # Phase 4 — account endpoints.
    ("GET", "/accounts/users/me/collections/ids"): _AUTH_45,
    ("GET", "/accounts/users/me/collections/releases"): _AUTH_45,
    ("POST", "/accounts/users/me/collections/releases"): _AUTH_45,
    ("POST", "/accounts/users/me/collections"): _AUTH_45,
    ("DELETE", "/accounts/users/me/collections"): _AUTH_45,
    ("GET", "/accounts/users/me/collections/references/age-ratings"): _AUTH_45,
    ("GET", "/accounts/users/me/collections/references/genres"): _AUTH_45,
    ("GET", "/accounts/users/me/collections/references/types"): _AUTH_45,
    ("GET", "/accounts/users/me/collections/references/years"): _AUTH_45,
    ("GET", "/accounts/users/me/views/history"): _AUTH_46,
    ("GET", "/accounts/users/me/views/timecodes"): _AUTH_46,
    ("POST", "/accounts/users/me/views/timecodes"): _AUTH_46,
    ("DELETE", "/accounts/users/me/views/timecodes"): _AUTH_46,
    ("GET", "/anime/releases/{idOrAlias}/episodes/timecodes"): _AUTH_46,
    ("GET", "/anime/releases/episodes/{releaseEpisodeId}/timecode"): _AUTH_46,
    ("GET", "/anime/releases/{releaseId}/rating"): _AUTH_47,
    ("POST", "/anime/releases/{releaseId}/rating"): _AUTH_47,
    ("DELETE", "/anime/releases/{releaseId}/rating"): _AUTH_47,
    # Ads (spec tag "Реклама.Vasts"), even though they live under /media.
    ("GET", "/media/vasts"): _ADS,
    ("GET", "/media/manifest.xml"): _ADS,
}


def spec_operations() -> dict[Operation, dict[str, Any]]:
    return {
        (method.upper(), path): operation
        for path, item in SPEC["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    }


def walk_resources(obj: object, prefix: str = "client") -> Iterator[tuple[str, BaseResource]]:
    """Yield ``(dotted name, resource)`` for every resource reachable from ``obj``."""
    for name, value in vars(obj).items():
        if isinstance(value, BaseResource):
            dotted = f"{prefix}.{name}"
            yield dotted, value
            yield from walk_resources(value, dotted)


@pytest.fixture(scope="module")
def resources() -> dict[str, BaseResource]:
    return dict(walk_resources(AniLiberty()))


@pytest.fixture(scope="module")
def implemented(resources: dict[str, BaseResource]) -> dict[Operation, str]:
    """Each implemented operation → the dotted name of the resource that declares it."""
    owners: dict[Operation, str] = {}
    for name, resource in resources.items():
        for method, path in resource.ENDPOINTS:
            operation = (method, path)
            assert operation not in owners, f"{method} {path}: in {owners[operation]} and {name}"
            owners[operation] = name
    return owners


def subclasses(cls: type) -> set[type]:
    direct = set(cls.__subclasses__())
    return direct.union(*(subclasses(c) for c in direct))


def test_every_operation_is_covered(implemented: dict[Operation, str]) -> None:
    missing = sorted(set(spec_operations()) - set(implemented) - set(NOT_IMPLEMENTED))
    assert not missing, (
        "spec operations neither implemented (a resource's ENDPOINTS) nor skipped "
        f"(NOT_IMPLEMENTED): {missing}"
    )


def test_implemented_operations_exist_in_the_spec(implemented: dict[Operation, str]) -> None:
    unknown = sorted(set(implemented) - set(spec_operations()))
    assert not unknown, f"ENDPOINTS entries not in spec/openapi.json: {unknown}"


def test_skipped_operations_exist_in_the_spec() -> None:
    stale = sorted(set(NOT_IMPLEMENTED) - set(spec_operations()))
    assert not stale, f"NOT_IMPLEMENTED entries not in spec/openapi.json: {stale}"


def test_nothing_is_both_implemented_and_skipped(implemented: dict[Operation, str]) -> None:
    both = sorted(set(implemented) & set(NOT_IMPLEMENTED))
    assert not both, f"implemented, so remove from NOT_IMPLEMENTED: {both}"


def test_every_skip_has_a_reason() -> None:
    assert all(reason.strip() for reason in NOT_IMPLEMENTED.values())


def test_every_resource_class_is_reachable_from_the_client(
    resources: dict[str, BaseResource],
) -> None:
    reachable = {type(resource) for resource in resources.values()}
    # Only the SDK's own public classes: tests define throwaway subclasses of their own, and
    # private ones (``_SessionResource``) are shared bases, not namespaces.
    sdk_classes = {
        cls
        for cls in subclasses(BaseResource)
        if cls.__module__.startswith("aniliberty.") and not cls.__name__.startswith("_")
    }
    orphans = sorted(cls.__name__ for cls in sdk_classes - reachable)
    assert not orphans, f"resource classes not attached to AniLiberty: {orphans}"


# --- docs/endpoints.md ---------------------------------------------------------------------

_ROW = re.compile(r"^\| `(?P<method>[A-Z]+)` \| `(?P<path>[^`]+)` \|(?P<rest>.*)\|\s*$")
_SDK_METHOD = re.compile(r"`(client(?:\.\w+)+)\(\)`")


def endpoint_rows() -> dict[Operation, list[str]]:
    """Rows of the table in docs/endpoints.md: operation → the cells after the path."""
    rows: dict[Operation, list[str]] = {}
    text = (ROOT / "docs" / "endpoints.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        match = _ROW.match(line)
        if match is None:
            continue
        operation = (match["method"], match["path"])
        assert operation not in rows, f"{operation} is listed twice in docs/endpoints.md"
        # Tag | Description | Auth | SDK method | Phase
        rows[operation] = [cell.strip() for cell in match["rest"].split("|")]
    return rows


def test_endpoints_doc_lists_every_operation() -> None:
    rows, spec = set(endpoint_rows()), set(spec_operations())
    assert not sorted(spec - rows), f"missing from docs/endpoints.md: {sorted(spec - rows)}"
    assert not sorted(rows - spec), f"not in the spec: {sorted(rows - spec)}"


def test_endpoints_doc_auth_column_follows_the_spec() -> None:
    operations = spec_operations()
    for operation, (_tag, _description, auth, _sdk, _phase) in endpoint_rows().items():
        has_own_security = bool(operations[operation].get("security"))
        assert (auth == "yes") == has_own_security, f"{operation}: Auth column is {auth!r}"


def test_endpoints_doc_sdk_methods_match_the_code(
    resources: dict[str, BaseResource], implemented: dict[Operation, str]
) -> None:
    for operation, (_tag, _description, _auth, sdk, _phase) in endpoint_rows().items():
        names = _SDK_METHOD.findall(sdk)
        if operation not in implemented:
            assert not names, f"{operation} is not implemented, but the doc names {names}"
            continue
        assert names, f"{operation} is implemented by {implemented[operation]}, doc has no method"
        for name in names:
            owner, _, method = name.rpartition(".")
            assert owner == implemented[operation], (
                f"{operation}: doc names {name}(), but the endpoint is declared by "
                f"{implemented[operation]}"
            )
            assert callable(getattr(resources[owner], method, None)), f"{name}() doesn't exist"
