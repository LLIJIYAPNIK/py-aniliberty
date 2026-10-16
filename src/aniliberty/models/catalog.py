"""Catalog models (spec tags ``Аниме.Каталог`` and ``Аниме.Каталог.Справочники``)."""

from __future__ import annotations

from aniliberty.models.common import ValueDescription


class SortingOption(ValueDescription[str]):
    """A way to sort the catalog, from ``client.catalog.references.sorting()``.

    ``value`` is what the catalog's ``sorting`` filter takes, e.g. ``"FRESH_AT_DESC"``.

    Attributes:
        label: Short name, in Russian, e.g. ``"Обновлены недавно"``.
    """

    label: str | None = None
