"""Archiver service - core archival logic."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from annextube.lib.config import Config
from annextube.lib.logging_config import get_logger
from annextube.models.channel import Channel
from annextube.models.playlist import Playlist
from annextube.models.video import Video
from annextube.services.export import ExportService
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

    def __init__(self, repo_path: Path, config: Config, skip_existing: bool = False):
        """Initialize Archiver.

        Args:
            repo_path: Path to archive repository
            config: Configuration object
            skip_existing: If True, skip videos that have already been processed
        """
        self.repo_path = repo_path
        self.config = config
        self.skip_existing = skip_existing
        self.git_annex = GitAnnexService(repo_path)
        self.youtube = YouTubeService()

        # Initialize sync state service
        from .sync_state import SyncStateService
        self.sync_state = SyncStateService(repo_path)
        self.sync_state.load()
        self.export = ExportService(repo_path)
        self._video_id_to_path_cache = None  # Cache for video ID to path mapping

    def _load_video_paths(self) -> dict:
        """Load existing video ID to path mapping from videos.tsv.

        Returns:
            Dictionary mapping video_id to current path
        """
        videos_tsv = self.repo_path / "videos" / "videos.tsv"
        if not videos_tsv.exists():
            return {}

        video_map = {}
        try:
            with open(videos_tsv, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) < 2:  # No data rows
                    return {}

                # Parse header to find path and video_id columns
                header = lines[0].strip().split('\t')
                try:
                    path_idx = header.index('path')
                    video_id_idx = header.index('video_id')
                except ValueError:
                    logger.warning("videos.tsv missing required columns (path, video_id)")
                    return {}

                # Parse data rows
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    fields = line.strip().split('\t')
                    if len(fields) > max(path_idx, video_id_idx):
                        video_id = fields[video_id_idx]
                        path = fields[path_idx]
                        if video_id and path:
                            video_map[video_id] = path

        except Exception as e:
            logger.warning(f"Failed to load videos.tsv: {e}")
            return {}

        return video_map

    def _rename_video_if_needed(self, video: Video, new_path: Path) -> Path:
        """Rename video directory if path pattern has changed.

        Uses git mv to preserve history when renaming.

        Args:
            video: Video model instance
            new_path: New desired path for video

        Returns:
            Actual path to use (either new_path or existing path if no rename needed)
        """
        # Load video path cache if not already loaded
        if self._video_id_to_path_cache is None:
            self._video_id_to_path_cache = self._load_video_paths()

        # Check if this video already exists with a different path
        existing_rel_path = self._video_id_to_path_cache.get(video.video_id)
        if not existing_rel_path:
            # New video, no rename needed
            return new_path

        existing_path = self.repo_path / "videos" / existing_rel_path

        # If paths are the same, no rename needed
        if existing_path == new_path:
            logger.debug(f"Video path unchanged: {existing_rel_path}")
            return new_path

        # Path has changed - need to rename
        if not existing_path.exists():
            logger.warning(f"Existing path not found for {video.video_id}: {existing_path}")
            return new_path

        logger.info(f"Renaming video {video.video_id}: {existing_rel_path} -> {new_path.name}")

        try:
            # Ensure parent directory exists
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Use git mv to preserve history
            import subprocess
            result = subprocess.run(
                ["git", "mv", str(existing_path), str(new_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"git mv successful: {result.stdout}")

            # Update cache
            self._video_id_to_path_cache[video.video_id] = new_path.relative_to(self.repo_path / "videos").as_posix()

            return new_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to rename video with git mv: {e.stderr}")
            # If git mv fails, fall back to existing path
            return existing_path
        except Exception as e:
            logger.error(f"Failed to rename video: {e}")
            return existing_path

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

    def _get_playlist_path(self, playlist: Playlist) -> Path:
        """Generate playlist directory path from pattern.

        Uses sanitized playlist title for filesystem-friendly browsing.

        Args:
            playlist: Playlist model instance

        Returns:
            Path to playlist directory
        """
        # Use sanitized title for filesystem-friendly names
        # Pattern support kept for backward compatibility
        pattern = self.config.organization.playlist_path_pattern

        # Build placeholders
        placeholders = {
            'playlist_id': playlist.playlist_id,
            'channel_id': playlist.channel_id,
            'channel_name': sanitize_filename(playlist.channel_name),
            'playlist_title': sanitize_filename(playlist.title),
        }

        # Replace placeholders in pattern
        path_str = pattern
        for key, value in placeholders.items():
            path_str = path_str.replace(f'{{{key}}}', value)

        # If still using default {playlist_id}, use sanitized title instead
        if path_str == playlist.playlist_id:
            path_str = sanitize_filename(playlist.title)

        return self.repo_path / "playlists" / path_str

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

            # Generate TSV metadata files
            try:
                logger.info("Generating TSV metadata files")
                self.export.generate_all()
                self.git_annex.add_and_commit("Update TSV metadata files")
            except Exception as e:
                logger.warning(f"Failed to generate TSV files: {e}")

            # Save sync state
            self.sync_state.save()

        except Exception as e:
            logger.error(f"Channel backup failed: {e}")
            stats["errors"].append(str(e))

        return stats

    def backup_playlist(self, playlist_url: str) -> dict:
        """Backup a YouTube playlist.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            Summary dictionary with statistics
        """
        logger.info(f"Starting backup for playlist: {playlist_url}")

        stats = {
            "playlist_url": playlist_url,
            "videos_processed": 0,
            "videos_tracked": 0,
            "metadata_saved": 0,
            "captions_downloaded": 0,
            "errors": [],
        }

        try:
            # Get playlist metadata
            playlist = self.youtube.get_playlist_metadata(playlist_url)
            if not playlist:
                logger.error("Failed to fetch playlist metadata")
                stats["errors"].append("Failed to fetch playlist metadata")
                return stats

            # Create playlist directory
            playlist_dir = self._get_playlist_path(playlist)
            playlist_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Playlist directory: {playlist_dir}")

            # Save playlist metadata
            metadata_path = playlist_dir / "playlist.json"
            with open(metadata_path, "w") as f:
                json.dump(playlist.to_dict(), f, indent=2)
            logger.debug(f"Saved playlist metadata: {metadata_path}")

            # Get playlist videos
            limit = self.config.filters.limit
            videos_metadata = self.youtube.get_playlist_videos(playlist_url, limit=limit)

            if not videos_metadata:
                logger.warning("No videos found in playlist")
                return stats

            logger.info(f"Found {len(videos_metadata)} videos to process")

            # Get prefix width and separator for ordered symlinks
            prefix_width = self.config.organization.playlist_prefix_width
            separator = self.config.organization.playlist_prefix_separator

            # Process each video and create ordered symlinks
            for i, video_meta in enumerate(videos_metadata, 1):
                try:
                    logger.info(f"Processing video {i}/{len(videos_metadata)}: {video_meta.get('title', 'Unknown')}")
                    video = self.youtube.metadata_to_video(video_meta)

                    # Process video (creates video directory with content)
                    caption_count = self._process_video(video)

                    # Create ordered symlink in playlist directory
                    video_dir = self._get_video_path(video)
                    if video_dir.exists():
                        # Create symlink with zero-padded numeric prefix
                        # Format: {NNNN}_{video_dir_name} -> ../../videos/{video_dir_name}
                        prefix = f"{i:0{prefix_width}d}{separator}"
                        symlink_name = f"{prefix}{video_dir.name}"
                        symlink_path = playlist_dir / symlink_name

                        # Create relative symlink (for repository portability)
                        # From: playlists/{playlist_name}/{symlink}
                        # To:   videos/{video_dir_name}
                        relative_target = Path("..") / ".." / "videos" / video_dir.name

                        # Remove existing symlink if present
                        if symlink_path.exists() or symlink_path.is_symlink():
                            symlink_path.unlink()

                        symlink_path.symlink_to(relative_target)
                        logger.debug(f"Created symlink: {symlink_name} -> {relative_target}")
                    else:
                        logger.warning(f"Video directory not found, skipping symlink: {video_dir}")

                    stats["videos_processed"] += 1
                    stats["videos_tracked"] += 1
                    stats["metadata_saved"] += 1
                    stats["captions_downloaded"] += caption_count

                except Exception as e:
                    logger.error(f"Failed to process video {video_meta.get('id', 'unknown')}: {e}", exc_info=True)
                    stats["errors"].append(str(e))

            # Commit changes
            self.git_annex.add_and_commit(
                f"Backup playlist: {playlist.title} ({stats['videos_processed']} videos)"
            )

            logger.info(f"Backup complete: {stats['videos_processed']} videos processed")

            # Generate TSV metadata files
            try:
                logger.info("Generating TSV metadata files")
                self.export.generate_all()
                self.git_annex.add_and_commit("Update TSV metadata files")
            except Exception as e:
                logger.warning(f"Failed to generate TSV files: {e}")

            # Save sync state
            self.sync_state.save()

        except Exception as e:
            logger.error(f"Playlist backup failed: {e}")
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

        # Check if we should skip this video
        if self.skip_existing:
            video_state = self.sync_state.get_video_state(video.video_id)
            if video_state and video_state.last_metadata_fetch:
                logger.info(f"Skipping already-processed video: {video.video_id}")
                return 0

        # Calculate expected path using configurable pattern
        expected_path = self._get_video_path(video)

        # Check if video needs renaming (path pattern changed)
        video_dir = self._rename_video_if_needed(video, expected_path)

        # Create directory if it doesn't exist (new videos)
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
                    'filetype': 'video',
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

        # Download comments (if enabled)
        comments_fetched = False
        if self.config.components.comments_depth > 0:
            comments_path = video_dir / "comments.json"
            comments_fetched = self.youtube.download_comments(
                video.video_id,
                comments_path,
                max_depth=self.config.components.comments_depth
            )

        # Update sync state
        self.sync_state.update_video_state(
            video_id=video.video_id,
            published_at=video.published_at,
            comment_count=video.comment_count,
            view_count=video.view_count,
            like_count=video.like_count,
            metadata_fetched=True,
            comments_fetched=comments_fetched,
            captions_fetched=(caption_count > 0),
        )

        return caption_count

    def _download_thumbnail(self, video: Video, video_dir: Path) -> None:
        """Download video thumbnail and set git-annex metadata.

        Args:
            video: Video model instance
            video_dir: Video directory path
        """
        try:
            import urllib.request

            thumbnail_path = video_dir / "thumbnail.jpg"
            urllib.request.urlretrieve(video.thumbnail_url, thumbnail_path)
            logger.debug(f"Downloaded thumbnail: {thumbnail_path}")

            # Set git-annex metadata for thumbnail
            # Note: Must be done after git add, so we do it in a try/except
            try:
                metadata = {
                    'video_id': video.video_id,
                    'title': video.title,
                    'channel': video.channel_name,
                    'published': video.published_at.strftime('%Y-%m-%d'),
                    'filetype': 'thumbnail',
                }
                self.git_annex.set_metadata(thumbnail_path, metadata)
                logger.debug(f"Set git-annex metadata for thumbnail: {thumbnail_path}")
            except Exception as e:
                # Metadata setting might fail if file not yet in annex
                logger.debug(f"Could not set thumbnail metadata (will be set on commit): {e}")

        except Exception as e:
            logger.warning(f"Failed to download thumbnail: {e}")

    def _download_captions(self, video: Video, video_dir: Path) -> int:
        """Download video captions, generate captions.tsv, and set git-annex metadata.

        Args:
            video: Video model instance
            video_dir: Video directory path

        Returns:
            Number of caption files downloaded
        """
        try:
            captions_dir = video_dir / "captions"
            # Use caption language filter from config
            language_pattern = self.config.components.caption_languages
            captions_metadata = self.youtube.download_captions(
                video.video_id, captions_dir, language_pattern=language_pattern
            )

            if captions_metadata:
                # Create captions.tsv with metadata
                captions_tsv_path = video_dir / "captions.tsv"
                with open(captions_tsv_path, "w") as f:
                    # Write header
                    f.write("language_code\tauto_generated\tfile_path\tfetched_at\n")
                    # Write caption rows and set git-annex metadata
                    for caption in captions_metadata:
                        f.write(
                            f"{caption['language_code']}\t"
                            f"{caption['auto_generated']}\t"
                            f"{caption['file_path']}\t"
                            f"{caption['fetched_at']}\n"
                        )

                        # Set git-annex metadata for each caption file
                        # captions are text files (*.vtt) so they go to git, not annex
                        # but we can still set metadata if they end up in annex
                        # (depends on .gitattributes rules)
                        try:
                            caption_file_path = self.repo_path / caption['file_path']
                            lang_code = caption['language_code']
                            metadata = {
                                'video_id': video.video_id,
                                'title': video.title,
                                'channel': video.channel_name,
                                'published': video.published_at.strftime('%Y-%m-%d'),
                                'filetype': f'caption.{lang_code}',
                                'language': lang_code,
                                'auto_generated': str(caption['auto_generated']),
                            }
                            self.git_annex.set_metadata(caption_file_path, metadata)
                            logger.debug(f"Set git-annex metadata for caption: {caption_file_path}")
                        except Exception as e:
                            # Captions are in git (*.vtt), so metadata setting may not apply
                            logger.debug(f"Could not set caption metadata (file in git, not annex): {e}")

                logger.debug(f"Downloaded {len(captions_metadata)} caption files and created captions.tsv")
                return len(captions_metadata)

        except Exception as e:
            logger.warning(f"Failed to download captions: {e}")

        return 0
