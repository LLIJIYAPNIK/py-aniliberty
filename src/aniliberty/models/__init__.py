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
from aniliberty.models.common import EMPTY_VALUE_AS_NONE, Image, ImageSet, ValueDescription
from aniliberty.models.episode import Episode, SkipRange
from aniliberty.models.franchise import Franchise, FranchiseRelease
from aniliberty.models.genre import Genre
from aniliberty.models.media import Promotion, Video, VideoOrigin
from aniliberty.models.release import (
    AgeRating,
    ExternalRating,
    Release,
    ReleaseMember,
    ReleaseMemberUser,
    ReleaseName,
    ReleaseRating,
    Sponsor,
)
from aniliberty.models.schedule import ScheduledRelease, ScheduleNow
from aniliberty.models.team import Team, TeamMember, TeamMemberAccount, TeamRole
from aniliberty.models.torrent import Torrent, TorrentCodec, TorrentFile, TorrentMember
from aniliberty.models.user import TorrentStats, UserProfile

__all__ = [
    "EMPTY_VALUE_AS_NONE",
    "AgeRating",
    "AgeRatingValue",
    "CatalogSorting",
    "ApiStatus",
    "AuthToken",
    "Episode",
    "ExternalRating",
    "Franchise",
    "FranchiseRelease",
    "Genre",
    "Image",
    "ImageSet",
    "IssuedOtp",
    "Otp",
    "ProductionStatus",
    "Promotion",
    "PublishStatus",
    "Release",
    "ReleaseType",
    "ReleaseMember",
    "ReleaseMemberUser",
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
    "TeamMemberAccount",
    "TeamRole",
    "Torrent",
    "TorrentCodec",
    "TorrentFile",
    "TorrentMember",
    "TorrentStats",
    "UserProfile",
    "ValueDescription",
    "Video",
    "VideoOrigin",
]
