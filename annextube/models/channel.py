"""Channel entity model."""

from dataclasses import dataclass
from datetime import datetime


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
    last_sync: datetime
    created_at: datetime
    fetched_at: datetime
    custom_url: str | None = None
    banner_url: str | None = None
    country: str | None = None

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
            "last_sync": self.last_sync.isoformat(),
            "created_at": self.created_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
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
            last_sync=datetime.fromisoformat(data["last_sync"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
        )
