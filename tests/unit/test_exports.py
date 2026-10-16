"""The package root exports everything a user needs to annotate their code."""

from __future__ import annotations

import aniliberty
import aniliberty.models


def test_every_public_model_and_literal_is_exported_from_the_root() -> None:
    # EMPTY_VALUE_AS_NONE is a validator for building your own models, not a type to import.
    missing = set(aniliberty.models.__all__) - set(aniliberty.__all__) - {"EMPTY_VALUE_AS_NONE"}

    assert not missing, f"export from aniliberty too: {sorted(missing)}"


def test_root_exports_resolve() -> None:
    for name in aniliberty.__all__:
        assert hasattr(aniliberty, name), name
