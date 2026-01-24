"""Archiver service - core archival logic."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from annextube.lib.config import Config
from annextube.lib.logging_config import get_logger
from annextube.models.channel import Channel
from annextube.models.video import Video
from annextube.services.git_annex import GitAnnexService
from annextube.services.youtube import YouTubeService

logger = get_logger(__name__)


class Archiver:
    """Core archival logic coordinating git-annex and YouTube services."""

    def __init__(self, repo_path: Path, config: Config):
        """Initialize Archiver.

        Args:
            repo_path: Path to archive repository
            config: Configuration object
        """
        self.repo_path = repo_path
        self.config = config
        self.git_annex = GitAnnexService(repo_path)
        self.youtube = YouTubeService()

    def backup_channel(self, channel_url: str) -> dict:
        """Backup a YouTube channel.

        Args:
            channel_url: YouTube channel URL

        Returns:
            Summary dictionary with statistics
        """
        logger.info(f"Starting backup for channel: {channel_url}")

        stats = {
            "channel_url": channel_url,
            "videos_processed": 0,
            "videos_tracked": 0,
            "metadata_saved": 0,
            "captions_downloaded": 0,
            "errors": [],
        }

        try:
            # Get channel videos
            limit = self.config.filters.limit
            videos_metadata = self.youtube.get_channel_videos(channel_url, limit=limit)

            if not videos_metadata:
                logger.warning("No videos found")
                return stats

            logger.info(f"Found {len(videos_metadata)} videos to process")

            # Process each video
            for i, video_meta in enumerate(videos_metadata, 1):
                try:
                    logger.info(f"Processing video {i}/{len(videos_metadata)}: {video_meta.get('title', 'Unknown')}")
                    video = self.youtube.metadata_to_video(video_meta)
                    self._process_video(video)

                    stats["videos_processed"] += 1
                    stats["videos_tracked"] += 1
                    stats["metadata_saved"] += 1

                except Exception as e:
                    logger.error(f"Failed to process video {video_meta.get('id', 'unknown')}: {e}", exc_info=True)
                    stats["errors"].append(str(e))

            # Commit changes
            self.git_annex.add_and_commit(
                f"Backup channel: {channel_url} ({stats['videos_processed']} videos)"
            )

            logger.info(f"Backup complete: {stats['videos_processed']} videos processed")

        except Exception as e:
            logger.error(f"Channel backup failed: {e}")
            stats["errors"].append(str(e))

        return stats

    def _process_video(self, video: Video) -> None:
        """Process a single video.

        Args:
            video: Video model instance
        """
        logger.debug(f"Processing video: {video.video_id} - {video.title}")

        # Create video directory
        video_dir = self.repo_path / "videos" / video.video_id
        video_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        metadata_path = video_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(video.to_dict(), f, indent=2)

        logger.debug(f"Saved metadata: {metadata_path}")

        # Track video URL (if videos component enabled)
        if self.config.components.videos:
            video_url = self.youtube.extract_video_url(video.video_id)
            if video_url:
                video_file = video_dir / "video.mp4"
                try:
                    self.git_annex.addurl(
                        url=video_url, file_path=video_file, relaxed=True, fast=True
                    )
                    logger.debug(f"Tracked video URL: {video_file}")
                except Exception as e:
                    logger.warning(f"Failed to track video URL: {e}")

        # Download thumbnail (if enabled)
        if self.config.components.thumbnails and video.thumbnail_url:
            self._download_thumbnail(video, video_dir)

        # Download captions (if enabled)
        if self.config.components.captions and video.captions_available:
            self._download_captions(video, video_dir)

    def _download_thumbnail(self, video: Video, video_dir: Path) -> None:
        """Download video thumbnail.

        Args:
            video: Video model instance
            video_dir: Video directory path
        """
        try:
            import urllib.request

            thumbnail_path = video_dir / "thumbnail.jpg"
            urllib.request.urlretrieve(video.thumbnail_url, thumbnail_path)
            logger.debug(f"Downloaded thumbnail: {thumbnail_path}")

        except Exception as e:
            logger.warning(f"Failed to download thumbnail: {e}")

    def _download_captions(self, video: Video, video_dir: Path) -> None:
        """Download video captions.

        Args:
            video: Video model instance
            video_dir: Video directory path
        """
        try:
            captions_dir = video_dir / "captions"
            languages = self.youtube.download_captions(video.video_id, captions_dir)

            if languages:
                logger.debug(f"Downloaded {len(languages)} caption files")

        except Exception as e:
            logger.warning(f"Failed to download captions: {e}")
