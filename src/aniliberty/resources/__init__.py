"""Resource namespaces of ``AniLiberty`` (``client.app``, ...)."""

from aniliberty.resources.app import AppResource
from aniliberty.resources.catalog import CatalogReferencesResource, CatalogResource
from aniliberty.resources.episodes import EpisodesResource
from aniliberty.resources.franchises import FranchisesResource
from aniliberty.resources.genres import GenresResource
from aniliberty.resources.releases import ReleasesResource
from aniliberty.resources.schedule import ScheduleResource
from aniliberty.resources.torrents import TorrentsResource

__all__ = [
    "AppResource",
    "CatalogReferencesResource",
    "CatalogResource",
    "EpisodesResource",
    "FranchisesResource",
    "GenresResource",
    "ReleasesResource",
    "ScheduleResource",
    "TorrentsResource",
]
