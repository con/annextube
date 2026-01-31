"""Archiver service - core archival logic."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from annextube.lib.config import SourceConfig

from annextube.lib.config import Config
from annextube.lib.file_utils import AtomicFileWriter
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
        Sanitized text safe for filesystem (preserves original casing, uses '-' for word separation)
    """
    # Replace special chars (except spaces and hyphens)
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with hyphens (keep underscores for field separation)
    text = re.sub(r'[-\s]+', '-', text)
    # Limit length (preserve original casing)
    text = text[:100]
    return text


class Archiver:
    """Core archival logic coordinating git-annex and YouTube services."""

    def __init__(self, repo_path: Path, config: Config, update_mode: str = "videos-incremental",
                 date_from: Optional[datetime] = None, date_to: Optional[datetime] = None):
        """Initialize Archiver.

        Args:
            repo_path: Path to archive repository
            config: Configuration object
            update_mode: Update mode - "videos-incremental" (default), "all-incremental", "all-force",
                        "social" (comments+captions), "playlists", "comments", "captions"
            date_from: Filter videos published on or after this date (for video published_at, not comment timestamps)
            date_to: Filter videos published on or before this date (for video published_at, not comment timestamps)
        """
        self.repo_path = repo_path
        self.config = config
        self.update_mode = update_mode
        self.date_from = date_from
        self.date_to = date_to
        self.git_annex = GitAnnexService(repo_path)

        # Parse extractor args from ytdlp_extra_opts
        extractor_args = self._parse_extractor_args(config.user.ytdlp_extra_opts)

        # Initialize YouTubeService with user config settings
        self.youtube = YouTubeService(
            cookies_file=config.user.cookies_file,
            cookies_from_browser=config.user.cookies_from_browser,
            proxy=config.user.proxy,
            limit_rate=config.user.limit_rate,
            sleep_interval=config.user.sleep_interval,
            max_sleep_interval=config.user.max_sleep_interval,
            extractor_args=extractor_args,
        )

        self.export = ExportService(repo_path)
        self._video_id_to_path_cache = None  # Cache for video ID to path mapping
        self._processed_video_ids = set()  # Track videos processed in current run (avoid duplicates)

        # Configure git-annex with user config settings
        self.git_annex.configure_ytdlp_options(
            cookies_file=config.user.cookies_file,
            cookies_from_browser=config.user.cookies_from_browser,
            proxy=config.user.proxy,
            limit_rate=config.user.limit_rate,
            sleep_interval=config.user.sleep_interval,
            max_sleep_interval=config.user.max_sleep_interval,
            extra_opts=config.user.ytdlp_extra_opts,
        )

    def _parse_extractor_args(self, ytdlp_extra_opts: list[str]) -> dict:
        """Parse ytdlp_extra_opts CLI-style options to Python API extractor_args format.

        Converts ["--extractor-args", "youtube:player_client=android"]
        to {"youtube": {"player_client": ["android"]}}

        Args:
            ytdlp_extra_opts: List of CLI-style yt-dlp options

        Returns:
            Dictionary of extractor arguments for yt-dlp Python API
        """
        extractor_args = {}

        i = 0
        while i < len(ytdlp_extra_opts):
            opt = ytdlp_extra_opts[i]

            if opt == "--extractor-args" and i + 1 < len(ytdlp_extra_opts):
                # Parse "extractor:key=value" format
                arg_value = ytdlp_extra_opts[i + 1]
                if ":" in arg_value:
                    extractor, key_value = arg_value.split(":", 1)
                    if "=" in key_value:
                        key, value = key_value.split("=", 1)
                        if extractor not in extractor_args:
                            extractor_args[extractor] = {}
                        # Values are stored as lists in Python API
                        extractor_args[extractor][key] = [value]
                i += 2
            else:
                i += 1

        return extractor_args

    def _should_process_video_by_date(self, video_metadata: dict) -> bool:
        """Check if video should be processed based on date filters.

        Args:
            video_metadata: Video metadata dict (either yt-dlp schema or our stored schema)

        Returns:
            True if video is within date range (or no date filter set)
        """
        if not self.date_from and not self.date_to:
            return True  # No date filter

        # Extract published date - handle both schemas
        published_str = video_metadata.get("published_at") or video_metadata.get("upload_date", "")
        if not published_str:
            logger.warning(f"Video {video_metadata.get('video_id', video_metadata.get('id', 'unknown'))} has no published date, skipping")
            return False

        # Parse the date
        try:
            if len(published_str) == 8 and published_str.isdigit():
                # yt-dlp format: YYYYMMDD
                published_at = datetime.strptime(published_str, "%Y%m%d")
            else:
                # ISO format: YYYY-MM-DDTHH:MM:SS
                published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse published date '{published_str}': {e}")
            return False

        # Apply date filters
        if self.date_from and published_at < self.date_from:
            return False
        if self.date_to and published_at > self.date_to:
            return False

        return True

    def _should_process_component(self, component: str) -> bool:
        """Determine if a component should be processed based on update mode.

        Args:
            component: Component name ("videos", "playlists", "comments", "captions", "metadata")

        Returns:
            True if component should be processed
        """
        mode = self.update_mode

        # Component-specific modes
        if mode == component:
            return True

        # "social" is shortcut for comments + captions
        if mode == "social":
            return component in ["comments", "captions"]

        # "playlists" mode only processes playlists
        if mode == "playlists":
            return component == "playlists"

        # "comments" mode only processes comments
        if mode == "comments":
            return component == "comments"

        # "captions" mode only processes captions
        if mode == "captions":
            return component == "captions"

        # videos-incremental: new videos only, but also update playlists if video set changed
        if mode == "videos-incremental":
            return component in ["videos", "metadata", "playlists"]

        # all-incremental: new videos + social for recent + playlists
        if mode == "all-incremental":
            return component in ["videos", "metadata", "comments", "captions", "playlists"]

        # all-force: everything
        if mode == "all-force":
            return True

        # Default: process everything
        return True

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

    def _discover_playlists(self, channel_url: str, include_pattern: str,
                           exclude_pattern: Optional[str], include_podcasts: str) -> List[str]:
        """Discover and filter playlists from a channel.

        Args:
            channel_url: YouTube channel URL
            include_pattern: "all", "none", or regex pattern for playlists to include
            exclude_pattern: Optional regex pattern for playlists to exclude
            include_podcasts: "all", "none", or regex pattern for podcasts to include

        Returns:
            List of playlist URLs to backup
        """
        if include_pattern == "none" and include_podcasts == "none":
            return []

        playlists = []

        # Fetch and filter playlists
        if include_pattern != "none":
            playlists = self.youtube.get_channel_playlists(channel_url)

        # Fetch and filter podcasts
        if include_podcasts != "none":
            podcasts = self.youtube.get_channel_podcasts(channel_url)
            logger.info(f"Discovered {len(podcasts)} podcasts")

            # Filter podcasts by pattern
            if include_podcasts != "all":
                import re
                try:
                    pattern = re.compile(include_podcasts)
                    original_count = len(podcasts)
                    podcasts = [p for p in podcasts if pattern.search(p['title'])]
                    logger.info(f"Podcast filter '{include_podcasts}' matched {len(podcasts)}/{original_count} podcasts")
                except re.error as e:
                    logger.error(f"Invalid include_podcasts regex '{include_podcasts}': {e}")
                    podcasts = []

            playlists.extend(podcasts)

        if not playlists:
            return []

        # Filter by include pattern
        if include_pattern != "all":
            import re
            try:
                pattern = re.compile(include_pattern)
                original_count = len(playlists)
                playlists = [p for p in playlists if pattern.search(p['title'])]
                logger.info(f"Include filter '{include_pattern}' matched {len(playlists)}/{original_count} playlists")
            except re.error as e:
                logger.error(f"Invalid include_playlists regex '{include_pattern}': {e}")
                return []

        # Filter by exclude pattern
        if exclude_pattern:
            import re
            try:
                pattern = re.compile(exclude_pattern)
                original_count = len(playlists)
                playlists = [p for p in playlists if not pattern.search(p['title'])]
                logger.info(f"Exclude filter '{exclude_pattern}' removed {original_count - len(playlists)} playlists")
            except re.error as e:
                logger.error(f"Invalid exclude_playlists regex '{exclude_pattern}': {e}")

        # Log discovered playlists
        if playlists:
            logger.info(f"Will backup {len(playlists)} playlists:")
            for p in playlists:
                logger.info(f"  - {p['title']} ({p['video_count']} videos)")

        return [p['url'] for p in playlists]

    def backup_channel(self, channel_url: str, source_config: Optional['SourceConfig'] = None) -> dict:
        """Backup a YouTube channel.

        Args:
            channel_url: YouTube channel URL
            source_config: Optional source configuration for playlists

        Returns:
            Summary dictionary with statistics
        """
        logger.info(f"Starting backup for channel: {channel_url} (mode: {self.update_mode})")

        stats = {
            "channel_url": channel_url,
            "videos_processed": 0,
            "videos_tracked": 0,
            "metadata_saved": 0,
            "captions_downloaded": 0,
            "errors": [],
        }

        # Determine what videos to fetch based on update_mode
        limit = self.config.filters.limit
        existing_video_ids = None
        videos_metadata = []

        # Skip video fetching for component-specific modes that don't need videos
        skip_video_fetch = self.update_mode in ["social", "comments", "captions", "playlists"]

        if skip_video_fetch:
            # Component-specific mode: don't fetch new videos, only update existing ones
            logger.info(f"{self.update_mode} mode: skipping new video fetch")
        elif self.update_mode in ["videos-incremental", "all-incremental"]:
            # Get existing IDs for incremental updates
            from .tsv_reader import TSVReader
            videos_tsv_path = self.repo_path / "videos" / "videos.tsv"
            existing_video_ids = TSVReader.get_existing_video_ids(videos_tsv_path)

            if existing_video_ids:
                logger.info(f"Incremental mode: filtering {len(existing_video_ids)} existing videos")
                # YouTube service uses two-pass approach: extract_flat for IDs, then full metadata for new only
            else:
                logger.info("No existing videos.tsv found, performing full initial backup")

        # Fetch videos (unless in component-specific mode)
        # NOTE: In incremental mode, we don't use limit - we fetch until we hit existing videos.
        # This is more efficient than fetching a fixed number that might all be existing.
        if not skip_video_fetch:
            all_videos = self.youtube.get_channel_videos(
                channel_url,
                limit=limit,
                existing_video_ids=existing_video_ids
            )

            # Apply date filter if specified
            if self.date_from or self.date_to:
                videos_metadata = [v for v in all_videos if self._should_process_video_by_date(v)]
                logger.info(f"Filtered {len(all_videos)} videos to {len(videos_metadata)} within date range")
            else:
                videos_metadata = all_videos

        # For component-specific modes, load existing videos from TSV
        if skip_video_fetch and not videos_metadata:
            logger.info("Loading existing videos for component-specific update...")
            import csv
            videos_tsv_path = self.repo_path / "videos" / "videos.tsv"

            if videos_tsv_path.exists():
                # Read existing videos from TSV
                total_videos = 0
                with open(videos_tsv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter='\t')
                    for row in reader:
                        total_videos += 1
                        video_id = row.get("video_id")
                        video_path_str = row.get("path")
                        if video_id and video_path_str:
                            # Load metadata from disk
                            video_path = self.repo_path / "videos" / video_path_str
                            metadata_path = video_path / "metadata.json"
                            if metadata_path.exists():
                                with open(metadata_path) as f:
                                    video_meta = json.load(f)
                                    # Apply date filter
                                    if self._should_process_video_by_date(video_meta):
                                        videos_metadata.append(video_meta)

                if self.date_from or self.date_to:
                    logger.info(f"Loaded {len(videos_metadata)} videos (from {total_videos} total) matching date filter")
                else:
                    logger.info(f"Loaded {len(videos_metadata)} existing videos from TSV")
            else:
                logger.warning("No videos.tsv found, cannot process component updates")
                return stats

        if not videos_metadata:
            logger.warning("No videos found")
            return stats

        logger.info(f"Found {len(videos_metadata)} videos to process")

        # Process each video (fail-fast: errors will propagate)
        for i, video_meta in enumerate(videos_metadata, 1):
            logger.info(f"Processing video {i}/{len(videos_metadata)}: {video_meta.get('title', 'Unknown')}")
            video = self.youtube.metadata_to_video(video_meta)
            caption_count = self._process_video(video)

            stats["videos_processed"] += 1
            stats["videos_tracked"] += 1
            stats["metadata_saved"] += 1
            stats["captions_downloaded"] += caption_count

        # Commit changes
        self.git_annex.add_and_commit(
            f"Backup channel: {channel_url} ({stats['videos_processed']} videos)"
        )

        logger.info(f"Backup complete: {stats['videos_processed']} videos processed")

        # Auto-discover and backup playlists if configured AND mode allows playlist processing
        # Component-specific modes (comments, captions, social) should not process playlists
        if (source_config and source_config.include_playlists != "none" and
                self._should_process_component("playlists")):
            logger.info("Discovering playlists from channel...")
            playlist_urls = self._discover_playlists(
                channel_url,
                source_config.include_playlists,
                source_config.exclude_playlists,
                source_config.include_podcasts
            )

            # Playlist errors will propagate (fail-fast)
            for playlist_url in playlist_urls:
                playlist_stats = self.backup_playlist(playlist_url)
                stats["videos_processed"] += playlist_stats.get("videos_processed", 0)
                stats["videos_tracked"] += playlist_stats.get("videos_tracked", 0)
                stats["metadata_saved"] += playlist_stats.get("metadata_saved", 0)
                stats["captions_downloaded"] += playlist_stats.get("captions_downloaded", 0)
                stats["errors"].extend(playlist_stats.get("errors", []))

        # Generate TSV metadata files (non-critical, can be regenerated later)
        try:
            logger.info("Generating TSV metadata files")
            self.export.generate_all()
            self.git_annex.add_and_commit("Update TSV metadata files")
        except Exception as e:
            logger.warning(f"Failed to generate TSV files: {e}")

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

        # Get playlist metadata
        playlist = self.youtube.get_playlist_metadata(playlist_url)
        if not playlist:
            raise ValueError(f"Failed to fetch playlist metadata for {playlist_url}")

        # Create playlist directory
        playlist_dir = self._get_playlist_path(playlist)
        playlist_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Playlist directory: {playlist_dir}")

        # Get playlist videos
        limit = self.config.filters.limit
        all_videos = self.youtube.get_playlist_videos(playlist_url, limit=limit)

        # Apply date filter if specified
        if self.date_from or self.date_to:
            videos_metadata = [v for v in all_videos if self._should_process_video_by_date(v)]
            logger.info(f"Filtered {len(all_videos)} videos to {len(videos_metadata)} within date range")
        else:
            videos_metadata = all_videos

        if not videos_metadata:
            logger.warning("No videos found in playlist (after date filtering)")
            return stats

        logger.info(f"Found {len(videos_metadata)} videos in playlist")

        # Check if playlist content changed (for incremental modes)
        playlist_changed = True
        metadata_path = playlist_dir / "playlist.json"

        if metadata_path.exists() and self.update_mode in ["videos-incremental", "all-incremental"]:
            try:
                with open(metadata_path, 'r') as f:
                    old_data = json.load(f)
                    old_video_ids = [v['video_id'] for v in old_data.get('videos', [])]
                    new_video_ids = [v.get('id') for v in videos_metadata if v.get('id')]

                    if old_video_ids == new_video_ids:
                        playlist_changed = False
                        logger.info(f"Playlist content unchanged, skipping update: {playlist.title}")
            except Exception as e:
                logger.debug(f"Failed to compare playlist content: {e}")
                playlist_changed = True

        # Only update playlist metadata if content changed
        if playlist_changed:
            with AtomicFileWriter(metadata_path) as f:
                json.dump(playlist.to_dict(), f, indent=2)
            logger.debug(f"Saved playlist metadata: {metadata_path}")

        # Skip video processing in playlists mode if content unchanged
        if not playlist_changed and self.update_mode == "playlists":
            logger.info("Playlist content unchanged, skipping video processing")
            return stats

        # Get prefix width and separator for ordered symlinks
        prefix_width = self.config.organization.playlist_prefix_width
        separator = self.config.organization.playlist_prefix_separator

        # Process each video and create ordered symlinks (fail-fast)
        for i, video_meta in enumerate(videos_metadata, 1):
            video = self.youtube.metadata_to_video(video_meta)
            video_id = video.video_id

            # Check if video was already processed in this run (e.g., from channel backup)
            if video_id in self._processed_video_ids:
                logger.info(f"Video {i}/{len(videos_metadata)} already processed in this run: {video.title}")
                caption_count = 0
            else:
                logger.info(f"Processing video {i}/{len(videos_metadata)}: {video_meta.get('title', 'Unknown')}")
                # Process video (creates video directory with content)
                caption_count = self._process_video(video)

                stats["videos_processed"] += 1
                stats["videos_tracked"] += 1
                stats["metadata_saved"] += 1
                stats["captions_downloaded"] += caption_count

            # Create ordered symlink in playlist directory (even if already processed)
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

        # Commit changes
        self.git_annex.add_and_commit(
            f"Backup playlist: {playlist.title} ({stats['videos_processed']} videos)"
        )

        logger.info(f"Backup complete: {stats['videos_processed']} videos processed")

        # Generate TSV metadata files (non-critical, can be regenerated later)
        try:
            logger.info("Generating TSV metadata files")
            self.export.generate_all()
            self.git_annex.add_and_commit("Update TSV metadata files")
        except Exception as e:
            logger.warning(f"Failed to generate TSV files: {e}")

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

        # Calculate expected path using configurable pattern
        expected_path = self._get_video_path(video)

        # Detect if this is a NEW video (metadata.json doesn't exist yet)
        # NEW videos should get ALL configured components regardless of update mode
        metadata_path = expected_path / "metadata.json"
        is_new_video = not metadata_path.exists()

        # Log whether this is a new or existing video
        if is_new_video:
            logger.info(f"Processing NEW video: {video.title}")
        else:
            logger.debug(f"Updating EXISTING video: {video.title}")

        # Check if we should skip this video (for incremental modes)
        if self.update_mode in ["videos-incremental", "all-incremental"]:
            # Skip if metadata.json already exists (video already processed)
            if not is_new_video:  # Use our detection instead of checking again
                logger.debug(f"Skipping already-processed video: {video.video_id}")
                # For all-incremental, still check if we need to update social data
                if self.update_mode == "all-incremental":
                    # TODO: Implement social data updates for recent videos
                    pass
                return 0

        # Continue with path calculation

        # Check if video needs renaming (path pattern changed)
        video_dir = self._rename_video_if_needed(video, expected_path)

        # Create directory if it doesn't exist (new videos)
        video_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Video directory: {video_dir}")

        # Save metadata
        metadata_path = video_dir / "metadata.json"
        with AtomicFileWriter(metadata_path) as f:
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

        # Download thumbnail (if enabled and mode allows)
        # For NEW videos: always fetch if configured, regardless of mode
        # For EXISTING videos: respect component-specific mode
        should_fetch_thumbnail = self.config.components.thumbnails and video.thumbnail_url and \
                               (is_new_video or self._should_process_component("metadata"))
        if should_fetch_thumbnail:
            self._download_thumbnail(video, video_dir)

        # Download captions (if enabled and mode allows)
        # For NEW videos: always try to fetch if configured (we don't know what's available yet)
        # For EXISTING videos: only fetch if captions exist and mode allows it
        caption_count = 0
        if is_new_video:
            # New video: try to download if captions enabled, regardless of what metadata says
            should_fetch_captions = self.config.components.captions
        else:
            # Existing video: only download if captions available and mode allows
            should_fetch_captions = self.config.components.captions and video.captions_available and \
                                   self._should_process_component("captions")
        if should_fetch_captions:
            downloaded_captions = self._download_captions(video, video_dir)
            caption_count = len(downloaded_captions)

            # Update video metadata with actually downloaded captions
            if downloaded_captions:
                video.captions_available = downloaded_captions
                # Re-save metadata with updated captions_available
                metadata_path = video_dir / "metadata.json"
                with AtomicFileWriter(metadata_path) as f:
                    json.dump(video.to_dict(), f, indent=2)
                logger.debug(f"Updated metadata with {len(downloaded_captions)} downloaded captions")

        # Download comments (if enabled and mode allows)
        # For NEW videos: always fetch if configured, regardless of mode
        # For EXISTING videos: respect component-specific mode
        # comments_depth: None = unlimited, 0 = disabled, N = limit to N
        comments_fetched = False
        should_fetch_comments = self.config.components.comments_depth != 0 and \
                               (is_new_video or self._should_process_component("comments"))
        if should_fetch_comments:
            comments_path = video_dir / "comments.json"
            comments_fetched = self.youtube.download_comments(
                video.video_id,
                comments_path,
                max_depth=self.config.components.comments_depth
            )

            # Set git-annex metadata for comments file
            if comments_fetched and comments_path.exists():
                metadata = {
                    'video_id': video.video_id,
                    'title': video.title,
                    'channel': video.channel_name,
                    'published': video.published_at.strftime('%Y-%m-%d'),
                    'filetype': 'comments',
                }
                self.git_annex.set_metadata_if_changed(comments_path, metadata)

        # Track that this video was processed in this run
        self._processed_video_ids.add(video.video_id)

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

    def _download_captions(self, video: Video, video_dir: Path) -> List[str]:
        """Download video captions, generate captions.tsv, and set git-annex metadata.

        Captions are saved directly in video directory (not captions/ subdirectory)
        for automatic discovery by video players.

        Args:
            video: Video model instance
            video_dir: Video directory path

        Returns:
            List of downloaded caption language codes
        """
        try:
            # Save captions directly in video directory (not subdirectory)
            # This allows video players to auto-discover them
            # Use caption settings from config
            language_pattern = self.config.components.caption_languages
            auto_translated_langs = self.config.components.auto_translated_captions

            # Extract video base filename (without extension) to match video file
            # e.g., "video.mkv" -> "video"
            video_filename = self.config.organization.video_filename
            base_filename = Path(video_filename).stem

            captions_metadata = self.youtube.download_captions(
                video.video_id,
                video_dir,
                language_pattern=language_pattern,
                auto_translated_langs=auto_translated_langs,
                base_filename=base_filename
            )

            if captions_metadata:
                # Create captions.tsv with metadata
                captions_tsv_path = video_dir / "captions.tsv"
                with AtomicFileWriter(captions_tsv_path) as f:
                    # Write header (added auto_translated column)
                    f.write("language_code\tauto_generated\tauto_translated\tfile_path\tfetched_at\n")
                    # Write caption rows and set git-annex metadata
                    for caption in captions_metadata:
                        f.write(
                            f"{caption['language_code']}\t"
                            f"{caption['auto_generated']}\t"
                            f"{caption.get('auto_translated', False)}\t"
                            f"{caption['file_path']}\t"
                            f"{caption['fetched_at']}\n"
                        )

                        # Set git-annex metadata for each caption file
                        # Only updates if file is in git-annex (based on .gitattributes)
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
                            'auto_translated': str(caption.get('auto_translated', False)),
                        }
                        self.git_annex.set_metadata_if_changed(caption_file_path, metadata)

                logger.debug(f"Downloaded {len(captions_metadata)} caption files and created captions.tsv")
                # Return list of language codes
                return sorted([c['language_code'] for c in captions_metadata])

        except Exception as e:
            logger.warning(f"Failed to download captions: {e}")

        return []
