"""YouTube service using yt-dlp for metadata and video operations."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yt_dlp

from annextube.lib.logging_config import get_logger
from annextube.models.video import Video

logger = get_logger(__name__)


class YouTubeService:
    """Wrapper around yt-dlp for YouTube operations."""

    def __init__(self, archive_file: Optional[Path] = None):
        """Initialize YouTubeService.

        Args:
            archive_file: Optional path to yt-dlp archive file for tracking
        """
        self.archive_file = archive_file

    def _get_ydl_opts(self, download: bool = False) -> Dict[str, Any]:
        """Get yt-dlp options.

        Args:
            download: Whether to download video content

        Returns:
            yt-dlp options dictionary
        """
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,  # Get full metadata
            "skip_download": not download,
        }

        if self.archive_file:
            opts["download_archive"] = str(self.archive_file)

        return opts

    def get_channel_videos(
        self, channel_url: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get videos from a channel.

        Args:
            channel_url: YouTube channel URL
            limit: Optional limit for number of videos (most recent)

        Returns:
            List of video metadata dictionaries
        """
        logger.info(f"Fetching videos from channel: {channel_url}")

        # Ensure we're getting the videos tab, not channel tabs
        if not channel_url.endswith("/videos"):
            channel_url = channel_url.rstrip("/") + "/videos"
            logger.debug(f"Adjusted URL to videos tab: {channel_url}")

        ydl_opts = self._get_ydl_opts(download=False)

        # Get full metadata directly
        ydl_opts.update(
            {
                "playlistend": limit if limit else None,
                "ignoreerrors": True,  # Continue on errors
                "no_warnings": False,  # Show warnings for debugging
            }
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract channel info (this gets the uploads playlist with full metadata)
                info = ydl.extract_info(channel_url, download=False)

                if not info:
                    logger.warning(f"No information found for channel: {channel_url}")
                    return []

                # Get entries (videos) - full metadata included
                entries = info.get("entries", [])

                if not entries:
                    logger.warning("Channel has no videos or videos are not accessible")
                    return []

                logger.info(f"Found {len(entries)} video(s) in channel")

                if limit:
                    entries = entries[:limit]
                    logger.info(f"Limited to {len(entries)} video(s)")

                # Filter out None entries and extract metadata
                videos = []
                for entry in entries:
                    if entry is None:
                        continue

                    # Some entries might be incomplete, skip them
                    if not entry.get("id"):
                        logger.warning(f"Skipping entry without ID: {entry.get('title', 'Unknown')}")
                        continue

                    videos.append(entry)

                logger.info(f"Successfully fetched metadata for {len(videos)} video(s)")
                return videos

            except Exception as e:
                logger.error(f"Failed to fetch channel videos: {e}", exc_info=True)
                return []

    def get_video_metadata(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a single video.

        Args:
            video_url: YouTube video URL

        Returns:
            Video metadata dictionary or None if failed
        """
        logger.debug(f"Fetching metadata for: {video_url}")

        ydl_opts = self._get_ydl_opts(download=False)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                return info
            except Exception as e:
                logger.error(f"Failed to fetch video metadata: {e}")
                return None

    def extract_video_url(self, video_id: str) -> Optional[str]:
        """Extract direct video URL for git-annex tracking.

        Args:
            video_id: YouTube video ID

        Returns:
            Direct video URL or None if failed
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        info = self.get_video_metadata(video_url)

        if not info:
            return None

        # Get best format URL
        formats = info.get("formats", [])
        if not formats:
            return video_url  # Fallback to YouTube URL

        # Get best video+audio format
        best_format = None
        for fmt in formats:
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                best_format = fmt
                break

        if best_format and "url" in best_format:
            return best_format["url"]

        return video_url  # Fallback

    def download_captions(self, video_id: str, output_dir: Path) -> List[str]:
        """Download captions for a video.

        Args:
            video_id: YouTube video ID
            output_dir: Directory to save captions

        Returns:
            List of downloaded caption language codes
        """
        logger.info(f"Downloading captions for: {video_id}")

        output_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["all"],
            "subtitlesformat": "vtt",
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        }

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])

                # Find downloaded caption files
                caption_files = list(output_dir.glob(f"{video_id}.*.vtt"))
                languages = [f.stem.split(".")[-1] for f in caption_files]

                logger.info(f"Downloaded {len(languages)} captions: {languages}")
                return languages

            except Exception as e:
                logger.error(f"Failed to download captions: {e}")
                return []

    def metadata_to_video(self, metadata: Dict[str, Any]) -> Video:
        """Convert yt-dlp metadata to Video model.

        Args:
            metadata: yt-dlp metadata dictionary

        Returns:
            Video model instance
        """
        # Parse published date
        published_str = metadata.get("upload_date", "")
        if published_str:
            try:
                published_at = datetime.strptime(published_str, "%Y%m%d")
            except ValueError:
                published_at = datetime.now()
        else:
            published_at = datetime.now()

        # Get available caption languages
        subtitles = metadata.get("subtitles", {})
        auto_captions = metadata.get("automatic_captions", {})
        all_captions = set(list(subtitles.keys()) + list(auto_captions.keys()))

        # Get tags, handle both list and None
        tags = metadata.get("tags")
        if tags is None:
            tags = []
        elif not isinstance(tags, list):
            tags = []

        # Get category
        category = metadata.get("category", "")
        categories = [category] if category else []

        return Video(
            video_id=metadata["id"],
            title=metadata.get("title", "Unknown"),
            description=metadata.get("description", ""),
            channel_id=metadata.get("channel_id", metadata.get("uploader_id", "")),
            channel_name=metadata.get("channel", metadata.get("uploader", "")),
            published_at=published_at,
            duration=int(metadata.get("duration", 0) or 0),
            view_count=int(metadata.get("view_count", 0) or 0),
            like_count=int(metadata.get("like_count", 0) or 0),
            comment_count=int(metadata.get("comment_count", 0) or 0),
            thumbnail_url=metadata.get("thumbnail", ""),
            license=metadata.get("license", "standard"),
            privacy_status="public",  # yt-dlp doesn't expose this easily
            availability=metadata.get("availability", "public"),
            tags=tags,
            categories=categories,
            language=metadata.get("language"),
            captions_available=list(all_captions),
            has_auto_captions=len(auto_captions) > 0,
            download_status="not_downloaded",
            source_url=metadata.get("webpage_url", f"https://www.youtube.com/watch?v={metadata['id']}"),
            fetched_at=datetime.now(),
            updated_at=datetime.now(),
        )
