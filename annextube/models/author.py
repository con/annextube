"""Author model for tracking video creators and commenters."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Author:
    """Represents a YouTube channel author (video uploader or commenter)."""

    author_id: str  # YouTube channel ID
    name: str  # Channel/author display name
    channel_url: Optional[str] = None  # Full channel URL if available
    first_seen: Optional[datetime] = None  # First time encountered
    last_seen: Optional[datetime] = None  # Most recent encounter
    video_count: int = 0  # Number of videos uploaded by this author
    comment_count: int = 0  # Number of comments made by this author

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'author_id': self.author_id,
            'name': self.name,
            'channel_url': self.channel_url,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'video_count': self.video_count,
            'comment_count': self.comment_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Author":
        """Create Author from dictionary."""
        first_seen = None
        if data.get('first_seen'):
            first_seen = datetime.fromisoformat(data['first_seen'])

        last_seen = None
        if data.get('last_seen'):
            last_seen = datetime.fromisoformat(data['last_seen'])

        return cls(
            author_id=data['author_id'],
            name=data['name'],
            channel_url=data.get('channel_url'),
            first_seen=first_seen,
            last_seen=last_seen,
            video_count=data.get('video_count', 0),
            comment_count=data.get('comment_count', 0),
        )
