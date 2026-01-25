"""Service for tracking synchronization state of sources and videos."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class VideoSyncState:
    """Sync state for a single video."""

    video_id: str
    published_at: Optional[datetime] = None
    last_metadata_fetch: Optional[datetime] = None
    last_comments_fetch: Optional[datetime] = None
    last_captions_fetch: Optional[datetime] = None
    comment_count_last: int = 0
    view_count_last: int = 0
    like_count_last: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'video_id': self.video_id,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'last_metadata_fetch': self.last_metadata_fetch.isoformat() if self.last_metadata_fetch else None,
            'last_comments_fetch': self.last_comments_fetch.isoformat() if self.last_comments_fetch else None,
            'last_captions_fetch': self.last_captions_fetch.isoformat() if self.last_captions_fetch else None,
            'comment_count_last': self.comment_count_last,
            'view_count_last': self.view_count_last,
            'like_count_last': self.like_count_last,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VideoSyncState":
        """Create from dictionary."""
        return cls(
            video_id=data['video_id'],
            published_at=datetime.fromisoformat(data['published_at']) if data.get('published_at') else None,
            last_metadata_fetch=datetime.fromisoformat(data['last_metadata_fetch']) if data.get('last_metadata_fetch') else None,
            last_comments_fetch=datetime.fromisoformat(data['last_comments_fetch']) if data.get('last_comments_fetch') else None,
            last_captions_fetch=datetime.fromisoformat(data['last_captions_fetch']) if data.get('last_captions_fetch') else None,
            comment_count_last=data.get('comment_count_last', 0),
            view_count_last=data.get('view_count_last', 0),
            like_count_last=data.get('like_count_last', 0),
        )


@dataclass
class SourceSyncState:
    """Sync state for a source (channel or playlist)."""

    source_url: str
    source_type: str  # 'channel' or 'playlist'
    last_sync: Optional[datetime] = None
    last_video_published: Optional[datetime] = None
    videos_tracked: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'source_url': self.source_url,
            'source_type': self.source_type,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'last_video_published': self.last_video_published.isoformat() if self.last_video_published else None,
            'videos_tracked': self.videos_tracked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SourceSyncState":
        """Create from dictionary."""
        return cls(
            source_url=data['source_url'],
            source_type=data['source_type'],
            last_sync=datetime.fromisoformat(data['last_sync']) if data.get('last_sync') else None,
            last_video_published=datetime.fromisoformat(data['last_video_published']) if data.get('last_video_published') else None,
            videos_tracked=data.get('videos_tracked', 0),
        )


class SyncStateService:
    """Service for managing sync state."""

    def __init__(self, repo_path: Path):
        """Initialize SyncStateService.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path
        self.state_file = repo_path / ".annextube" / "sync_state.json"
        self.sources: Dict[str, SourceSyncState] = {}
        self.videos: Dict[str, VideoSyncState] = {}

    def load(self) -> None:
        """Load sync state from file."""
        if not self.state_file.exists():
            logger.debug(f"No sync state file found at {self.state_file}")
            return

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load sources
            sources_data = data.get('sources', {})
            self.sources = {
                url: SourceSyncState.from_dict(state)
                for url, state in sources_data.items()
            }

            # Load videos
            videos_data = data.get('videos', {})
            self.videos = {
                video_id: VideoSyncState.from_dict(state)
                for video_id, state in videos_data.items()
            }

            logger.info(f"Loaded sync state: {len(self.sources)} sources, {len(self.videos)} videos")

        except Exception as e:
            logger.error(f"Failed to load sync state: {e}")

    def save(self) -> None:
        """Save sync state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'sources': {
                url: state.to_dict()
                for url, state in self.sources.items()
            },
            'videos': {
                video_id: state.to_dict()
                for video_id, state in self.videos.items()
            }
        }

        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved sync state: {len(self.sources)} sources, {len(self.videos)} videos")

        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    def get_source_state(self, source_url: str) -> Optional[SourceSyncState]:
        """Get sync state for a source.

        Args:
            source_url: URL of the source

        Returns:
            SourceSyncState if found, None otherwise
        """
        return self.sources.get(source_url)

    def update_source_state(self, source_url: str, source_type: str,
                           last_video_published: Optional[datetime] = None,
                           videos_tracked: Optional[int] = None) -> SourceSyncState:
        """Update sync state for a source.

        Args:
            source_url: URL of the source
            source_type: Type of source ('channel' or 'playlist')
            last_video_published: Most recent video publication date
            videos_tracked: Number of videos tracked

        Returns:
            Updated SourceSyncState
        """
        if source_url not in self.sources:
            self.sources[source_url] = SourceSyncState(
                source_url=source_url,
                source_type=source_type,
            )

        state = self.sources[source_url]
        state.last_sync = datetime.now()

        if last_video_published:
            state.last_video_published = last_video_published

        if videos_tracked is not None:
            state.videos_tracked = videos_tracked

        return state

    def get_video_state(self, video_id: str) -> Optional[VideoSyncState]:
        """Get sync state for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoSyncState if found, None otherwise
        """
        return self.videos.get(video_id)

    def update_video_state(self, video_id: str,
                          published_at: Optional[datetime] = None,
                          comment_count: Optional[int] = None,
                          view_count: Optional[int] = None,
                          like_count: Optional[int] = None,
                          metadata_fetched: bool = False,
                          comments_fetched: bool = False,
                          captions_fetched: bool = False) -> VideoSyncState:
        """Update sync state for a video.

        Args:
            video_id: YouTube video ID
            published_at: Video publication date
            comment_count: Current comment count
            view_count: Current view count
            like_count: Current like count
            metadata_fetched: Whether metadata was fetched this sync
            comments_fetched: Whether comments were fetched this sync
            captions_fetched: Whether captions were fetched this sync

        Returns:
            Updated VideoSyncState
        """
        if video_id not in self.videos:
            self.videos[video_id] = VideoSyncState(video_id=video_id)

        state = self.videos[video_id]
        now = datetime.now()

        if published_at:
            state.published_at = published_at

        if comment_count is not None:
            state.comment_count_last = comment_count

        if view_count is not None:
            state.view_count_last = view_count

        if like_count is not None:
            state.like_count_last = like_count

        if metadata_fetched:
            state.last_metadata_fetch = now

        if comments_fetched:
            state.last_comments_fetch = now

        if captions_fetched:
            state.last_captions_fetch = now

        return state

    def should_update_comments(self, video_id: str, update_window_days: int = 7) -> bool:
        """Check if video comments should be updated.

        Args:
            video_id: YouTube video ID
            update_window_days: Number of days for update window

        Returns:
            True if comments should be updated
        """
        state = self.get_video_state(video_id)

        # First time: always update
        if not state or not state.last_comments_fetch:
            return True

        # Check if within update window
        if state.published_at:
            days_since_published = (datetime.now() - state.published_at).days
            if days_since_published <= update_window_days:
                return True

        # Check if comments were fetched recently
        days_since_fetch = (datetime.now() - state.last_comments_fetch).days
        if days_since_fetch > update_window_days:
            return True

        return False

    def should_update_captions(self, video_id: str, update_window_days: int = 7) -> bool:
        """Check if video captions should be updated.

        Args:
            video_id: YouTube video ID
            update_window_days: Number of days for update window

        Returns:
            True if captions should be updated
        """
        state = self.get_video_state(video_id)

        # First time: always update
        if not state or not state.last_captions_fetch:
            return True

        # Check if within update window
        if state.published_at:
            days_since_published = (datetime.now() - state.published_at).days
            if days_since_published <= update_window_days:
                return True

        # Check if captions were fetched recently
        days_since_fetch = (datetime.now() - state.last_captions_fetch).days
        if days_since_fetch > update_window_days:
            return True

        return False
