"""YouTube service using yt-dlp for metadata and video operations."""

import json
import re
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yt_dlp

from annextube.lib.file_utils import AtomicFileWriter
from annextube.lib.logging_config import get_logger
from annextube.lib.process_semaphore import CookieFileSemaphore
from annextube.lib.ytdlp_ratelimit import (
    RateLimitDetector,
    YouTubeRateLimitError,
    retry_on_ytdlp_rate_limit,
)
from annextube.models.playlist import Playlist
from annextube.models.video import Video
from annextube.services.youtube_api import (
    YouTubeAPICommentsService,
    create_api_client,
)

logger = get_logger(__name__)


class YouTubeService:
    """Wrapper around yt-dlp for YouTube operations."""

    def __init__(
        self,
        archive_file: Path | None = None,
        cookies_file: str | None = None,
        cookies_from_browser: str | None = None,
        proxy: str | None = None,
        limit_rate: str | None = None,
        sleep_interval: int | None = None,
        max_sleep_interval: int | None = None,
        extractor_args: dict[str, Any] | None = None,
        remote_components: str | None = None,
        youtube_api_key: str | None = None,
        rate_limit_max_wait_seconds: int = 7200,
        yt_dlp_max_parallel: int = 1,
    ):
        """Initialize YouTubeService.

        Args:
            archive_file: Optional path to yt-dlp archive file for tracking
            cookies_file: Path to Netscape cookies file
            cookies_from_browser: Browser to extract cookies from (e.g., "firefox")
            proxy: Proxy URL (e.g., "socks5://127.0.0.1:9050")
            limit_rate: Bandwidth limit (e.g., "500K")
            sleep_interval: Minimum seconds between downloads
            max_sleep_interval: Maximum seconds between downloads
            extractor_args: Extractor-specific arguments (e.g., {"youtube": {"player_client": ["android"]}})
            remote_components: Remote components to enable (e.g., "ejs:github" for JS challenge solver)
            youtube_api_key: YouTube Data API v3 key for enhanced metadata (optional)
            rate_limit_max_wait_seconds: Max seconds to wait on rate-limit retry (default 7200)
            yt_dlp_max_parallel: Max concurrent yt-dlp calls per cookie file (default 1)
        """
        # Ensure deno is in PATH for EJS solver (if installed)
        import os
        import pwd
        try:
            actual_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        except Exception:
            actual_home = Path.home()

        deno_bin = actual_home / ".deno" / "bin"
        if deno_bin.exists() and str(deno_bin) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{deno_bin}:{os.environ.get('PATH', '')}"
            logger.debug(f"Added deno to PATH: {deno_bin}")

        self.archive_file = archive_file
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        self.proxy = proxy
        self.limit_rate = limit_rate
        self.sleep_interval = sleep_interval
        self.max_sleep_interval = max_sleep_interval
        self.extractor_args = extractor_args or {}
        self.remote_components = remote_components

        # Track unavailable video IDs discovered during playlist extraction
        self._last_unavailable_ids: set[str] = set()

        # Create YouTube API client for enhanced metadata if key provided
        self.api_client = create_api_client(youtube_api_key)

        # Rate-limit / concurrency settings
        self._rate_limit_max_wait_seconds = rate_limit_max_wait_seconds
        self._semaphore: CookieFileSemaphore | None = None
        if yt_dlp_max_parallel > 0:
            self._semaphore = CookieFileSemaphore(
                cookies_file=cookies_file,
                max_parallel=yt_dlp_max_parallel,
            )

        # Debug: Show what config was passed to YouTubeService
        logger.debug(f"YouTubeService initialized with: cookies_file={cookies_file}, cookies_from_browser={cookies_from_browser}, proxy={proxy}, api_key={'***' if youtube_api_key else None}")

    @contextmanager
    def _semaphore_guard(self) -> Generator[None, None, None]:
        """Acquire/release the cross-process semaphore if configured."""
        if self._semaphore:
            self._semaphore.acquire()
        try:
            yield
        finally:
            if self._semaphore:
                self._semaphore.release()

    def _make_rate_limit_detector(self, base_logger: Any) -> RateLimitDetector:
        """Create a RateLimitDetector wrapping *base_logger*."""
        return RateLimitDetector(base_logger)

    def _with_rate_limit_retry(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Call *func* with automatic rate-limit detection and retry.

        Wraps ``retry_on_ytdlp_rate_limit`` with instance-level settings.
        """
        return retry_on_ytdlp_rate_limit(
            func,
            *args,
            max_retries=3,
            max_wait_seconds=self._rate_limit_max_wait_seconds,
            cookies_file=self.cookies_file,
            **kwargs,
        )

    def _check_detector(self, detector: RateLimitDetector) -> None:
        """Raise YouTubeRateLimitError if *detector* flagged a rate limit."""
        if detector.rate_limited:
            raise YouTubeRateLimitError(
                detector.rate_limit_message,
                detector.wait_seconds,
            )

    def _extract_info_checked(
        self,
        url: str,
        extra_opts: dict[str, Any] | None = None,
        download: bool = False,
    ) -> dict[str, Any] | None:
        """Run ``extract_info`` with rate-limit detection.

        Creates a fresh ``RateLimitDetector``, injects it into yt-dlp opts,
        and raises ``YouTubeRateLimitError`` if a ban pattern is logged.
        """
        import logging as stdlib_logging
        base_logger = stdlib_logging.getLogger("yt_dlp")
        detector = self._make_rate_limit_detector(base_logger)
        opts = self._get_ydl_opts(download=download, rate_limit_detector=detector)
        if extra_opts:
            opts.update(extra_opts)
        with self._semaphore_guard():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=download)
        self._check_detector(detector)
        result: dict[str, Any] | None = info
        return result

    def _fetch_single_video_info(self, video_id: str) -> dict[str, Any] | None:
        """Fetch full metadata for one video with rate-limit retry.

        Used by per-video loops.  Each call creates its own yt-dlp instance
        so a fresh ``RateLimitDetector`` is wired in.
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        result: dict[str, Any] | None = self._with_rate_limit_retry(
            self._extract_info_checked,
            video_url,
            extra_opts={"ignoreerrors": True},
        )
        return result

    def _get_ydl_opts(
        self, download: bool = False, rate_limit_detector: RateLimitDetector | None = None
    ) -> dict[str, Any]:
        """Get yt-dlp options including user config settings.

        Args:
            download: Whether to download video content
            rate_limit_detector: Optional detector to inject as the yt-dlp logger.
                When provided, it wraps the normal yt-dlp logger and watches
                for rate-limit messages.

        Returns:
            yt-dlp options dictionary
        """
        logger.debug(f"Building yt-dlp options (download={download})")

        # Enable yt-dlp's own verbose logging only at HEAVY_DEBUG level (5)
        # Regular DEBUG level (10) shows only annextube debug logs
        import logging as stdlib_logging

        from annextube.lib.logging_config import HEAVY_DEBUG

        # Check effective level (handles inheritance from parent loggers)
        effective_level = logger.getEffectiveLevel()
        enable_ytdlp_verbose = effective_level <= HEAVY_DEBUG
        logger.debug(f"yt-dlp verbose mode: {enable_ytdlp_verbose} (effective_level={effective_level}, HEAVY_DEBUG={HEAVY_DEBUG})")

        # Configure yt-dlp to use Python logging (so it goes through our formatter with datetime + logger name)
        # Use standard "yt_dlp" logger name (not annextube.yt_dlp) for interoperability
        ytdlp_logger = stdlib_logging.getLogger("yt_dlp")
        ytdlp_logger.setLevel(HEAVY_DEBUG if enable_ytdlp_verbose else stdlib_logging.INFO)

        # Configure yt_dlp logger to use same handlers as annextube logger (if not already configured)
        annextube_logger = stdlib_logging.getLogger("annextube")
        if annextube_logger.handlers and not ytdlp_logger.handlers:
            for handler in annextube_logger.handlers:
                ytdlp_logger.addHandler(handler)
            ytdlp_logger.propagate = False

        # Use rate-limit detector as the yt-dlp logger when provided
        effective_logger: Any = rate_limit_detector if rate_limit_detector else ytdlp_logger

        opts: dict[str, Any] = {
            "quiet": not enable_ytdlp_verbose,  # Disable quiet in debug mode
            "no_warnings": not enable_ytdlp_verbose,  # Show warnings in debug mode
            "verbose": enable_ytdlp_verbose,  # Enable yt-dlp's verbose output
            "logger": effective_logger,  # Use Python logger (or detector wrapper)
            "extract_flat": False,  # Get full metadata
            "skip_download": not download,
        }

        if self.archive_file:
            opts["download_archive"] = str(self.archive_file)

        # Add cookie configuration (from user config)
        if self.cookies_file:
            cookie_path = Path(self.cookies_file).expanduser().resolve()
            opts["cookiefile"] = str(cookie_path)
            logger.debug(f"yt-dlp: Using cookie file: {cookie_path} (exists={cookie_path.exists()})")
        elif self.cookies_from_browser:
            # Parse browser:profile format
            parts = self.cookies_from_browser.split(":", 1)
            browser = parts[0]
            profile = parts[1] if len(parts) > 1 else None
            opts["cookiesfrombrowser"] = (browser, profile, None, None)
            logger.debug(f"yt-dlp: Using cookies from browser: {browser}" + (f" (profile: {profile})" if profile else ""))

        # Add network settings (from user config)
        if self.proxy:
            opts["proxy"] = self.proxy

        if self.limit_rate:
            opts["ratelimit"] = self.limit_rate

        if self.sleep_interval is not None:
            opts["sleep_interval"] = self.sleep_interval

        if self.max_sleep_interval is not None:
            opts["max_sleep_interval"] = self.max_sleep_interval

        # Add extractor arguments (e.g., Android client workaround)
        if self.extractor_args:
            opts["extractor_args"] = self.extractor_args
            logger.debug(f"yt-dlp: Using extractor args: {self.extractor_args}")

        # Enable remote components for JS challenge solver.
        # Default to ejs:github since deno is a core dependency.
        remote = self.remote_components or "ejs:github"
        opts["remote_components"] = [remote]
        logger.debug(f"yt-dlp: Using remote components: {remote}")

        # Log full options for debugging
        logger.debug(f"yt-dlp options: {opts}")
        return opts

    def get_channel_videos(
        self, channel_url: str, limit: int | None = None,
        existing_video_ids: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """Get videos from a channel.

        Args:
            channel_url: YouTube channel URL
            limit: Optional limit for number of videos (most recent)
            existing_video_ids: Optional set of video IDs already in archive (for incremental updates)

        Returns:
            List of video metadata dictionaries
        """
        logger.info(f"Fetching videos from channel: {channel_url}")

        if existing_video_ids:
            logger.info(f"Will filter out {len(existing_video_ids)} existing videos by ID")

        # Ensure we're getting the videos tab, not channel tabs
        if not channel_url.endswith("/videos"):
            channel_url = channel_url.rstrip("/") + "/videos"
            logger.debug(f"Adjusted URL to videos tab: {channel_url}")

        ydl_opts = self._get_ydl_opts(download=False)

        # In incremental mode, use two-pass approach:
        # 1. First pass with extract_flat to get just video IDs (fast)
        # 2. Second pass to fetch full metadata only for new videos
        use_two_pass = existing_video_ids is not None and len(existing_video_ids) > 0

        if use_two_pass:
            assert existing_video_ids is not None  # Type narrowing for mypy
            # First pass: Get just IDs with extract_flat
            import logging as stdlib_logging
            _base_logger = stdlib_logging.getLogger("yt_dlp")
            _detector = self._make_rate_limit_detector(_base_logger)
            flat_opts = self._get_ydl_opts(download=False, rate_limit_detector=_detector)
            flat_opts.update({
                "extract_flat": "in_playlist",  # Just get video IDs, no metadata
                "playlistend": limit if limit else None,
                "ignoreerrors": True,
            })

            logger.info("First pass: fetching video list (this may take a minute for large playlists)...")
            with yt_dlp.YoutubeDL(flat_opts) as ydl_flat:
                try:
                    with self._semaphore_guard():
                        info = ydl_flat.extract_info(channel_url, download=False)
                    self._check_detector(_detector)
                    if not info or not info.get("entries"):
                        logger.warning("No videos found in channel")
                        return []

                    # Filter to find new video IDs
                    all_entries = list(info.get("entries", []))
                    logger.info(f"Scanning {len(all_entries)} videos for new content...")
                    new_video_ids: list[str] = []
                    consecutive_existing = 0

                    for i, entry in enumerate(all_entries, 1):
                        # Progress indicator every 100 videos
                        if i % 100 == 0:
                            logger.info(f"Scanned {i}/{len(all_entries)} videos, found {len(new_video_ids)} new so far")
                        if not entry or not entry.get("id"):
                            continue

                        video_id = entry["id"]
                        if video_id in existing_video_ids:
                            logger.debug(f"Skipping existing video: {video_id}")
                            consecutive_existing += 1
                            if consecutive_existing >= 10:
                                logger.info("Stopping: found 10 consecutive existing videos")
                                break
                            continue

                        consecutive_existing = 0
                        new_video_ids.append(video_id)

                    if not new_video_ids:
                        logger.info("No new videos found")
                        return []

                    logger.info(f"Found {len(new_video_ids)} new video(s), fetching full metadata")

                except Exception as e:
                    logger.error(f"Failed flat extraction: {e}", exc_info=True)
                    # Fall back to regular extraction
                    use_two_pass = False

            # Second pass: Fetch full metadata only for new videos (outside the flat extraction context)
            if use_two_pass:
                videos = []
                total_new = len(new_video_ids)
                for idx, video_id in enumerate(new_video_ids, 1):
                    try:
                        logger.info(f"Fetching metadata [{idx}/{total_new}]: {video_id}")
                        video_info = self._fetch_single_video_info(video_id)
                        if video_info:
                            videos.append(video_info)
                    except YouTubeRateLimitError:
                        logger.error("Rate limit persisted after retries, stopping video fetch")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for {video_id}: {e}")

                logger.info(f"Successfully fetched metadata for {len(videos)}/{total_new} new video(s)")
                return videos

        # Regular extraction (initial backup or fallback)
        logger.info("Fetching videos (this may take several minutes for large channels)...")
        import logging as stdlib_logging
        _base_logger2 = stdlib_logging.getLogger("yt_dlp")
        _detector2 = self._make_rate_limit_detector(_base_logger2)
        ydl_opts = self._get_ydl_opts(download=False, rate_limit_detector=_detector2)
        ydl_opts.update(
            {
                "playlistend": limit if limit else None,
                "ignoreerrors": True,  # Continue on errors
                "no_warnings": False,  # Show warnings for debugging
            }
        )

        logger.debug(f"Calling yt-dlp: extract_info('{channel_url}', download=False) with opts={ydl_opts}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract channel info (this gets the uploads playlist with full metadata)
                with self._semaphore_guard():
                    info = ydl.extract_info(channel_url, download=False)
                self._check_detector(_detector2)

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
                # In incremental mode, stop when we hit consecutive existing videos
                videos = []
                consecutive_existing = 0
                max_consecutive_existing = 10  # Stop after 10 consecutive existing videos
                total_entries = len(entries)

                for idx, entry in enumerate(entries, 1):
                    # Progress indicator every 100 videos
                    if idx % 100 == 0:
                        logger.info(f"Processing {idx}/{total_entries} videos, found {len(videos)} new so far...")
                    if entry is None:
                        continue

                    # Some entries might be incomplete, skip them
                    if not entry.get("id"):
                        logger.warning(f"Skipping entry without ID: {entry.get('title', 'Unknown')}")
                        continue

                    # Filter by existing video IDs (for incremental updates)
                    if existing_video_ids and entry.get("id") in existing_video_ids:
                        logger.debug(f"Skipping existing video: {entry.get('id')}")
                        consecutive_existing += 1

                        # Stop early if we've hit many consecutive existing videos
                        # This is the mykrok pattern: assume no new videos after this point
                        if consecutive_existing >= max_consecutive_existing:
                            logger.info(f"Stopping: found {consecutive_existing} consecutive existing videos")
                            break
                        continue

                    # Found a new video - reset consecutive counter
                    consecutive_existing = 0
                    videos.append(entry)

                logger.info(f"Successfully fetched metadata for {len(videos)} video(s)")
                if existing_video_ids and consecutive_existing > 0:
                    logger.info(f"Stopped after encountering {consecutive_existing} existing video(s)")
                return videos

            except Exception as e:
                logger.error(f"Failed to fetch channel videos: {e}", exc_info=True)
                return []

    def get_playlist_videos(
        self, playlist_url: str, limit: int | None = None,
        repo_path: Path | None = None, incremental: bool = False
    ) -> list[dict[str, Any]]:
        """Get videos from a playlist.

        In incremental mode with known unavailable videos, uses two-pass approach:
        1. First pass: extract_flat to get just video IDs (fast)
        2. Filter out known unavailable videos
        3. Second pass: fetch full metadata only for available videos

        Args:
            playlist_url: YouTube playlist URL
            limit: Optional limit for number of videos (most recent)
            repo_path: Optional path to archive repository (for incremental mode)
            incremental: If True, skip videos known to be unavailable

        Returns:
            List of video metadata dictionaries
        """
        logger.info(f"Fetching videos from playlist: {playlist_url}")

        # Reset per-call tracking of unavailable IDs
        self._last_unavailable_ids = set()

        # In incremental mode, load known unavailable videos first
        unavailable_videos: set[str] = set()
        if incremental and repo_path:
            unavailable_videos = self._load_unavailable_videos(repo_path)
            if unavailable_videos:
                logger.info(f"Loaded {len(unavailable_videos)} known unavailable video(s) from archive")

        # Use two-pass approach if we have unavailable videos to filter
        use_two_pass = incremental and len(unavailable_videos) > 0

        if use_two_pass:
            # First pass: Get just video IDs with extract_flat (fast, no metadata fetching)
            import logging as stdlib_logging
            _base_logger_pl = stdlib_logging.getLogger("yt_dlp")
            _detector_pl = self._make_rate_limit_detector(_base_logger_pl)
            flat_opts = self._get_ydl_opts(download=False, rate_limit_detector=_detector_pl)
            flat_opts.update({
                "extract_flat": "in_playlist",  # Just get video IDs, no metadata
                "playlistend": limit if limit else None,
                "ignoreerrors": True,
            })

            logger.info("First pass: fetching video ID list (fast)...")
            with yt_dlp.YoutubeDL(flat_opts) as ydl_flat:
                try:
                    with self._semaphore_guard():
                        info = ydl_flat.extract_info(playlist_url, download=False)
                    self._check_detector(_detector_pl)
                    if not info or not info.get("entries"):
                        logger.warning("No videos found in playlist")
                        return []

                    # Get all video IDs
                    all_entries = list(info.get("entries", []))
                    logger.info(f"Found {len(all_entries)} video(s) in playlist")

                    # Filter to find videos to fetch (exclude known unavailable)
                    video_ids_to_fetch: list[str] = []
                    skipped_unavailable = 0

                    for entry in all_entries:
                        if not entry or not entry.get("id"):
                            continue

                        video_id = entry["id"]
                        if video_id in unavailable_videos:
                            logger.debug(f"Skipping known unavailable video: {video_id}")
                            skipped_unavailable += 1
                            continue

                        video_ids_to_fetch.append(video_id)

                    if skipped_unavailable > 0:
                        logger.info(f"Skipped {skipped_unavailable} video(s) known to be unavailable")

                    if not video_ids_to_fetch:
                        logger.info("No new videos to fetch (all known unavailable)")
                        return []

                    logger.info(f"Will fetch full metadata for {len(video_ids_to_fetch)} video(s)")

                except Exception as e:
                    logger.error(f"Failed flat extraction: {e}", exc_info=True)
                    # Fall back to regular extraction
                    use_two_pass = False

            # Second pass: Fetch full metadata only for available videos
            if use_two_pass:
                videos = []
                total_to_fetch = len(video_ids_to_fetch)
                for idx, video_id in enumerate(video_ids_to_fetch, 1):
                    try:
                        if idx % 100 == 0 or idx == 1 or idx == total_to_fetch:
                            logger.info(f"Fetching metadata [{idx}/{total_to_fetch}]: {video_id}")
                        video_info = self._fetch_single_video_info(video_id)
                        if video_info:
                            videos.append(video_info)
                        else:
                            logger.warning(f"No metadata returned for {video_id}")
                    except YouTubeRateLimitError:
                        logger.error("Rate limit persisted after retries, stopping video fetch")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for {video_id}: {e}")
                        self._last_unavailable_ids.add(video_id)

                logger.info(f"Successfully fetched metadata for {len(videos)}/{total_to_fetch} video(s)")
                if self._last_unavailable_ids:
                    logger.info(f"Detected {len(self._last_unavailable_ids)} newly unavailable video(s)")
                return videos

        # Regular extraction (non-incremental or no unavailable videos)
        import logging as stdlib_logging
        _base_logger_plr = stdlib_logging.getLogger("yt_dlp")
        _detector_plr = self._make_rate_limit_detector(_base_logger_plr)
        ydl_opts = self._get_ydl_opts(download=False, rate_limit_detector=_detector_plr)
        ydl_opts.update(
            {
                "playlistend": limit if limit else None,
                "ignoreerrors": True,  # Continue on errors
                "no_warnings": False,  # Show warnings for debugging
            }
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract playlist info (gets full metadata for all videos)
                logger.info("Fetching playlist metadata (this may take several minutes for large playlists)...")
                logger.debug(f"Calling yt-dlp: extract_info('{playlist_url}', download=False)")
                with self._semaphore_guard():
                    info = ydl.extract_info(playlist_url, download=False)
                self._check_detector(_detector_plr)

                if not info:
                    logger.warning(f"No information found for playlist: {playlist_url}")
                    return []

                # Get entries (videos) - full metadata included
                entries = info.get("entries", [])

                if not entries:
                    logger.warning("Playlist has no videos or videos are not accessible")
                    return []

                logger.info(f"Found {len(entries)} video(s) in playlist")

                if limit:
                    entries = entries[:limit]
                    logger.info(f"Limited to {len(entries)} video(s)")

                # Filter out None entries and extract metadata
                videos = []
                total_entries = len(entries)
                for idx, entry in enumerate(entries, 1):
                    # Progress indicator every 100 videos
                    if idx % 100 == 0:
                        logger.info(f"Processing {idx}/{total_entries} videos...")

                    if entry is None:
                        continue

                    # Some entries might be incomplete, skip them
                    video_id = entry.get("id")
                    if not video_id:
                        logger.warning(f"Skipping entry without ID: {entry.get('title', 'Unknown')}")
                        continue

                    videos.append(entry)

                logger.info(f"Successfully processed {len(videos)}/{total_entries} video(s)")
                return videos

            except Exception as e:
                logger.error(f"Failed to fetch playlist videos: {e}", exc_info=True)
                return []

    def _load_unavailable_videos(self, repo_path: Path) -> set[str]:
        """Load video IDs of known unavailable videos from archive.

        Reads from two sources:
        1. .annextube/unavailable_videos.json (centralized registry)
        2. videos/**/metadata.json with non-public availability (legacy/explicit)

        Args:
            repo_path: Path to archive repository

        Returns:
            Set of video IDs known to be unavailable
        """
        unavailable: set[str] = set()

        # Source 1: centralized unavailable_videos.json (fast)
        unavail_path = repo_path / ".annextube" / "unavailable_videos.json"
        if unavail_path.exists():
            try:
                with open(unavail_path, encoding="utf-8") as f:
                    data = json.load(f)
                unavailable.update(data.keys())
                logger.debug(f"Loaded {len(data)} unavailable IDs from {unavail_path.name}")
            except Exception as e:
                logger.warning(f"Failed to load {unavail_path}: {e}")

        # Source 2: scan metadata.json files for explicit unavailability
        videos_dir = repo_path / "videos"
        if videos_dir.exists():
            metadata_files = list(videos_dir.glob("**/metadata.json"))

            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, encoding='utf-8') as f:
                        metadata = json.load(f)

                    video_id = metadata.get("video_id")
                    availability = metadata.get("availability", "public")

                    # Consider video unavailable if not public
                    # Possible values: 'public', 'private', 'removed', 'unavailable', 'unlisted'
                    if video_id and availability in ['private', 'removed', 'unavailable']:
                        unavailable.add(video_id)
                        logger.debug(f"Found unavailable video: {video_id} (status: {availability})")
                except Exception as e:
                    logger.debug(f"Failed to parse metadata file {metadata_file}: {e}")
                    continue

        return unavailable

    def get_playlist_metadata(self, playlist_url: str) -> Playlist | None:
        """Get metadata for a playlist.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            Playlist model instance or None if failed
        """
        logger.debug(f"Fetching playlist metadata: {playlist_url}")

        try:
            info = self._with_rate_limit_retry(
                self._extract_info_checked,
                playlist_url,
                extra_opts={"extract_flat": True},
            )
        except YouTubeRateLimitError:
            logger.error(f"Rate limit fetching playlist metadata: {playlist_url}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch playlist metadata: {e}")
            return None

        if not info:
            return None

        try:
            # Parse last modified date if available
            last_modified = None
            if info.get("modified_date"):
                try:
                    last_modified = datetime.strptime(info["modified_date"], "%Y%m%d")
                except ValueError:
                    pass

            # Get video IDs from entries
            video_ids = []
            for entry in info.get("entries", []):
                if entry and entry.get("id"):
                    video_ids.append(entry["id"])

            return Playlist(
                playlist_id=info["id"],
                title=info.get("title", "Unknown"),
                description=info.get("description", ""),
                channel_id=info.get("channel_id", info.get("uploader_id", "")),
                channel_name=info.get("channel", info.get("uploader", "")),
                video_count=info.get("playlist_count", len(video_ids)),
                privacy_status=info.get("availability", "public"),
                last_modified=last_modified,
                video_ids=video_ids,
                thumbnail_url=info.get("thumbnail"),
                fetched_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Failed to fetch playlist metadata: {e}")
            return None

    def get_videos_metadata(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch full metadata for specific video IDs.

        Used to get metadata for playlist-exclusive videos that weren't
        discovered via channel video listing.

        Args:
            video_ids: List of YouTube video IDs to fetch metadata for

        Returns:
            List of video metadata dictionaries (skips failed fetches)
        """
        if not video_ids:
            return []

        logger.info(f"Fetching metadata for {len(video_ids)} individual video(s)")

        videos = []
        for idx, video_id in enumerate(video_ids, 1):
            try:
                if idx % 10 == 0 or idx == 1 or idx == len(video_ids):
                    logger.info(f"Fetching metadata [{idx}/{len(video_ids)}]: {video_id}")
                info = self._fetch_single_video_info(video_id)
                if info:
                    videos.append(info)
            except YouTubeRateLimitError:
                logger.error("Rate limit persisted after retries, stopping metadata fetch")
                break
            except Exception as e:
                logger.warning(f"Failed to fetch metadata for {video_id}: {e}")

        logger.info(f"Successfully fetched metadata for {len(videos)}/{len(video_ids)} video(s)")
        return videos

    def get_channel_playlists(self, channel_url: str) -> list[dict[str, Any]]:
        """Get all playlists from a channel.

        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channel)

        Returns:
            List of playlist dicts with: id, title, url, video_count
        """
        logger.debug(f"Discovering playlists from channel: {channel_url}")

        # Construct playlists tab URL
        playlists_url = channel_url.rstrip("/") + "/playlists"

        try:
            info = self._with_rate_limit_retry(
                self._extract_info_checked,
                playlists_url,
                extra_opts={"extract_flat": True},
            )
        except YouTubeRateLimitError:
            logger.error(f"Rate limit fetching playlists for: {channel_url}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch channel playlists: {e}")
            return []

        if not info or "entries" not in info:
            logger.warning(f"No playlists found for channel: {channel_url}")
            return []

        playlists = []
        for entry in info["entries"]:
            if entry and entry.get("_type") == "url" and entry.get("ie_key") == "YoutubeTab":
                playlist_id = None
                url = entry.get("url", "")
                if "list=" in url:
                    playlist_id = url.split("list=")[1].split("&")[0]

                playlists.append({
                    "id": playlist_id or entry.get("id"),
                    "title": entry.get("title") or "Unknown",
                    "url": url,
                    "video_count": entry.get("playlist_count", 0),
                })

        logger.info(f"Discovered {len(playlists)} playlists from {channel_url}")
        return playlists

    def get_channel_podcasts(self, channel_url: str) -> list[dict[str, Any]]:
        """Get all podcasts from a channel's Podcasts tab.

        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channel)

        Returns:
            List of podcast dicts with: id, title, url, video_count
        """
        logger.debug(f"Discovering podcasts from channel: {channel_url}")

        # Construct podcasts tab URL
        podcasts_url = channel_url.rstrip("/") + "/podcasts"

        try:
            info = self._with_rate_limit_retry(
                self._extract_info_checked,
                podcasts_url,
                extra_opts={"extract_flat": True},
            )
        except YouTubeRateLimitError:
            logger.error(f"Rate limit fetching podcasts for: {channel_url}")
            return []
        except Exception as e:
            logger.debug(f"Failed to fetch channel podcasts (may not have podcasts): {e}")
            return []

        if not info or "entries" not in info:
            logger.debug(f"No podcasts found for channel: {channel_url}")
            return []

        podcasts = []
        for entry in info["entries"]:
            if entry and entry.get("_type") == "url" and entry.get("ie_key") == "YoutubeTab":
                playlist_id = None
                url = entry.get("url", "")
                if "list=" in url:
                    playlist_id = url.split("list=")[1].split("&")[0]

                podcasts.append({
                    "id": playlist_id or entry.get("id"),
                    "title": entry.get("title") or "Unknown",
                    "url": url,
                    "video_count": entry.get("playlist_count", 0),
                })

        logger.info(f"Discovered {len(podcasts)} podcasts from {channel_url}")
        return podcasts

    def get_channel_metadata(self, channel_url: str) -> dict[str, Any]:
        """Extract channel-level metadata (description, avatar, subscribers).

        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channel)

        Returns:
            Dictionary with channel metadata: {
                channel_id, channel_name, description, custom_url,
                avatar_url, subscriber_count, video_count
            }
        """
        logger.debug(f"Extracting channel metadata from: {channel_url}")

        try:
            info = self._with_rate_limit_retry(
                self._extract_info_checked,
                channel_url,
                extra_opts={"extract_flat": True},
            )
        except YouTubeRateLimitError:
            logger.error(f"Rate limit extracting channel metadata: {channel_url}")
            return {}
        except Exception as e:
            logger.error(f"Failed to extract channel metadata: {e}")
            return {}

        if not info:
            logger.warning(f"No information found for channel: {channel_url}")
            return {}

        # Extract avatar URL (use highest resolution available)
        avatar_url = ""
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda t: t.get("width", 0) * t.get("height", 0),
                reverse=True
            )
            avatar_url = sorted_thumbs[0].get("url", "")

        # Parse custom URL from original_url or channel_url
        custom_url = ""
        original_url = info.get("original_url", channel_url)
        if "@" in original_url:
            custom_url = original_url.split("@")[-1].split("/")[0].split("?")[0]

        metadata = {
            "channel_id": info.get("channel_id") or info.get("uploader_id", ""),
            "channel_name": info.get("channel") or info.get("uploader", ""),
            "description": info.get("description", ""),
            "custom_url": custom_url,
            "avatar_url": avatar_url,
            "subscriber_count": info.get("channel_follower_count") or 0,
            "video_count": info.get("playlist_count", 0),
        }

        logger.info(
            f"Extracted channel metadata: {metadata['channel_name']} "
            f"({metadata['subscriber_count']} subscribers, "
            f"{metadata['video_count']} videos)"
        )
        return metadata

    def get_video_metadata(self, video_url: str) -> dict[str, Any] | None:
        """Get metadata for a single video.

        Args:
            video_url: YouTube video URL

        Returns:
            Video metadata dictionary or None if failed.
            If video is unavailable, returns dict with:
            - 'id': video_id
            - 'availability': 'unavailable' or 'private' or 'removed'
            - 'privacy_status': 'non-public' or 'removed'
        """
        logger.debug(f"Fetching metadata for: {video_url}")

        try:
            info = self._with_rate_limit_retry(
                self._extract_info_checked, video_url,
            )
            return cast(dict[str, Any] | None, info)
        except YouTubeRateLimitError:
            logger.error(f"Rate limit fetching video metadata: {video_url}")
            return None
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            # Extract video ID from URL
            video_id = None
            if 'v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
            elif '/' in video_url:
                video_id = video_url.split('/')[-1]

            # Detect specific error types
            if 'private video' in error_msg or 'this video is private' in error_msg:
                logger.warning(f"Video is private: {video_url}")
                return {
                    'id': video_id,
                    'availability': 'private',
                    'privacy_status': 'non-public',
                    'title': f'Private Video ({video_id})',
                    'was_available': True,
                }
            elif 'video has been removed' in error_msg or 'unavailable' in error_msg or 'deleted' in error_msg:
                logger.warning(f"Video has been removed: {video_url}")
                return {
                    'id': video_id,
                    'availability': 'removed',
                    'privacy_status': 'removed',
                    'title': f'Removed Video ({video_id})',
                    'was_available': True,
                }
            else:
                logger.error(f"Failed to fetch video metadata: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to fetch video metadata: {e}")
            return None

    def extract_video_url(self, video_id: str) -> str | None:
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
            return cast(str, best_format["url"])

        return video_url  # Fallback

    def download_captions(
        self, video_id: str, output_dir: Path, language_pattern: str = ".*",
        auto_translated_langs: list[str] | None = None, base_filename: str | None = None
    ) -> list[dict[str, Any]]:
        """Download captions for a video, excluding auto-translated by default.

        By default, downloads only:
        - Manual subtitles (uploaded by creator)
        - Auto-generated captions (speech-to-text in original language)

        Auto-translated captions (machine translation to other languages) are excluded
        unless explicitly specified in auto_translated_langs.

        Args:
            video_id: YouTube video ID
            output_dir: Directory to save captions
            language_pattern: Regex pattern for filtering caption languages
                             (default: ".*" for all languages)
            auto_translated_langs: List of language codes for auto-translated captions to download
                                  (e.g., ["en", "es"]). Default: [] (no auto-translated)
            base_filename: Base filename for caption files (without extension)
                          (e.g., "video" produces "video.ru.vtt")
                          If None, uses video_id as base filename

        Returns:
            List of caption metadata dictionaries with keys:
            - language_code: Language code (e.g., 'en', 'ru')
            - auto_generated: Whether caption is auto-generated (vs manual)
            - auto_translated: Whether caption is auto-translated
            - file_path: Path to caption file
            - fetched_at: ISO 8601 timestamp when fetched
        """
        if auto_translated_langs is None:
            auto_translated_langs = []

        # Use base_filename for caption files (defaults to video_id for backward compatibility)
        if base_filename is None:
            base_filename = video_id

        logger.info(f"Downloading captions for: {video_id} (pattern: {language_pattern}, auto-translated: {auto_translated_langs or 'none'})")

        output_dir.mkdir(parents=True, exist_ok=True)
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            # Get available captions without downloading (with rate-limit detection)
            info = self._with_rate_limit_retry(
                self._extract_info_checked, video_url,
            )

            if not info:
                logger.warning(f"No info available for video: {video_id}")
                return []

            # Get available subtitles and auto captions
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})

            if not subtitles and not automatic_captions:
                logger.info(f"No captions available for video: {video_id}")
                return []

            # Determine which captions to download
            langs_to_download = []

            # Always include manual subtitles (if they match pattern)
            pattern = re.compile(language_pattern)
            for lang in subtitles.keys():
                if pattern.match(lang):
                    langs_to_download.append(lang)

            # For automatic captions, check if auto-translated
            for lang, variants in automatic_captions.items():
                if not pattern.match(lang):
                    continue

                # Check first variant's URL to determine if auto-translated
                if variants and len(variants) > 0:
                    url = variants[0].get('url', '')
                    # Auto-translated captions have tlang parameter in URL
                    is_auto_translated = 'tlang=' in url

                    if is_auto_translated:
                        # Only download if explicitly requested
                        if lang in auto_translated_langs:
                            langs_to_download.append(lang)
                    else:
                        # Auto-generated (not translated) - always download
                        langs_to_download.append(lang)

            if not langs_to_download:
                logger.info(
                    f"No captions to download after filtering "
                    f"(manual: {len(subtitles)}, auto: {len(automatic_captions)})"
                )
                return []

            logger.info(
                f"Downloading {len(langs_to_download)} caption(s): {sorted(langs_to_download)}"
            )

            # Download selected captions
            ydl_opts = self._get_ydl_opts(download=False)
            ydl_opts.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": langs_to_download,
                "subtitlesformat": "vtt",
                "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            })

            def _download():
                with self._semaphore_guard():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])

            # Retry on rate limits
            self._with_rate_limit_retry(_download)

            # Find downloaded caption files (yt-dlp uses video_id in filename)
            caption_files = list(output_dir.glob(f"{video_id}.*.vtt"))

            # Rename files if base_filename differs from video_id
            # This allows video.ru.vtt instead of VIDEO_ID.ru.vtt for player auto-discovery
            if base_filename != video_id:
                renamed_files = []
                for caption_file in caption_files:
                    # Extract language code from filename (video_id.lang.vtt)
                    lang_code = caption_file.stem.split(".")[-1]
                    new_name = output_dir / f"{base_filename}.{lang_code}.vtt"
                    caption_file.rename(new_name)
                    renamed_files.append(new_name)
                    logger.debug(f"Renamed {caption_file.name} -> {new_name.name}")
                caption_files = renamed_files

            # Deduplicate: remove LANG-orig if identical to LANG
            # This avoids storing duplicate files for curated vs original captions
            files_to_remove = []
            for caption_file in caption_files:
                lang_code = caption_file.stem.split(".")[-1]

                # Check if this is a -orig variant
                if lang_code.endswith('-orig'):
                    base_lang = lang_code[:-5]  # Remove '-orig' suffix
                    base_file = output_dir / f"{base_filename}.{base_lang}.vtt"

                    if base_file.exists():
                        # Compare file contents
                        try:
                            with open(caption_file, 'rb') as f1, open(base_file, 'rb') as f2:
                                if f1.read() == f2.read():
                                    # Files are identical - remove -orig variant
                                    logger.debug(f"Removing duplicate {lang_code} (identical to {base_lang})")
                                    caption_file.unlink()
                                    files_to_remove.append(caption_file)
                                else:
                                    logger.debug(f"Keeping both {lang_code} and {base_lang} (differ)")
                        except Exception as e:
                            logger.warning(f"Failed to compare {lang_code} and {base_lang}: {e}")

            # Update caption_files to exclude removed files
            caption_files = [f for f in caption_files if f not in files_to_remove]

            # Build metadata for each downloaded caption
            captions_metadata = []
            fetched_at = datetime.now().isoformat()

            for caption_file in caption_files:
                # Extract language code from filename (video_id.lang.vtt)
                lang_code = caption_file.stem.split(".")[-1]

                # Determine caption type
                is_manual = lang_code in subtitles
                is_auto_generated = lang_code in automatic_captions and not is_manual

                # Check if auto-translated
                is_auto_translated = False
                if is_auto_generated and lang_code in automatic_captions:
                    variants = automatic_captions[lang_code]
                    if variants and len(variants) > 0:
                        url = variants[0].get('url', '')
                        is_auto_translated = 'tlang=' in url

                # Path relative to repo root (video directory is videos/VIDEO_DIR/)
                relative_path = caption_file.relative_to(output_dir.parent.parent)

                captions_metadata.append({
                    'language_code': lang_code,
                    'auto_generated': is_auto_generated,
                    'auto_translated': is_auto_translated,
                    'file_path': str(relative_path),
                    'fetched_at': fetched_at
                })

            logger.info(f"Downloaded {len(captions_metadata)} caption(s): {[c['language_code'] for c in captions_metadata]}")
            return captions_metadata

        except Exception as e:
            logger.error(f"Failed to download captions: {e}")
            return []

    def download_comments(
        self,
        video_id: str,
        output_path: Path,
        max_depth: int | None = None,
        max_replies_per_thread: int = 10
    ) -> bool:
        """Download comments for a video with smart incremental fetching.

        Fetches ALL comments by default (no limit), including comment replies.
        If comments.json already exists, merges new comments with existing ones
        (deduplicates by comment_id).

        NOTE: max_depth limits top-level comments PER FETCH, not total. Total count
        can exceed max_depth due to incremental merging across multiple runs.

        Args:
            video_id: YouTube video ID
            output_path: Path to save comments JSON file
            max_depth: Maximum number of top-level comments to fetch per run
                      (None = unlimited, 0 = disabled)
            max_replies_per_thread: Maximum number of replies to fetch per comment
                      thread (default: 10). Set to 0 to disable reply fetching.

        Returns:
            True if successful, False otherwise
        """
        if max_depth == 0:
            logger.debug(f"Comments disabled (max_depth=0) for: {video_id}")
            return False

        # Load existing comments for incremental update
        existing_comments = {}
        existing_comment_ids = set()
        if output_path.exists():
            try:
                with open(output_path, encoding='utf-8') as f:
                    existing_list = json.load(f)
                    existing_comments = {c['comment_id']: c for c in existing_list if c.get('comment_id')}
                    existing_comment_ids = set(existing_comments.keys())
                    logger.info(f"Loaded {len(existing_comments)} existing comments for incremental update")
            except Exception as e:
                logger.warning(f"Failed to load existing comments: {e}")

        max_str = f"up to {max_depth} parents" if max_depth else "all parents (unlimited)"
        replies_str = f"{max_replies_per_thread} replies/thread" if max_replies_per_thread > 0 else "no replies"
        logger.info(f"Downloading comments for: {video_id} ({max_str}, {replies_str})")

        # Try YouTube Data API first (supports reply threading properly)
        comments = []
        comment_source = "yt-dlp"  # Track which source we used

        try:
            api_service = YouTubeAPICommentsService()
            logger.info(f"Attempting to fetch comments via YouTube Data API for: {video_id}")

            comments = api_service.fetch_comments(
                video_id=video_id,
                max_comments=max_depth,
                max_replies_per_thread=max_replies_per_thread,
                existing_comment_ids=existing_comment_ids if existing_comment_ids else None
            )

            if comments:
                comment_source = "youtube-api"
                logger.info(f"Successfully fetched {len(comments)} comments via YouTube Data API")
        except ValueError as e:
            # No API key configured - fall back to yt-dlp
            logger.debug(f"YouTube Data API not available: {e}")
            logger.info("Falling back to yt-dlp for comment fetching")
        except Exception as e:
            # API error (quota exceeded, network error, etc.) - fall back to yt-dlp
            logger.warning(f"YouTube Data API failed: {e}")
            logger.info("Falling back to yt-dlp for comment fetching")

        # Fall back to yt-dlp if API didn't return comments
        if not comments:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            ydl_opts = self._get_ydl_opts(download=False)
            ydl_opts.update({
                "getcomments": True,
                "writeinfojson": False,  # Don't write info json
            })

            # Configure comment fetching with reply support
            # Format: [max_parents, max_replies_per_thread, max_total_replies, reserved]
            # See: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/youtube.py#L3356
            if max_depth or max_replies_per_thread > 0:
                max_parents = str(max_depth) if max_depth else ''
                max_replies = str(max_replies_per_thread) if max_replies_per_thread > 0 else '0'
                # total_replies = unlimited (empty string)
                ydl_opts["extractor_args"] = {
                    "youtube": {
                        "max_comments": [max_parents, max_replies, '', '']
                    }
                }

            def _download():
                with self._semaphore_guard():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # Extract info with comments
                        info = ydl.extract_info(video_url, download=False)
                        return info

            try:
                # Retry on rate limits
                info = self._with_rate_limit_retry(_download)

                if not info:
                    logger.warning(f"No info available for video: {video_id}")
                    return False

                # Extract comments from yt-dlp
                comments = info.get('comments', [])

                if not comments and not existing_comments:
                    logger.info(f"No comments available for video: {video_id}")
                    # Still save empty comments file for consistency
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with AtomicFileWriter(output_path) as f:
                        json.dump([], f, indent=2)
                    return True

            except Exception as e:
                logger.error(f"Failed to download comments via yt-dlp: {e}")
                if not existing_comments:
                    return False
                # If we have existing comments, continue with those
                comments = []

        # Normalize comments to annextube format
        # YouTube API already returns correct format, yt-dlp needs conversion
        if comment_source == "yt-dlp" and comments:
            # Debug: Log sample comment fields to understand what yt-dlp provides
            if logger.isEnabledFor(5):  # DEBUG level
                sample = comments[0]
                logger.debug(f"Sample yt-dlp comment fields: {list(sample.keys())}")
                logger.debug(f"Sample timestamp type: {type(sample.get('timestamp'))}, value: {sample.get('timestamp')}")

            # Convert yt-dlp format to annextube format
            normalized_comments = []
            for comment in comments:
                comment_id = comment.get('id', '')
                if not comment_id:
                    continue

                # Normalize timestamp
                timestamp = comment.get('timestamp')
                if timestamp is not None:
                    timestamp = int(timestamp)

                normalized_comments.append({
                    'comment_id': comment_id,
                    'author': comment.get('author', ''),
                    'author_id': comment.get('author_id', ''),
                    'text': comment.get('text', ''),
                    'timestamp': timestamp,
                    'like_count': comment.get('like_count', 0),
                    'is_favorited': comment.get('is_favorited', False),
                    'parent': comment.get('parent', 'root'),
                })
            comments = normalized_comments

        # Merge new comments with existing ones
        new_count = 0
        updated_count = 0
        for comment in comments:
            comment_id = comment.get('comment_id', '')
            if not comment_id:
                continue

            # Check if this is a new comment
            if comment_id not in existing_comments:
                # New comment - add all fields
                new_count += 1
                existing_comments[comment_id] = comment
            else:
                # Existing comment - only update fields that can change
                # Preserve original timestamp, author, text, etc. (stable fields)
                existing = existing_comments[comment_id]

                # Update like_count if changed
                new_like_count = comment.get('like_count', 0)
                if existing.get('like_count', 0) != new_like_count:
                    existing['like_count'] = new_like_count
                    updated_count += 1

                # Update is_favorited if changed
                new_favorited = comment.get('is_favorited', False)
                if existing.get('is_favorited', False) != new_favorited:
                    existing['is_favorited'] = new_favorited
                    if updated_count == 0:  # Only count once per comment
                        updated_count += 1

        # Convert back to list and save
        final_comments = list(existing_comments.values())

        # Save comments to JSON file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with AtomicFileWriter(output_path) as f:
            json.dump(final_comments, f, indent=2, ensure_ascii=False)

        # Count root vs reply comments for better statistics
        root_comments = [c for c in final_comments if c.get('parent') == 'root']
        reply_comments = [c for c in final_comments if c.get('parent') != 'root']

        if new_count > 0 or updated_count > 0:
            parts = []
            if new_count > 0:
                parts.append(f"{new_count} new")
            if updated_count > 0:
                parts.append(f"{updated_count} updated")
            logger.info(
                f"Comments ({comment_source}): {', '.join(parts)}, "
                f"total: {len(final_comments)} ({len(root_comments)} top-level, {len(reply_comments)} replies)"
            )
        else:
            logger.info(
                f"No comment changes ({comment_source}), {len(final_comments)} existing "
                f"({len(root_comments)} top-level, {len(reply_comments)} replies)"
            )
        return True

    def metadata_to_video(
        self,
        metadata: dict[str, Any],
        enhance_with_api: bool = True,
        api_metadata_cache: dict[str, dict] | None = None,
    ) -> Video:
        """Convert metadata to Video model.

        Handles both yt-dlp schema (id) and our stored schema (video_id).
        Optionally enhances metadata with YouTube Data API v3 for accurate
        license information and additional fields.

        Args:
            metadata: yt-dlp metadata dictionary OR stored Video.to_dict() format
            enhance_with_api: Whether to enhance metadata with YouTube API (default: True)
            api_metadata_cache: Pre-fetched API metadata dict (video_id -> metadata).
                If provided and video_id is in cache, uses cached data instead of
                making a per-video API call. Enables batch API efficiency.

        Returns:
            Video model instance

        Raises:
            ValueError: If video_id/id is missing from metadata
        """
        # Extract video_id - handle both yt-dlp schema ("id") and stored schema ("video_id")
        video_id = metadata.get("video_id") or metadata.get("id")
        if not video_id:
            raise ValueError(f"Missing video_id/id in metadata. Available keys: {list(metadata.keys())}")

        # Enhance metadata with YouTube API if available and enabled
        api_metadata = {}
        if enhance_with_api and self.api_client and "video_id" not in metadata:
            # Only enhance for yt-dlp metadata (new videos), not stored metadata
            if api_metadata_cache is not None and video_id in api_metadata_cache:
                # Use pre-fetched batch data
                api_metadata = api_metadata_cache[video_id]
                if api_metadata:
                    logger.debug(f"Using cached API metadata for {video_id}")
            else:
                try:
                    api_data = self.api_client.enhance_video_metadata(video_id)
                    api_metadata = api_data.get(video_id, {})
                    if api_metadata:
                        logger.info(f"Enhanced metadata for {video_id} with YouTube API")
                except Exception as e:
                    logger.warning(f"Failed to enhance metadata with API for {video_id}: {e}")

        # Parse published date - handle both yt-dlp format and stored ISO format
        published_str = metadata.get("upload_date", "") or metadata.get("published_at", "")
        if published_str:
            try:
                # Try yt-dlp format first (YYYYMMDD)
                published_at = datetime.strptime(published_str, "%Y%m%d")
            except ValueError:
                try:
                    # Try ISO format (stored format)
                    published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Could not parse published date: {published_str}")
                    published_at = datetime.now()
        else:
            published_at = datetime.now()

        # Get available caption languages
        # For stored metadata (from metadata.json), use the stored captions_available list
        # For yt-dlp metadata (new videos), start with empty list - will be populated after download
        if "captions_available" in metadata:
            # Stored metadata - use what was actually downloaded
            all_captions = metadata.get("captions_available", [])
            has_auto_captions = metadata.get("has_auto_captions", False)
        else:
            # yt-dlp metadata - don't populate yet, will be set after download
            all_captions = []
            # Check if automatic_captions are available in yt-dlp metadata
            auto_captions = metadata.get("automatic_captions", {})
            has_auto_captions = len(auto_captions) > 0

        # Get tags, handle both list and None
        tags = metadata.get("tags")
        if tags is None:
            tags = []
        elif not isinstance(tags, list):
            tags = []

        # Get category - handle both yt-dlp and stored format
        category = metadata.get("category", "")
        categories = metadata.get("categories", [category] if category else [])

        # Handle channel_name - yt-dlp uses "channel", stored uses "channel_name"
        channel_name = metadata.get("channel_name") or metadata.get("channel") or metadata.get("uploader", "")

        # Handle thumbnail - yt-dlp uses "thumbnail", stored uses "thumbnail_url"
        thumbnail_url = metadata.get("thumbnail_url") or metadata.get("thumbnail", "")

        # Parse recording_date from API if present
        recording_date = None
        if api_metadata.get("recording_date"):
            try:
                # Replace 'Z' with '+00:00' for Python 3.10 compatibility
                date_str = api_metadata["recording_date"].replace('Z', '+00:00')
                recording_date = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                logger.warning(f"Invalid recording_date format: {api_metadata['recording_date']}")

        return Video(
            video_id=video_id,  # Use extracted video_id
            title=metadata.get("title", "Unknown"),
            description=metadata.get("description", ""),
            channel_id=metadata.get("channel_id", metadata.get("uploader_id", "")),
            channel_name=channel_name,
            published_at=published_at,
            duration=int(metadata.get("duration", 0) or 0),
            view_count=int(metadata.get("view_count", 0) or 0),
            like_count=int(metadata.get("like_count", 0) or 0),
            comment_count=int(metadata.get("comment_count", 0) or 0),
            thumbnail_url=thumbnail_url,
            # License - prefer API data (accurate), fallback to yt-dlp, default to "standard"
            license=api_metadata.get("license") or metadata.get("license") or "standard",
            privacy_status=metadata.get("privacy_status", "public"),
            availability=metadata.get("availability", "public"),
            tags=tags,
            categories=categories,
            language=metadata.get("language"),
            captions_available=all_captions,  # Empty for new videos, populated after download
            has_auto_captions=has_auto_captions,
            download_status=metadata.get("download_status", "not_downloaded"),
            source_url=metadata.get("source_url") or metadata.get("webpage_url", f"https://www.youtube.com/watch?v={video_id}"),
            fetched_at=datetime.now(),
            # Enhanced metadata from YouTube API (optional)
            licensed_content=api_metadata.get("licensed_content"),
            embeddable=api_metadata.get("embeddable"),
            made_for_kids=api_metadata.get("made_for_kids"),
            recording_date=recording_date,
            recording_location=api_metadata.get("recording_location"),
            location_description=api_metadata.get("location_description"),
            definition=api_metadata.get("definition"),
            dimension=api_metadata.get("dimension"),
            projection=api_metadata.get("projection"),
            region_restriction=api_metadata.get("region_restriction"),
            content_rating=api_metadata.get("content_rating"),
            topic_categories=api_metadata.get("topic_categories"),
        )
