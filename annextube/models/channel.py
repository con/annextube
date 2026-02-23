"""Channel entity model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict


class ArchiveStats(TypedDict, total=False):
    """Statistics computed from local archive."""

    total_videos_archived: int
    first_video_date: str | None  # ISO 8601 date
    last_video_date: str | None  # ISO 8601 date
    total_duration_seconds: int
    total_size_bytes: int


@dataclass
class Channel:
    """Represents a YouTube channel being archived."""

    channel_id: str
    name: str
    description: str
    subscriber_count: int
    video_count: int
    avatar_url: str
    videos: list[str]
    playlists: list[str]
    created_at: datetime
    custom_url: str | None = None
    last_sync: datetime | None = None
    fetched_at: datetime | None = None
    banner_url: str | None = None
    country: str | None = None
    archive_stats: ArchiveStats = field(default_factory=ArchiveStats)  # Stats from local archive

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "description": self.description,
            "custom_url": self.custom_url,
            "subscriber_count": self.subscriber_count,
            "video_count": self.video_count,
            "avatar_url": self.avatar_url,
            "banner_url": self.banner_url,
            "country": self.country,
            "videos": self.videos,
            "playlists": self.playlists,
            "created_at": self.created_at.isoformat(),
            "archive_stats": self.archive_stats,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Channel":
        """Create from dictionary (loaded from JSON)."""
        return cls(
            channel_id=data["channel_id"],
            name=data["name"],
            description=data["description"],
            custom_url=data.get("custom_url"),
            subscriber_count=data["subscriber_count"],
            video_count=data["video_count"],
            avatar_url=data["avatar_url"],
            banner_url=data.get("banner_url"),
            country=data.get("country"),
            videos=data["videos"],
            playlists=data["playlists"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_sync=datetime.fromisoformat(data["last_sync"]) if "last_sync" in data else None,
            fetched_at=datetime.fromisoformat(data["fetched_at"]) if "fetched_at" in data else None,
            archive_stats=data.get("archive_stats", {}),
        )
