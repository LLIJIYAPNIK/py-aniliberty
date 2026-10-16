"""Resource namespaces of ``AniLiberty`` (``client.app``, ...)."""

from aniliberty.resources.app import AppResource
from aniliberty.resources.auth import (
    AuthResource,
    OtpResource,
    PasswordResource,
    SocialAuthResource,
)
from aniliberty.resources.catalog import CatalogReferencesResource, CatalogResource
from aniliberty.resources.collections import (
    CollectionsReferencesResource,
    CollectionsResource,
)
from aniliberty.resources.episodes import EpisodesResource
from aniliberty.resources.favorites import FavoritesReferencesResource, FavoritesResource
from aniliberty.resources.franchises import FranchisesResource
from aniliberty.resources.genres import GenresResource
from aniliberty.resources.me import MeResource
from aniliberty.resources.media import MediaResource
from aniliberty.resources.releases import ReleasesResource
from aniliberty.resources.schedule import ScheduleResource
from aniliberty.resources.teams import TeamsResource
from aniliberty.resources.torrents import TorrentsResource

__all__ = [
    "AppResource",
    "AuthResource",
    "CatalogReferencesResource",
    "CatalogResource",
    "CollectionsReferencesResource",
    "CollectionsResource",
    "EpisodesResource",
    "FavoritesReferencesResource",
    "FavoritesResource",
    "FranchisesResource",
    "GenresResource",
    "MeResource",
    "MediaResource",
    "OtpResource",
    "PasswordResource",
    "ReleasesResource",
    "ScheduleResource",
    "SocialAuthResource",
    "TeamsResource",
    "TorrentsResource",
]
