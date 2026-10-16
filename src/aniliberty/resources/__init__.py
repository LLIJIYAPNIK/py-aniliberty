"""Resource namespaces of ``AniLiberty`` (``client.app``, ...)."""

from aniliberty.resources.app import AppResource
from aniliberty.resources.episodes import EpisodesResource
from aniliberty.resources.releases import ReleasesResource

__all__ = ["AppResource", "EpisodesResource", "ReleasesResource"]
