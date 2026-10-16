"""Catalog models (spec tags ``Аниме.Каталог`` and ``Аниме.Каталог.Справочники``)."""

from __future__ import annotations

from typing import Literal

from aniliberty.models.common import ValueDescription


class SortingOption(ValueDescription[str]):
    """A way to sort the catalog, from ``client.catalog.references.sorting()``.

    ``value`` is what the catalog's ``sorting`` filter takes, e.g. ``"FRESH_AT_DESC"``.

    Attributes:
        label: Short name, in Russian, e.g. ``"Обновлены недавно"``.
    """

    label: str | None = None


# Values of the catalog filters, copied from the `enum:` schemas of spec/openapi.json (the
# spec-sync test in tests/unit/test_catalog_resource.py fails if they drift apart). The
# catalog references (client.catalog.references) return the same values at runtime.

ReleaseType = Literal["TV", "ONA", "WEB", "OVA", "OAD", "MOVIE", "DORAMA", "SPECIAL"]
"""Release type. Spec: ``enums.anime.releases.release.type``."""

Season = Literal["winter", "spring", "summer", "autumn"]
"""Release season. Spec: ``enums.anime.releases.release.season``."""

AgeRatingValue = Literal["R0_PLUS", "R6_PLUS", "R12_PLUS", "R16_PLUS", "R18_PLUS"]
"""Age rating. Spec: ``enums.anime.releases.release.ageRating``."""

PublishStatus = Literal["IS_ONGOING", "IS_NOT_ONGOING"]
"""Whether the anime is still airing. Spec: ``enums.anime.catalog.filter.publishStatus``."""

ProductionStatus = Literal["IS_IN_PRODUCTION", "IS_NOT_IN_PRODUCTION"]
"""Whether AniLibria is still dubbing it. Spec: ``enums.anime.catalog.filter.productionStatus``."""

CatalogSorting = Literal[
    "FRESH_AT_DESC", "FRESH_AT_ASC", "RATING_DESC", "RATING_ASC", "YEAR_DESC", "YEAR_ASC"
]
"""Catalog sort order. Spec: ``enums.anime.catalog.filter.sorting``."""
