"""Archiver service - core archival logic."""

import json
import re
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


def sanitize_filename(text: str) -> str:
    """Sanitize text for use in filename.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for filesystem (uses '-' for word separation)
    """
    # Replace special chars (except spaces and hyphens)
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with hyphens (keep underscores for field separation)
    text = re.sub(r'[-\s]+', '-', text)
    # Limit length and lowercase
    text = text.lower()[:100]
    return text


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

    def _get_video_path(self, video: Video) -> Path:
        """Generate video directory path from pattern.

        Args:
            video: Video model instance

        Returns:
            Path to video directory
        """
        pattern = self.config.organization.video_path_pattern

        # Extract date from published_at (datetime object)
        try:
            if isinstance(video.published_at, datetime):
                date_str = video.published_at.strftime('%Y-%m-%d')
            else:
                # If it's a string, parse it
                date_obj = datetime.fromisoformat(str(video.published_at).replace('Z', '+00:00'))
                date_str = date_obj.strftime('%Y-%m-%d')
        except Exception as e:
            logger.warning(f"Failed to parse date from published_at: {e}")
            date_str = 'unknown'

        # Build placeholders
        placeholders = {
            'date': date_str,
            'video_id': video.video_id,
            'sanitized_title': sanitize_filename(video.title),
            'channel_id': video.channel_id,
            'channel_name': sanitize_filename(video.channel_name),
        }

        # Replace placeholders in pattern
        path_str = pattern
        for key, value in placeholders.items():
            path_str = path_str.replace(f'{{{key}}}', value)

        return self.repo_path / "videos" / path_str

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
                    caption_count = self._process_video(video)

                    stats["videos_processed"] += 1
                    stats["videos_tracked"] += 1
                    stats["metadata_saved"] += 1
                    stats["captions_downloaded"] += caption_count

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

    def _process_video(self, video: Video) -> int:
        """Process a single video.

        Args:
            video: Video model instance

        Returns:
            Number of captions downloaded
        """
        logger.debug(f"Processing video: {video.video_id} - {video.title}")
        caption_count = 0

        # Create video directory using configurable pattern
        video_dir = self._get_video_path(video)
        video_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Video directory: {video_dir}")

        # Save metadata
        metadata_path = video_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(video.to_dict(), f, indent=2)

        logger.debug(f"Saved metadata: {metadata_path}")

        # Track video URL with git-annex
        # Always track URL (even if videos=false), download only if videos=true
        # Use the YouTube watch URL directly - git-annex will invoke yt-dlp with --no-raw
        video_url = video.source_url  # YouTube watch URL, not extracted manifest URL
        if video_url:
            # Use configurable filename
            video_file = video_dir / self.config.organization.video_filename
            try:
                # Track URL without downloading (--fast --relaxed --no-raw)
                # --no-raw tells git-annex to use yt-dlp to resolve the YouTube URL
                self.git_annex.addurl(
                    url=video_url, file_path=video_file, relaxed=True, fast=True, no_raw=True
                )
                logger.debug(f"Tracked video URL: {video_file}")

                # Set git-annex metadata for the video file
                metadata = {
                    'video_id': video.video_id,
                    'title': video.title,
                    'channel': video.channel_name,
                    'published': video.published_at.strftime('%Y-%m-%d'),  # Just date
                    'duration': str(video.duration),
                    'source_url': video.source_url,
                }
                self.git_annex.set_metadata(video_file, metadata)
                logger.debug(f"Set git-annex metadata for: {video_file}")

                # If videos component enabled, download the content
                if self.config.components.videos:
                    logger.info(f"Downloading video content: {video_file}")
                    self.git_annex.get_file(video_file)

            except Exception as e:
                logger.warning(f"Failed to track video URL: {e}")

        # Download thumbnail (if enabled)
        if self.config.components.thumbnails and video.thumbnail_url:
            self._download_thumbnail(video, video_dir)

        # Download captions (if enabled)
        if self.config.components.captions and video.captions_available:
            caption_count = self._download_captions(video, video_dir)

        return caption_count

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

            # Note: Thumbnail metadata could be set after git add, but skipping for now
            # to avoid complexity with git-annex metadata timing

        except Exception as e:
            logger.warning(f"Failed to download thumbnail: {e}")

    def _download_captions(self, video: Video, video_dir: Path) -> int:
        """Download video captions and generate captions.tsv.

        Args:
            video: Video model instance
            video_dir: Video directory path

        Returns:
            Number of caption files downloaded
        """
        try:
            captions_dir = video_dir / "captions"
            captions_metadata = self.youtube.download_captions(video.video_id, captions_dir)

            if captions_metadata:
                # Create captions.tsv with metadata
                captions_tsv_path = video_dir / "captions.tsv"
                with open(captions_tsv_path, "w") as f:
                    # Write header
                    f.write("language_code\tauto_generated\tfile_path\tfetched_at\n")
                    # Write caption rows
                    for caption in captions_metadata:
                        f.write(
                            f"{caption['language_code']}\t"
                            f"{caption['auto_generated']}\t"
                            f"{caption['file_path']}\t"
                            f"{caption['fetched_at']}\n"
                        )

                logger.debug(f"Downloaded {len(captions_metadata)} caption files and created captions.tsv")
                return len(captions_metadata)

        except Exception as e:
            logger.warning(f"Failed to download captions: {e}")

        return 0
