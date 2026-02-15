"""Archiver service - core archival logic."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from annextube.lib.config import Config, SourceConfig
from annextube.lib.file_utils import AtomicFileWriter
from annextube.lib.logging_config import get_logger
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
                 date_from: datetime | None = None, date_to: datetime | None = None):
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

        # Parse extractor args and remote components from ytdlp_extra_opts
        extractor_args = self._parse_extractor_args(config.user.ytdlp_extra_opts)
        remote_components = self._parse_remote_components(config.user.ytdlp_extra_opts)

        # Initialize YouTubeService with user config settings
        self.youtube = YouTubeService(
            cookies_file=config.user.cookies_file,
            cookies_from_browser=config.user.cookies_from_browser,
            proxy=config.user.proxy,
            limit_rate=config.user.limit_rate,
            sleep_interval=config.user.sleep_interval,
            max_sleep_interval=config.user.max_sleep_interval,
            extractor_args=extractor_args,
            remote_components=remote_components,
            youtube_api_key=config.user.api_key,
            rate_limit_max_wait_seconds=config.user.rate_limit_max_wait_seconds,
            yt_dlp_max_parallel=config.user.yt_dlp_max_parallel,
        )

        self.export = ExportService(repo_path)
        self._video_id_to_path_cache: dict[str, str] | None = None  # Cache for video ID to path mapping (for rename detection)
        self._video_id_map_cache: dict[str, Path] | None = None  # Cache for _build_video_id_map
        self._processed_video_ids: set[str] = set()  # Track videos processed in current run (avoid duplicates)
        self._current_source_config: SourceConfig | None = None  # Current source being processed (for component overrides)
        self._is_initial_backup: bool | None = None  # Set at start of backup_channel/backup_playlist

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

    def _get_component_value(self, component: str) -> Any:
        """Get effective component value (source override or global config).

        Args:
            component: Component name (videos, metadata, comments_depth, captions, thumbnails)

        Returns:
            Effective component value
        """
        # Check if current source has an override
        if self._current_source_config:
            override = getattr(self._current_source_config, component, None)
            if override is not None:
                return override

        # Fall back to global config
        return getattr(self.config.components, component)

    def _parse_extractor_args(self, ytdlp_extra_opts: list[str]) -> dict:
        """Parse ytdlp_extra_opts CLI-style options to Python API extractor_args format.

        Converts ["--extractor-args", "youtube:player_client=android"]
        to {"youtube": {"player_client": ["android"]}}

        Args:
            ytdlp_extra_opts: List of CLI-style yt-dlp options

        Returns:
            Dictionary of extractor arguments for yt-dlp Python API
        """
        extractor_args: dict[str, dict[str, list[str]]] = {}

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

    def _parse_remote_components(self, ytdlp_extra_opts: list[str]) -> str | None:
        """Parse --remote-components option from ytdlp_extra_opts.

        Converts ["--remote-components", "ejs:github"] to "ejs:github"

        Args:
            ytdlp_extra_opts: List of CLI-style yt-dlp options

        Returns:
            Remote components value or None if not found
        """
        i = 0
        while i < len(ytdlp_extra_opts):
            opt = ytdlp_extra_opts[i]

            if opt == "--remote-components" and i + 1 < len(ytdlp_extra_opts):
                return ytdlp_extra_opts[i + 1]

            i += 1

        return None

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

    def _has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes in the repository.

        Returns:
            True if there are staged or unstaged changes
        """
        import subprocess
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.repo_path,
            capture_output=True,
            encoding="utf-8",
            check=True
        )
        return bool(result.stdout.strip())

    def _checkpoint(self, channel_url: str, videos_processed: int, total_videos: int) -> None:
        """Create a checkpoint by regenerating TSVs and committing progress.

        Args:
            channel_url: URL of the channel being backed up
            videos_processed: Number of videos processed so far
            total_videos: Total number of videos to process
        """
        if not self._has_uncommitted_changes():
            logger.debug("No uncommitted changes, skipping checkpoint")
            return

        logger.info(f"Checkpoint: {videos_processed}/{total_videos} videos processed")

        # Regenerate only videos.tsv during checkpoint (not all playlists TSVs)
        try:
            self.export.generate_videos_tsv()
        except Exception as e:
            logger.warning(f"Failed to regenerate videos.tsv during checkpoint: {e}")
            # Continue with commit anyway - TSVs can be regenerated later

        # Commit staged changes
        try:
            self.git_annex.add_and_commit(
                f"Checkpoint: {channel_url} ({videos_processed}/{total_videos} videos)"
            )
        except Exception as e:
            logger.error(f"Failed to commit checkpoint: {e}")
            raise

    def _load_video_paths(self) -> dict[str, str]:
        """Load existing video ID to path mapping from videos.tsv.

        Returns:
            Dictionary mapping video_id to current path
        """
        videos_tsv = self.repo_path / "videos" / "videos.tsv"
        if not videos_tsv.exists():
            return {}

        video_map = {}
        try:
            with open(videos_tsv, encoding='utf-8') as f:
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

        assert self._video_id_to_path_cache is not None  # Type narrowing for mypy
        # Check if this video already exists with a different path
        existing_rel_path = self._video_id_to_path_cache.get(video.video_id)
        if not existing_rel_path:
            # New video, no rename needed
            return new_path

        existing_path: Path = self.repo_path / "videos" / existing_rel_path

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
                encoding="utf-8",
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
                date_obj = video.published_at
                date_str = date_obj.strftime('%Y-%m-%d')
                year_str = date_obj.strftime('%Y')
                month_str = date_obj.strftime('%m')
            else:
                # If it's a string, parse it
                date_obj = datetime.fromisoformat(str(video.published_at).replace('Z', '+00:00'))
                date_str = date_obj.strftime('%Y-%m-%d')
                year_str = date_obj.strftime('%Y')
                month_str = date_obj.strftime('%m')
        except Exception as e:
            logger.warning(f"Failed to parse date from published_at: {e}")
            date_str = 'unknown'
            year_str = 'unknown'
            month_str = 'unknown'

        # Build placeholders
        placeholders = {
            'date': date_str,
            'year': year_str,
            'month': month_str,
            'video_id': video.video_id,
            'sanitized_title': sanitize_filename(video.title),
            'channel_id': video.channel_id,
            'channel_name': sanitize_filename(video.channel_name),
        }

        # Replace placeholders in pattern using .format()
        # This will raise KeyError if pattern contains unknown placeholders
        try:
            path_str = pattern.format(**placeholders)
        except KeyError as e:
            raise ValueError(
                f"Unknown placeholder {e} in video_path_pattern: {pattern}. "
                f"Valid placeholders: {', '.join(sorted(placeholders.keys()))}"
            ) from e

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

        # Replace placeholders in pattern using .format()
        # This will raise KeyError if pattern contains unknown placeholders
        try:
            path_str = pattern.format(**placeholders)
        except KeyError as e:
            raise ValueError(
                f"Unknown placeholder {e} in playlist_path_pattern: {pattern}. "
                f"Valid placeholders: {', '.join(sorted(placeholders.keys()))}"
            ) from e

        return self.repo_path / "playlists" / path_str

    def _get_playlist_symlink_name(self, video_dir: Path, playlist_index: int) -> str:
        """Generate playlist symlink name from playlist_video_pattern.

        Args:
            video_dir: Path to video directory
            playlist_index: 1-based position in playlist

        Returns:
            Symlink filename (e.g., "0001_video-title")
        """
        pattern = self.config.organization.playlist_video_pattern

        # Build placeholders
        placeholders = {
            'video_index': playlist_index,
            'video_path_basename': video_dir.name,
        }

        # Replace placeholders in pattern using .format()
        try:
            symlink_name = pattern.format(**placeholders)
        except KeyError as e:
            raise ValueError(
                f"Unknown placeholder {e} in playlist_video_pattern: {pattern}. "
                f"Valid placeholders: {', '.join(sorted(placeholders.keys()))}"
            ) from e

        return symlink_name

    def _build_video_id_map(self, use_cache: bool = True) -> dict[str, Path]:
        """Build mapping from video_id to video directory path.

        Scans all metadata.json files in videos/ directory to build the map.

        Args:
            use_cache: If True, return cached result if available

        Returns:
            Dictionary mapping video_id to absolute video directory Path
        """
        if use_cache and self._video_id_map_cache is not None:
            return self._video_id_map_cache

        videos_dir = self.repo_path / "videos"
        video_id_map: dict[str, Path] = {}

        if not videos_dir.exists():
            return video_id_map

        for metadata_path in videos_dir.rglob("metadata.json"):
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                video_id = metadata.get("video_id")
                if video_id:
                    video_id_map[video_id] = metadata_path.parent
            except Exception as e:
                logger.debug(f"Failed to read {metadata_path}: {e}")

        if use_cache:
            self._video_id_map_cache = video_id_map
        return video_id_map

    def _invalidate_video_id_map_cache(self) -> None:
        """Invalidate the video_id_map cache, forcing a fresh scan on next call."""
        self._video_id_map_cache = None

    def _save_playlist_metadata(self, playlist: Playlist, playlist_dir: Path) -> bool:
        """Save playlist.json if content changed.

        Args:
            playlist: Playlist model instance
            playlist_dir: Path to playlist directory

        Returns:
            True if saved (new or changed), False if unchanged
        """
        metadata_path = playlist_dir / "playlist.json"
        if metadata_path.exists() and self.update_mode in ["videos-incremental", "all-incremental"]:
            try:
                with open(metadata_path) as f:
                    old_data = json.load(f)
                old_ids = old_data.get('video_ids', [])
                if old_ids == playlist.video_ids:
                    return False
            except Exception:
                pass
        with AtomicFileWriter(metadata_path) as f:
            json.dump(playlist.to_dict(), f, indent=2)
        return True

    def _compute_desired_symlinks(
        self, playlist: Playlist, video_id_map: dict[str, Path]
    ) -> list[tuple[datetime, str, Path]]:
        """Compute desired symlink list sorted by (published_at, video_id).

        Args:
            playlist: Playlist model with video_ids
            video_id_map: Mapping from video_id to video directory path

        Returns:
            Sorted list of (published_at, video_id, video_dir) tuples
        """
        videos_with_dates: list[tuple[datetime, str, Path]] = []
        for video_id in playlist.video_ids:
            video_dir = video_id_map.get(video_id)
            if not video_dir:
                logger.debug(f"Video {video_id} not found in archive, skipping symlink")
                continue

            # Read published_at from metadata
            metadata_path = video_dir / "metadata.json"
            published_at = datetime.min  # fallback for missing dates
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                published_str = metadata.get("published_at", "")
                if published_str:
                    published_at = datetime.fromisoformat(
                        published_str.replace('Z', '+00:00')
                    )
            except Exception as e:
                logger.debug(f"Failed to read published_at for {video_id}: {e}")

            videos_with_dates.append((published_at, video_id, video_dir))

        videos_with_dates.sort(key=lambda x: (x[0], x[1]))
        return videos_with_dates

    def _read_existing_symlink_order(self, playlist_dir: Path) -> list[tuple[str, Path]]:
        """Read existing symlinks in order and extract video_ids from targets.

        Args:
            playlist_dir: Path to playlist directory

        Returns:
            List of (video_id, symlink_path) tuples in current order
        """
        existing: list[tuple[str, Path]] = []
        symlinks = sorted(
            [f for f in playlist_dir.iterdir() if f.is_symlink()],
            key=lambda p: p.name
        )
        for symlink in symlinks:
            try:
                target = symlink.resolve()
                metadata_path = target / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    video_id = metadata.get("video_id", "")
                    if video_id:
                        existing.append((video_id, symlink))
            except Exception as e:
                logger.debug(f"Failed to read symlink target {symlink.name}: {e}")
        return existing

    def _update_playlist_symlinks(
        self, playlist_dir: Path, playlist: Playlist, video_id_map: dict[str, Path]
    ) -> bool:
        """Update playlist symlinks, only changing what's different.

        Compares desired state vs existing state. If unchanged, skips entirely
        (common case for incremental backups). When different, does a full
        rebuild since index-based names shift on any insertion/deletion.

        Args:
            playlist_dir: Path to playlist directory
            playlist: Playlist model with video_ids
            video_id_map: Pre-built mapping from video_id to video directory

        Returns:
            True if symlinks were changed, False if already up-to-date
        """
        # Compute desired state
        desired = self._compute_desired_symlinks(playlist, video_id_map)

        # Read existing symlinks
        existing = self._read_existing_symlink_order(playlist_dir)

        # Compare ordered video_id lists
        desired_ids = [vid for _, vid, _ in desired]
        existing_ids = [vid for vid, _ in existing]

        if desired_ids == existing_ids:
            logger.info(f"Symlinks unchanged for {playlist_dir.name}")
            return False

        # Different — remove all old symlinks, recreate all
        for item in playlist_dir.iterdir():
            if item.is_symlink():
                item.unlink()

        for index, (_, _, video_dir) in enumerate(desired, 1):
            symlink_name = self._get_playlist_symlink_name(video_dir, index)
            relative_target = Path("..") / ".." / video_dir.relative_to(self.repo_path)
            (playlist_dir / symlink_name).symlink_to(relative_target)

        logger.info(
            f"Updated {len(desired)} symlinks in {playlist_dir.name} "
            f"(chronological order)"
        )
        return True

    def _rebuild_playlist_symlinks(self, playlist_dir: Path, playlist: Playlist) -> None:
        """Rebuild all symlinks in a playlist directory from scratch.

        Unconditionally removes existing symlinks and recreates them.
        Uses _compute_desired_symlinks for consistent ordering logic.

        Args:
            playlist_dir: Path to playlist directory
            playlist: Playlist model with video_ids
        """
        video_id_map = self._build_video_id_map(use_cache=False)

        # Remove all existing symlinks
        for item in playlist_dir.iterdir():
            if item.is_symlink():
                item.unlink()

        # Compute desired order and create symlinks
        desired = self._compute_desired_symlinks(playlist, video_id_map)
        for index, (_, _, video_dir) in enumerate(desired, 1):
            symlink_name = self._get_playlist_symlink_name(video_dir, index)
            relative_target = Path("..") / ".." / video_dir.relative_to(self.repo_path)
            (playlist_dir / symlink_name).symlink_to(relative_target)

        logger.info(
            f"Rebuilt {len(desired)} symlinks in {playlist_dir.name} "
            f"(chronological order)"
        )

    def _discover_playlists(self, channel_url: str, include_pattern: str,
                           exclude_pattern: str | None, include_podcasts: str) -> list[str]:
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
                    podcasts = [p for p in podcasts if pattern.search(p.get('title') or '')]
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
                playlists = [p for p in playlists if pattern.search(p.get('title') or '')]
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
                playlists = [p for p in playlists if not pattern.search(p.get('title') or '')]
                logger.info(f"Exclude filter '{exclude_pattern}' removed {original_count - len(playlists)} playlists")
            except re.error as e:
                logger.error(f"Invalid exclude_playlists regex '{exclude_pattern}': {e}")

        # Log discovered playlists
        if playlists:
            logger.info(f"Will backup {len(playlists)} playlists:")
            for p in playlists:
                logger.info(f"  - {p['title']} ({p['video_count']} videos)")

        return [p['url'] for p in playlists]

    def backup_channel(self, channel_url: str, source_config: SourceConfig | None = None) -> dict:
        """Backup a YouTube channel.

        Phased flow:
          Phase 1: Channel video discovery
          Phase 2: Playlist discovery (identifies playlist-exclusive videos)
          Phase 3: Video processing (channel + exclusive videos)
          Phase 4: Playlist composition (save metadata + diff-based symlinks)
          Phase 5: TSV generation (single generate_all())

        Args:
            channel_url: YouTube channel URL
            source_config: Optional source configuration for playlists and component overrides

        Returns:
            Summary dictionary with statistics
        """
        # Set current source for component overrides
        self._current_source_config = source_config
        self._is_initial_backup = not (self.repo_path / "videos" / "videos.tsv").exists()
        logger.info(f"Starting backup for channel: {channel_url} (mode: {self.update_mode})")

        stats: dict[str, Any] = {
            "channel_url": channel_url,
            "videos_processed": 0,
            "videos_tracked": 0,
            "metadata_saved": 0,
            "captions_downloaded": 0,
            "errors": [],
        }

        # ── Phase 1: Channel video discovery ──────────────────────────────
        limit = self.config.filters.limit
        existing_video_ids = None
        videos_metadata: list[dict[str, Any]] = []

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
            else:
                logger.info("No existing videos.tsv found, performing full initial backup")

        # Fetch videos (unless in component-specific mode)
        if not skip_video_fetch:
            all_videos = self.youtube.get_channel_videos(
                channel_url,
                limit=limit,
                existing_video_ids=existing_video_ids
            )

            # Apply date filter only for non-incremental, non-initial backups.
            is_initial_backup = not existing_video_ids
            is_incremental = existing_video_ids is not None and len(existing_video_ids) > 0
            if (self.date_from or self.date_to) and not is_initial_backup and not is_incremental:
                videos_metadata = [v for v in all_videos if self._should_process_video_by_date(v)]
                logger.info(f"Filtered {len(all_videos)} videos to {len(videos_metadata)} within date range")
            else:
                videos_metadata = all_videos
                if is_initial_backup and (self.date_from or self.date_to):
                    logger.info(f"Skipping date filter on initial backup - processing all {len(all_videos)} videos")
                elif is_incremental and (self.date_from or self.date_to):
                    logger.info(f"Skipping date filter in incremental mode - processing all {len(all_videos)} new videos")

        # For component-specific modes, load existing videos from TSV
        if skip_video_fetch and not videos_metadata:
            logger.info("Loading existing videos for component-specific update...")
            import csv
            videos_tsv_path = self.repo_path / "videos" / "videos.tsv"

            if videos_tsv_path.exists():
                total_videos = 0
                with open(videos_tsv_path, encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter='\t')
                    for row in reader:
                        total_videos += 1
                        video_id = row.get("video_id")
                        video_path_str = row.get("path")
                        if video_id and video_path_str:
                            video_path = self.repo_path / "videos" / video_path_str
                            metadata_path = video_path / "metadata.json"
                            if metadata_path.exists():
                                with open(metadata_path) as f:
                                    video_meta = json.load(f)
                                    if self._should_process_video_by_date(video_meta):
                                        videos_metadata.append(video_meta)

                if self.date_from or self.date_to:
                    logger.info(f"Loaded {len(videos_metadata)} videos (from {total_videos} total) matching date filter")
                else:
                    logger.info(f"Loaded {len(videos_metadata)} existing videos from TSV")
            else:
                logger.warning("No videos.tsv found, cannot process component updates")
                return stats

        # ── Phase 2: Playlist discovery (BEFORE video processing) ─────────
        playlists_info: list[tuple[Playlist, Path, str]] = []  # (playlist, playlist_dir, url)

        if (source_config and source_config.include_playlists != "none" and
                self._should_process_component("playlists")):
            logger.info("Discovering playlists from channel...")
            playlist_urls = self._discover_playlists(
                channel_url,
                source_config.include_playlists,
                source_config.exclude_playlists,
                source_config.include_podcasts
            )

            # Build set of channel video IDs for exclusive detection
            channel_video_ids: set[str] = set()
            for v in videos_metadata:
                vid = v.get('id') or v.get('video_id')
                if vid:
                    channel_video_ids.add(vid)

            exclusive_video_ids: list[str] = []

            for url in playlist_urls:
                playlist = self.youtube.get_playlist_metadata(url)
                if not playlist:
                    logger.warning(f"Failed to fetch playlist metadata for {url}, skipping")
                    continue
                playlist_dir = self._get_playlist_path(playlist)
                playlist_dir.mkdir(parents=True, exist_ok=True)
                playlists_info.append((playlist, playlist_dir, url))

                # Collect playlist-exclusive video IDs
                for vid in playlist.video_ids:
                    if vid not in channel_video_ids:
                        exclusive_video_ids.append(vid)

            # Deduplicate exclusive IDs (preserve order)
            exclusive_video_ids = list(dict.fromkeys(exclusive_video_ids))

            # Fetch full metadata for exclusive videos
            if exclusive_video_ids and self.update_mode != "playlists":
                logger.info(f"Found {len(exclusive_video_ids)} playlist-exclusive video(s), fetching metadata")
                exclusive_meta = self.youtube.get_videos_metadata(exclusive_video_ids)
                videos_metadata.extend(exclusive_meta)

        if not videos_metadata and not playlists_info:
            logger.warning("No videos found")
            return stats

        # ── Phase 3: Video processing (ALL videos: channel + exclusive) ───
        if self.update_mode != "playlists" and videos_metadata:
            logger.info(f"Found {len(videos_metadata)} videos to process")

            # Batch pre-fetch API data for efficiency
            prefetched_stats: dict[str, dict[str, int]] | None = None
            api_metadata_cache: dict[str, dict] | None = None

            if self.youtube.api_client:
                if self.update_mode == "all-incremental":
                    existing_ids: list[str] = [
                        vid
                        for v in videos_metadata
                        if v.get("video_id")
                        for vid in [v.get("video_id") or v.get("id")]
                        if vid is not None
                    ]
                    if existing_ids:
                        logger.info(f"Batch-fetching statistics for {len(existing_ids)} existing video(s)")
                        try:
                            prefetched_stats = self.youtube.api_client.batch_get_video_statistics(existing_ids)
                            logger.info(f"Pre-fetched statistics for {len(prefetched_stats)} video(s)")
                        except Exception as e:
                            logger.warning(f"Failed to batch-fetch statistics: {e}")

                new_video_ids: list[str] = [
                    v["id"]
                    for v in videos_metadata
                    if v.get("id") and not v.get("video_id")
                ]
                if new_video_ids:
                    logger.info(f"Batch-fetching API metadata for {len(new_video_ids)} new video(s)")
                    try:
                        api_metadata_cache = self.youtube.api_client.batch_enhance_video_metadata(new_video_ids)
                        logger.info(f"Pre-fetched API metadata for {len(api_metadata_cache)} video(s)")
                    except Exception as e:
                        logger.warning(f"Failed to batch-fetch API metadata: {e}")

            # Process each video with checkpoint support
            checkpoint_interval = self.config.backup.checkpoint_interval if self.config.backup.checkpoint_enabled else 0

            try:
                for i, video_meta in enumerate(videos_metadata, 1):
                    logger.info(f"Processing video {i}/{len(videos_metadata)}: {video_meta.get('title', 'Unknown')}")
                    video = self.youtube.metadata_to_video(video_meta, api_metadata_cache=api_metadata_cache)
                    caption_count = self._process_video(video, prefetched_stats=prefetched_stats)

                    stats["videos_processed"] += 1
                    stats["videos_tracked"] += 1
                    stats["metadata_saved"] += 1
                    stats["captions_downloaded"] += caption_count

                    # Periodic checkpoint
                    if checkpoint_interval > 0 and i % checkpoint_interval == 0 and i < len(videos_metadata):
                        self._checkpoint(channel_url, i, len(videos_metadata))

                # Final commit for video work
                if self._has_uncommitted_changes():
                    self.git_annex.add_and_commit(
                        f"Backup channel: {channel_url} ({stats['videos_processed']} videos)"
                    )

            except KeyboardInterrupt:
                logger.warning("Backup interrupted by user (Ctrl+C)")

                if self.config.backup.auto_commit_on_interrupt and self._has_uncommitted_changes():
                    logger.info(f"Auto-committing partial progress ({stats['videos_processed']} videos processed)...")
                    try:
                        self.export.generate_all()
                        self.git_annex.add_and_commit(
                            f"Partial backup (interrupted): {channel_url} ({stats['videos_processed']} videos)"
                        )
                        logger.info("Partial progress committed successfully")
                    except Exception as e:
                        logger.error(f"Failed to commit partial progress: {e}")
                        logger.info("Uncommitted changes remain. Run 'git status' to inspect.")

                raise

            logger.info(f"Backup complete: {stats['videos_processed']} videos processed")
        elif self.update_mode == "playlists":
            logger.info("Playlists mode: skipping video processing")

        # ── Phase 4: Playlist composition ─────────────────────────────────
        if playlists_info:
            self._invalidate_video_id_map_cache()
            video_id_map = self._build_video_id_map()

            for playlist, playlist_dir, _url in playlists_info:
                self._save_playlist_metadata(playlist, playlist_dir)
                self._update_playlist_symlinks(playlist_dir, playlist, video_id_map)

            # Single commit for all playlist work
            if self._has_uncommitted_changes():
                self.git_annex.add_and_commit(
                    f"Update playlists ({len(playlists_info)} playlists)"
                )

        # ── Phase 5: TSV generation ───────────────────────────────────────
        try:
            logger.info("Generating TSV metadata files")
            self.export.generate_all()
            if self._has_uncommitted_changes():
                self.git_annex.add_and_commit("Update TSV metadata files")
        except Exception as e:
            logger.warning(f"Failed to generate TSV files: {e}")

        # Log API quota usage summary
        if self.youtube.api_client:
            summary = self.youtube.api_client.get_quota_summary()
            if summary["total_units"] > 0:
                calls_str = ", ".join(f"{k}: {v}" for k, v in summary["calls"].items())
                logger.info(
                    f"YouTube API quota used: {summary['total_units']} unit(s) "
                    f"({calls_str})"
                )

        return stats

    def backup_playlist(self, playlist_url: str, source_config: SourceConfig | None = None) -> dict:
        """Backup a YouTube playlist (standalone entry point).

        Complete self-contained flow for ad-hoc playlist backup:
        fetch metadata, process videos, compose symlinks, generate TSVs.

        Args:
            playlist_url: YouTube playlist URL
            source_config: Optional source configuration for component overrides

        Returns:
            Summary dictionary with statistics
        """
        # Set current source for component overrides
        self._current_source_config = source_config
        # Use instance-level is_initial_backup if set (by backup_channel),
        # otherwise check file existence
        if self._is_initial_backup is None:
            self._is_initial_backup = not (self.repo_path / "videos" / "videos.tsv").exists()
        logger.info(f"Starting backup for playlist: {playlist_url}")

        stats: dict[str, Any] = {
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
        incremental = self.update_mode in ["videos-incremental", "all-incremental", "playlists"]
        all_videos = self.youtube.get_playlist_videos(
            playlist_url,
            limit=limit,
            repo_path=self.repo_path,
            incremental=incremental
        )

        # Record unavailable videos so they're skipped on future runs
        fetched_ids: set[str] = set()
        for v in all_videos:
            vid = v.get("id") or v.get("video_id")
            if vid:
                fetched_ids.add(vid)
        self._save_unavailable_stubs(playlist, fetched_ids)

        # Apply date filter if specified (but NOT on initial backup)
        is_initial = self._is_initial_backup

        if (self.date_from or self.date_to) and not is_initial:
            videos_metadata = [v for v in all_videos if self._should_process_video_by_date(v)]
            logger.info(f"Filtered {len(all_videos)} videos to {len(videos_metadata)} within date range")
        else:
            videos_metadata = all_videos
            if is_initial and (self.date_from or self.date_to):
                logger.info(f"Skipping date filter on initial backup - processing all {len(all_videos)} videos")

        if not videos_metadata:
            logger.warning("No videos found in playlist (after date filtering)")
            return stats

        logger.info(f"Found {len(videos_metadata)} videos in playlist")

        # Save playlist metadata (with change detection)
        playlist_changed = self._save_playlist_metadata(playlist, playlist_dir)

        # Skip video processing in playlists mode if content unchanged
        if not playlist_changed and self.update_mode == "playlists":
            logger.info("Playlist content unchanged, skipping video processing")
            # Still update symlinks — video directories may have been added from channel backup
            self._invalidate_video_id_map_cache()
            video_id_map = self._build_video_id_map()
            self._update_playlist_symlinks(playlist_dir, playlist, video_id_map)
            return stats

        # Process each video with checkpoint support
        checkpoint_interval = self.config.backup.checkpoint_interval if self.config.backup.checkpoint_enabled else 0

        try:
            for i, video_meta in enumerate(videos_metadata, 1):
                video = self.youtube.metadata_to_video(video_meta)
                video_id = video.video_id

                # Check if video was already processed in this run (e.g., from channel backup)
                if video_id in self._processed_video_ids:
                    logger.info(f"Video {i}/{len(videos_metadata)} already processed in this run: {video.title}")
                else:
                    logger.info(f"Processing video {i}/{len(videos_metadata)}: {video_meta.get('title', 'Unknown')}")
                    caption_count = self._process_video(video)

                    stats["videos_processed"] += 1
                    stats["videos_tracked"] += 1
                    stats["metadata_saved"] += 1
                    stats["captions_downloaded"] += caption_count

                # Periodic checkpoint
                if checkpoint_interval > 0 and i % checkpoint_interval == 0 and i < len(videos_metadata):
                    self._checkpoint(playlist_url, i, len(videos_metadata))

            # Commit video work
            if self._has_uncommitted_changes():
                self.git_annex.add_and_commit(
                    f"Backup playlist: {playlist.title} ({stats['videos_processed']} videos)"
                )

        except KeyboardInterrupt:
            logger.warning("Backup interrupted by user (Ctrl+C)")

            if self.config.backup.auto_commit_on_interrupt and self._has_uncommitted_changes():
                logger.info(f"Auto-committing partial progress ({stats['videos_processed']} videos processed)...")
                try:
                    self.export.generate_all()
                    self.git_annex.add_and_commit(
                        f"Partial backup (interrupted): {playlist.title} ({stats['videos_processed']} videos)"
                    )
                    logger.info("Partial progress committed successfully")
                except Exception as e:
                    logger.error(f"Failed to commit partial progress: {e}")
                    logger.info("Uncommitted changes remain. Run 'git status' to inspect.")

            raise

        logger.info(f"Backup complete: {stats['videos_processed']} videos processed")

        # Compose symlinks
        self._invalidate_video_id_map_cache()
        video_id_map = self._build_video_id_map()
        self._update_playlist_symlinks(playlist_dir, playlist, video_id_map)

        # Generate TSV metadata files
        try:
            logger.info("Generating TSV metadata files")
            self.export.generate_all()
            if self._has_uncommitted_changes():
                self.git_annex.add_and_commit("Update TSV metadata files")
        except Exception as e:
            logger.warning(f"Failed to generate TSV files: {e}")

        return stats

    def _save_unavailable_stubs(self, playlist: Playlist, fetched_video_ids: set[str]) -> int:
        """Record unavailable playlist videos in .annextube/unavailable_videos.json.

        Compares playlist.video_ids against fetched + already-archived IDs
        to find unavailable videos and records them so
        _load_unavailable_videos() will skip them on subsequent runs.

        Args:
            playlist: Playlist model with full video_ids list
            fetched_video_ids: Set of video IDs that were successfully fetched

        Returns:
            Number of newly recorded unavailable video IDs
        """
        # Collect IDs that were explicitly detected as unavailable during extraction
        newly_unavailable = set(self.youtube._last_unavailable_ids)

        # Also find IDs in the playlist that weren't fetched and don't have metadata
        all_playlist_ids = set(playlist.video_ids)
        missing_ids = all_playlist_ids - fetched_video_ids

        # Check which missing IDs already have metadata.json in the archive
        video_id_map = self._build_video_id_map()

        for video_id in missing_ids:
            if video_id not in video_id_map:
                newly_unavailable.add(video_id)

        if not newly_unavailable:
            return 0

        # Load existing unavailable_videos.json
        unavail_path = self.repo_path / ".annextube" / "unavailable_videos.json"
        existing: dict[str, dict] = {}
        if unavail_path.exists():
            try:
                with open(unavail_path, encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load {unavail_path}: {e}")

        # Add new entries (skip already-recorded IDs)
        now = datetime.now().isoformat()
        new_count = 0
        for video_id in newly_unavailable:
            if video_id in existing:
                continue
            existing[video_id] = {
                "detected_at": now,
                "reason": "unavailable",
                "playlist_id": playlist.playlist_id,
            }
            new_count += 1
            logger.debug(f"Recorded unavailable video: {video_id}")

        if new_count == 0:
            return 0

        # Write updated file
        unavail_path.parent.mkdir(parents=True, exist_ok=True)
        with AtomicFileWriter(unavail_path) as f:
            json.dump(existing, f, indent=2)

        logger.info(f"Recorded {new_count} newly unavailable video(s) in {unavail_path.name}")
        return new_count

    def _process_video(self, video: Video, prefetched_stats: dict[str, dict[str, int]] | None = None) -> int:
        """Process a single video.

        Args:
            video: Video model instance
            prefetched_stats: Pre-fetched statistics dict (video_id -> stats) for batch efficiency.
                If provided, uses this instead of making per-video API calls.

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
                    # Check if video is within update window (default: 7 days)
                    # date_from/date_to filter on video publication date, not comment timestamps
                    if self.date_from and video.published_at < self.date_from:
                        logger.debug(f"Video outside update window: {video.published_at} < {self.date_from}")
                        return 0
                    if self.date_to and video.published_at > self.date_to:
                        logger.debug(f"Video outside update window: {video.published_at} > {self.date_to}")
                        return 0

                    # Load existing metadata to compare statistics
                    video_dir = self._rename_video_if_needed(video, expected_path)
                    metadata_path = video_dir / "metadata.json"

                    try:
                        with open(metadata_path, encoding='utf-8') as f:
                            old_metadata = json.load(f)
                        old_comment_count = old_metadata.get('comment_count', 0)
                        old_view_count = old_metadata.get('view_count', 0)
                        old_like_count = old_metadata.get('like_count', 0)
                    except Exception as e:
                        logger.warning(f"Failed to load existing metadata for {video.video_id}: {e}")
                        return 0

                    # Use pre-fetched statistics if available, otherwise fetch per-video (1 unit/request)
                    try:
                        if prefetched_stats is not None:
                            video_stats = prefetched_stats
                        else:
                            # Fallback: per-video fetch (inefficient, but works without batch)
                            from annextube.services.youtube_api import YouTubeAPIMetadataClient
                            api_client = YouTubeAPIMetadataClient()
                            video_stats = api_client.get_video_statistics(video.video_id)

                        if video.video_id in video_stats:
                            current_stats = video_stats[video.video_id]
                            new_comment_count = current_stats.get('commentCount', 0)
                            new_view_count = current_stats.get('viewCount', 0)
                            new_like_count = current_stats.get('likeCount', 0)

                            # Check if any statistics changed
                            stats_changed = (
                                new_comment_count != old_comment_count or
                                new_view_count != old_view_count or
                                new_like_count != old_like_count
                            )

                            if not stats_changed:
                                logger.debug(
                                    f"No social data changes for {video.video_id}: "
                                    f"comments={old_comment_count}, views={old_view_count}, likes={old_like_count}"
                                )
                                return 0

                            # Statistics changed - update video object with new values
                            logger.info(
                                f"Social data changed for {video.video_id}: "
                                f"comments {old_comment_count}->{new_comment_count}, "
                                f"views {old_view_count}->{new_view_count}, "
                                f"likes {old_like_count}->{new_like_count}"
                            )
                            video.comment_count = new_comment_count
                            video.view_count = new_view_count
                            video.like_count = new_like_count

                            # Update metadata.json with new statistics
                            with AtomicFileWriter(metadata_path) as f:
                                json.dump(video.to_dict(), f, indent=2)
                            logger.debug(f"Updated metadata with new statistics: {metadata_path}")

                            # If comment count increased, fetch new comments (with early stopping)
                            if new_comment_count > old_comment_count and self._get_component_value('comments_depth') != 0:
                                logger.info(
                                    f"Comment count increased ({old_comment_count} -> {new_comment_count}), "
                                    "fetching new comments with early stopping"
                                )
                                comments_path = video_dir / "comments.json"
                                self.youtube.download_comments(
                                    video.video_id,
                                    comments_path,
                                    max_depth=self._get_component_value('comments_depth')
                                )

                            # Return non-zero to indicate we updated something
                            return 1
                        else:
                            logger.warning(f"YouTube API did not return statistics for {video.video_id}")
                            return 0

                    except ValueError as e:
                        # API key not configured - can't check statistics
                        logger.debug(f"YouTube API not available for social updates: {e}")
                        return 0
                    except Exception as e:
                        logger.warning(f"Failed to fetch statistics for {video.video_id}: {e}")
                        return 0

                return 0

        # Continue with path calculation

        # Check if video needs renaming (path pattern changed)
        video_dir = self._rename_video_if_needed(video, expected_path)

        # Create directory if it doesn't exist (new videos)
        video_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Video directory: {video_dir}")

        # Set file_path to relative path (for consistency with TSV export)
        relative_path = video_dir.relative_to(self.repo_path / "videos")
        video.file_path = str(relative_path)

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

                # Update download_status to reflect action taken
                video.download_status = "tracked"

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
                if self._get_component_value('videos'):
                    logger.info(f"Downloading video content: {video_file}")
                    self.git_annex.get_file(video_file)

                    # Verify downloaded file is actually a video, not HTML/text error page
                    if not self._verify_video_file(video_file):
                        video.download_status = "failed"
                        error_msg = (
                            f"Downloaded file is not a valid video (likely HTML error page): {video_file}\n\n"
                            f"This usually means yt-dlp failed to download the video.\n"
                            f"To clean up and retry:\n"
                            f"  1. Drop the bad content: git annex drop '{video_file}'\n"
                            f"  2. Re-run backup to retry download\n\n"
                            f"Common causes:\n"
                            f"  - Video requires authentication (use cookies)\n"
                            f"  - Video is age-restricted or geo-blocked\n"
                            f"  - YouTube changed their API (update yt-dlp: uv pip install --upgrade yt-dlp)\n"
                            f"  - Video was deleted or made private\n"
                        )
                        logger.error(error_msg)
                        raise ValueError(f"Invalid video file: {video_file}")

                    # Successfully downloaded
                    video.download_status = "downloaded"

            except Exception as e:
                if video.download_status not in ("tracked", "downloaded"):
                    video.download_status = "failed"
                logger.warning(f"Failed to track video URL: {e}")

        # Save metadata (after tracking so download_status and file_path are set correctly)
        metadata_path = video_dir / "metadata.json"
        with AtomicFileWriter(metadata_path) as f:
            json.dump(video.to_dict(), f, indent=2)

        logger.debug(f"Saved metadata: {metadata_path}")

        # Download thumbnail (if enabled and mode allows)
        # For NEW videos: always fetch if configured, regardless of mode
        # For EXISTING videos: respect component-specific mode
        should_fetch_thumbnail = self._get_component_value('thumbnails') and video.thumbnail_url and \
                               (is_new_video or self._should_process_component("metadata"))
        if should_fetch_thumbnail:
            self._download_thumbnail(video, video_dir)

        # Download captions (if enabled and mode allows)
        # For NEW videos: always try to fetch if configured (we don't know what's available yet)
        # For EXISTING videos: try to fetch if captions enabled AND mode allows
        # (even if captions_available is empty - user may have enabled captions later)
        caption_count = 0
        captions_enabled = self._get_component_value('captions')
        if is_new_video:
            # New video: try to download if captions enabled, regardless of what metadata says
            should_fetch_captions = captions_enabled
            logger.info(f"Caption check for {video.video_id}: NEW video, captions_enabled={captions_enabled}, should_fetch={should_fetch_captions}")
        else:
            # Existing video: download if captions enabled AND mode allows
            # Don't check captions_available - it may be empty if captions were disabled previously
            mode_allows = self._should_process_component("captions")
            should_fetch_captions = bool(captions_enabled and mode_allows)
            logger.info(
                f"Caption check for {video.video_id}: EXISTING video, "
                f"captions_enabled={captions_enabled}, mode_allows={mode_allows}, "
                f"should_fetch={should_fetch_captions}"
            )
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
            else:
                logger.debug(f"No captions downloaded for {video.video_id} (none available)")

        # Download comments (if enabled and mode allows)
        # For NEW videos: always fetch if configured, regardless of mode
        # For EXISTING videos: respect component-specific mode
        # comments_depth: None = unlimited, 0 = disabled, N = limit to N
        comments_fetched = False
        should_fetch_comments = self._get_component_value('comments_depth') != 0 and \
                               (is_new_video or self._should_process_component("comments"))
        if should_fetch_comments:
            comments_path = video_dir / "comments.json"
            comments_fetched = self.youtube.download_comments(
                video.video_id,
                comments_path,
                max_depth=self._get_component_value('comments_depth')
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

    def _verify_video_file(self, video_file: Path) -> bool:
        """Verify downloaded file is actually a video, not HTML/text error page.

        Args:
            video_file: Path to downloaded video file

        Returns:
            True if file appears to be a valid video, False otherwise
        """
        if not video_file.exists():
            logger.warning(f"Video file does not exist: {video_file}")
            return False

        # Check file size - video files should be reasonably large
        file_size = video_file.stat().st_size
        if file_size < 1024:  # Less than 1 KB is suspiciously small
            logger.warning(f"Video file suspiciously small ({file_size} bytes): {video_file}")
            return False

        # Check file type using magic bytes (first few bytes of file)
        try:
            with open(video_file, 'rb') as f:
                header = f.read(512)

            # Check for HTML/text signatures (common error pages)
            html_signatures = [
                b'<!DOCTYPE',
                b'<html',
                b'<HTML',
                b'<?xml',
            ]

            for sig in html_signatures:
                if header.startswith(sig) or sig in header[:200]:
                    logger.error(f"File appears to be HTML/text, not video: {video_file}")
                    logger.debug(f"File header: {header[:100]!r}")
                    return False

            # Check for common video container signatures
            video_signatures = [
                (b'\x1a\x45\xdf\xa3', 'Matroska/WebM'),  # MKV/WebM
                (b'ftypmp4', 'MP4'),  # MP4 (starts with ftyp)
                (b'ftypisom', 'MP4'),  # MP4 ISO base media
                (b'ftypM4V', 'M4V'),  # M4V
                (b'\x00\x00\x00\x18ftypmp42', 'MP4'),  # MP4 variant
                (b'\x00\x00\x00\x1cftypisom', 'MP4'),  # MP4 variant
                (b'RIFF', 'AVI/WebM'),  # AVI or WebM
                (b'\x00\x00\x01\xba', 'MPEG'),  # MPEG PS
                (b'\x00\x00\x01\xb3', 'MPEG'),  # MPEG video
                (b'FLV', 'FLV'),  # Flash Video
            ]

            for sig, format_name in video_signatures:
                if sig in header[:50]:
                    logger.debug(f"Verified video file format: {format_name}")
                    return True

            # If we got here, we didn't find a known video signature
            # But it's not HTML either, so give benefit of doubt
            logger.warning(
                f"Could not identify video format (but not HTML): {video_file}\n"
                f"File may be valid but in unexpected format. Proceeding with caution."
            )
            return True  # Assume it's okay if not obviously HTML

        except Exception as e:
            logger.error(f"Failed to verify video file {video_file}: {e}")
            return False  # Fail safe - don't trust file we can't verify

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

    def _download_captions(self, video: Video, video_dir: Path) -> list[str]:
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
            logger.info(f"Attempting caption download for {video.video_id}: pattern={language_pattern}, auto_translated={auto_translated_langs}")

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
