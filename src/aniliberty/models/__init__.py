"""Pydantic models of API responses."""

from aniliberty.models.app import ApiStatus, RequestInfo
from aniliberty.models.auth import AuthToken, IssuedOtp, Otp, SocialLogin, SocialProvider
from aniliberty.models.catalog import (
    AgeRatingValue,
    CatalogSorting,
    ProductionStatus,
    PublishStatus,
    ReleaseType,
    Season,
    SortingOption,
)
from aniliberty.models.common import (
    EMPTY_VALUE_AS_NONE,
    Image,
    ImageSet,
    LinkedAccount,
    ValueDescription,
)
from aniliberty.models.episode import Episode, SkipRange
from aniliberty.models.franchise import Franchise, FranchiseRelease
from aniliberty.models.genre import Genre
from aniliberty.models.media import Promotion, Video, VideoOrigin
from aniliberty.models.release import (
    AgeRating,
    ExternalRating,
    Release,
    ReleaseMember,
    ReleaseName,
    ReleaseRating,
    Sponsor,
    UserRating,
)
from aniliberty.models.schedule import ScheduledRelease, ScheduleNow
from aniliberty.models.team import Team, TeamMember, TeamRole
from aniliberty.models.torrent import Torrent, TorrentCodec, TorrentFile, TorrentMember
from aniliberty.models.user import (
    CollectionItem,
    CollectionType,
    FavoritesSorting,
    TorrentStats,
    UserProfile,
)
from aniliberty.models.view import EpisodeView, HistoryEntry, Timecode

__all__ = [
    "EMPTY_VALUE_AS_NONE",
    "AgeRating",
    "AgeRatingValue",
    "CatalogSorting",
    "CollectionItem",
    "CollectionType",
    "ApiStatus",
    "AuthToken",
    "Episode",
    "EpisodeView",
    "ExternalRating",
    "FavoritesSorting",
    "Franchise",
    "FranchiseRelease",
    "Genre",
    "HistoryEntry",
    "Image",
    "ImageSet",
    "IssuedOtp",
    "LinkedAccount",
    "Otp",
    "ProductionStatus",
    "Promotion",
    "PublishStatus",
    "Release",
    "ReleaseType",
    "ReleaseMember",
    "ReleaseName",
    "ReleaseRating",
    "RequestInfo",
    "ScheduleNow",
    "ScheduledRelease",
    "Season",
    "SkipRange",
    "SocialLogin",
    "SocialProvider",
    "SortingOption",
    "Sponsor",
    "Team",
    "TeamMember",
    "TeamRole",
    "Timecode",
    "Torrent",
    "TorrentCodec",
    "TorrentFile",
    "TorrentMember",
    "TorrentStats",
    "UserRating",
    "UserProfile",
    "ValueDescription",
    "Video",
    "VideoOrigin",
]
