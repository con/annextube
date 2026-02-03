"""Playlist data model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Playlist:
    """Represents a YouTube playlist.

    Attributes:
        playlist_id: Unique YouTube playlist ID
        title: Playlist title
        description: Playlist description
        channel_id: Channel ID that owns the playlist
        channel_name: Channel name that owns the playlist
        video_count: Number of videos in playlist
        privacy_status: Privacy status (public, unlisted, private)
        last_modified: When playlist was last modified
        video_ids: Ordered list of video IDs in playlist
        thumbnail_url: Playlist thumbnail URL
        fetched_at: When this metadata was fetched
    """

    playlist_id: str
    title: str
    description: str
    channel_id: str
    channel_name: str
    video_count: int
    privacy_status: str
    last_modified: datetime | None
    video_ids: list[str]
    thumbnail_url: str | None = None
    fetched_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "playlist_id": self.playlist_id,
            "title": self.title,
            "description": self.description,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "video_count": self.video_count,
            "privacy_status": self.privacy_status,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "video_ids": self.video_ids,
            "thumbnail_url": self.thumbnail_url,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }
