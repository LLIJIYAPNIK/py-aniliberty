"""build_query: Python arguments → the API's query-string format."""

from __future__ import annotations

import enum
from typing import Any

import pytest

from aniliberty._query import build_query


class Sorting(enum.Enum):
    FRESH = "FRESH_AT_DESC"


def test_lists_are_comma_joined_into_one_parameter() -> None:
    assert build_query({"f": {"types": ["TV", "WEB"]}, "ids": (1, 2, 3)}) == {
        "f[types]": "TV,WEB",
        "ids": "1,2,3",
    }


def test_nested_mappings_become_bracketed_keys() -> None:
    query = build_query({"f": {"years": {"from_year": 2016, "to_year": 2020}}})
    assert query == {"f[years][from_year]": "2016", "f[years][to_year]": "2020"}


def test_scalars_and_enums() -> None:
    assert build_query(
        {"page": 2, "limit": 25, "f": {"search": "Мастера меча", "sorting": Sorting.FRESH}}
    ) == {"page": "2", "limit": "25", "f[search]": "Мастера меча", "f[sorting]": "FRESH_AT_DESC"}


def test_enums_inside_lists() -> None:
    assert build_query({"f": {"sorting": [Sorting.FRESH]}}) == {"f[sorting]": "FRESH_AT_DESC"}


@pytest.mark.parametrize(
    "params",
    [
        {"page": None},
        {"f": {"genres": []}},
        {"f": {}},
        {"f": {"years": {"from_year": None}}},
        {"ids": [None]},
    ],
)
def test_empty_values_are_left_out(params: dict[str, Any]) -> None:
    assert build_query(params) == {}


def test_none_items_inside_lists_are_skipped() -> None:
    assert build_query({"ids": [1, None, 3]}) == {"ids": "1,3"}


def test_list_item_with_a_comma_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"aliases: list item 'a,b' contains a comma"):
        build_query({"aliases": ["a,b"]})


@pytest.mark.parametrize("value", [True, object(), b"bytes"])
def test_unsupported_values_are_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="unsupported query value"):
        build_query({"x": value})
