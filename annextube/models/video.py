"""Video entity model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Video:
    """Represents a YouTube video with all associated metadata."""

    video_id: str
    title: str
    description: str
    channel_id: str
    channel_name: str
    published_at: datetime
    duration: int  # seconds
    view_count: int
    like_count: int
    comment_count: int
    thumbnail_url: str
    license: str  # 'standard' or 'creativeCommon'
    privacy_status: str  # 'public', 'unlisted', 'private'
    availability: str  # 'public', 'private', 'deleted', 'unavailable'
    tags: List[str]
    categories: List[str]
    captions_available: List[str]
    has_auto_captions: bool
    download_status: str  # 'not_downloaded', 'tracked', 'downloaded', 'failed'
    source_url: str
    fetched_at: datetime
    updated_at: datetime
    language: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "description": self.description,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "published_at": self.published_at.isoformat(),
            "duration": self.duration,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "thumbnail_url": self.thumbnail_url,
            "license": self.license,
            "privacy_status": self.privacy_status,
            "availability": self.availability,
            "tags": self.tags,
            "categories": self.categories,
            "language": self.language,
            "captions_available": self.captions_available,
            "has_auto_captions": self.has_auto_captions,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "download_status": self.download_status,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Video":
        """Create from dictionary (loaded from JSON)."""
        return cls(
            video_id=data["video_id"],
            title=data["title"],
            description=data["description"],
            channel_id=data["channel_id"],
            channel_name=data["channel_name"],
            published_at=datetime.fromisoformat(data["published_at"]),
            duration=data["duration"],
            view_count=data["view_count"],
            like_count=data["like_count"],
            comment_count=data["comment_count"],
            thumbnail_url=data["thumbnail_url"],
            license=data["license"],
            privacy_status=data["privacy_status"],
            availability=data["availability"],
            tags=data["tags"],
            categories=data["categories"],
            language=data.get("language"),
            captions_available=data["captions_available"],
            has_auto_captions=data["has_auto_captions"],
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            download_status=data["download_status"],
            source_url=data["source_url"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
