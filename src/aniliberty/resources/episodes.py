"""``client.episodes`` — the ``Аниме.Релизы.Эпизоды`` tag of the spec."""

from __future__ import annotations

from aniliberty.models.episode import Episode
from aniliberty.resources._base import BaseResource, path_segment


class EpisodesResource(BaseResource):
    """Episodes of releases, available as ``client.episodes``.

    Episode IDs come from ``Release.episodes`` (``client.releases.get()``/``list()``) or
    ``Release.latest_episode`` (``client.releases.latest()``).
    """

    ENDPOINTS = (("GET", "/anime/releases/episodes/{releaseEpisodeId}"),)

    async def get(self, episode_id: str) -> Episode:
        """Get one episode, with its HLS links and its release.

        Args:
            episode_id: Episode ID, a UUID string such as
                ``"a159552a-9fa7-4737-867b-d22cf7115602"``.

        Returns:
            The episode, with ``release`` filled in — the release (without ``genres``) and
            all of its episodes.

        Raises:
            NotFoundError: No episode with this ID (also for IDs that aren't UUIDs).
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Episode``.

        Example:
            ```python
            release = await client.releases.get("tensei-shitara-ken-deshita-2nd-season")
            episode = await client.episodes.get(release.episodes[0].id)
            print(episode.ordinal, episode.hls_1080 or episode.hls_720)
            ```
        """
        return await self._get(
            f"/anime/releases/episodes/{path_segment(episode_id, what='episode ID')}", Episode
        )
