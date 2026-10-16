"""``client.episodes`` — the ``Аниме.Релизы.Эпизоды`` tag of the spec."""

from __future__ import annotations

from aniliberty.models.episode import Episode
from aniliberty.models.view import EpisodeView
from aniliberty.resources._base import BaseResource, path_segment


class EpisodesResource(BaseResource):
    """Episodes of releases, available as ``client.episodes``.

    Episode IDs come from ``Release.episodes`` (``client.releases.get()``/``list()``) or
    ``Release.latest_episode`` (``client.releases.latest()``).
    """

    ENDPOINTS = (
        ("GET", "/anime/releases/episodes/{releaseEpisodeId}"),
        ("GET", "/anime/releases/episodes/{releaseEpisodeId}/timecode"),
    )

    async def get(self, episode: str | Episode) -> Episode:
        """Get one episode, with its HLS links and its release.

        Args:
            episode: Episode ID, a UUID string such as
                ``"a159552a-9fa7-4737-867b-d22cf7115602"``, or an ``Episode`` (e.g. from
                ``Release.episodes``, to get it with its release).

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
        return await self._get(f"/anime/releases/episodes/{_episode_segment(episode)}", Episode)

    async def timecode(self, episode: str | Episode) -> EpisodeView:
        """Get the logged-in user's watch record of an episode. Needs a session.

        Records appear about a minute after ``client.me.views.save_timecodes()``; for the
        positions saved just now use ``client.me.views.timecodes()``.

        Args:
            episode: Episode ID (a UUID string), or an ``Episode``.

        Returns:
            Where the user stopped in the episode and whether they finished it.

        Raises:
            NotFoundError: The user has no record for this episode (yet), or there is no
                such episode.
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``EpisodeView``.

        Example:
            ```python
            view = await client.episodes.timecode(episode.id)
            print(view.time, view.is_watched)
            ```
        """
        return await self._get(
            f"/anime/releases/episodes/{_episode_segment(episode)}/timecode", EpisodeView
        )


def _episode_segment(episode: str | Episode) -> str:
    """The path segment of an episode given by ID or ``Episode``."""
    if isinstance(episode, Episode):
        return episode.id
    return path_segment(episode, what="episode ID")
