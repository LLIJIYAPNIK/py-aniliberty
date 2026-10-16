"""Resource namespaces of ``AniLiberty`` (``client.app``, ...)."""

from aniliberty.resources.app import AppResource
from aniliberty.resources.releases import ReleasesResource

__all__ = ["AppResource", "ReleasesResource"]
