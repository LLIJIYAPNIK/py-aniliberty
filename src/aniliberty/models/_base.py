"""Base class for all SDK models (not public API)."""

from pydantic import BaseModel, ConfigDict


class AniLibertyModel(BaseModel):
    """Immutable model that ignores fields the SDK doesn't know about.

    ``extra="ignore"`` keeps the SDK working when the API adds fields; ``frozen=True`` makes
    models hashable and safe to share; ``populate_by_name=True`` lets fields with an API
    ``alias`` also be set by their Python name.
    """

    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)
