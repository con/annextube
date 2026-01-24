"""SyncState entity model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SyncState:
    """Tracks synchronization state for incremental updates."""

    source_url: str
    source_type: str  # 'channel' or 'playlist'
    source_id: str
    last_sync: datetime
    error_count: int
    status: str  # 'active', 'error', 'paused'
    videos_tracked: int
    videos_downloaded: int
    last_video_id: Optional[str] = None
    last_video_published: Optional[datetime] = None
    last_error: Optional[str] = None
    next_retry: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_url": self.source_url,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "last_sync": self.last_sync.isoformat(),
            "last_video_id": self.last_video_id,
            "last_video_published": (
                self.last_video_published.isoformat() if self.last_video_published else None
            ),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "next_retry": self.next_retry.isoformat() if self.next_retry else None,
            "status": self.status,
            "videos_tracked": self.videos_tracked,
            "videos_downloaded": self.videos_downloaded,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncState":
        """Create from dictionary (loaded from JSON)."""
        return cls(
            source_url=data["source_url"],
            source_type=data["source_type"],
            source_id=data["source_id"],
            last_sync=datetime.fromisoformat(data["last_sync"]),
            last_video_id=data.get("last_video_id"),
            last_video_published=(
                datetime.fromisoformat(data["last_video_published"])
                if data.get("last_video_published")
                else None
            ),
            error_count=data["error_count"],
            last_error=data.get("last_error"),
            next_retry=(
                datetime.fromisoformat(data["next_retry"]) if data.get("next_retry") else None
            ),
            status=data["status"],
            videos_tracked=data["videos_tracked"],
            videos_downloaded=data["videos_downloaded"],
        )
