"""YouTube service using yt-dlp for metadata and video operations."""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yt_dlp

from annextube.lib.logging_config import get_logger
from annextube.models.playlist import Playlist
from annextube.models.video import Video

logger = get_logger(__name__)

# Retry configuration for rate limits
MAX_RETRIES = 3
INITIAL_BACKOFF = 5  # seconds
BACKOFF_MULTIPLIER = 2


class YouTubeService:
    """Wrapper around yt-dlp for YouTube operations."""

    def __init__(self, archive_file: Optional[Path] = None):
        """Initialize YouTubeService.

        Args:
            archive_file: Optional path to yt-dlp archive file for tracking
        """
        self.archive_file = archive_file

    def _retry_on_rate_limit(self, func, *args, **kwargs):
        """Retry function on rate limit errors with exponential backoff.

        Respects Retry-After header if present in response.

        Args:
            func: Function to retry
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted
        """
        backoff = INITIAL_BACKOFF
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)

                # Log full error details for debugging
                logger.debug(f"YouTube API error (attempt {attempt + 1}/{MAX_RETRIES}): {error_str}")

                # Try to extract HTTP status code and headers from exception
                status_code = None
                if hasattr(e, 'code'):
                    status_code = e.code
                elif "429" in error_str or "Too Many Requests" in error_str:
                    status_code = 429
                elif "403" in error_str or "Forbidden" in error_str:
                    status_code = 403

                # Log response headers if available
                if hasattr(e, 'headers'):
                    logger.warning(f"HTTP {status_code} Response Headers: {dict(e.headers)}")
                elif hasattr(e, 'response') and hasattr(e.response, 'headers'):
                    logger.warning(f"HTTP {status_code} Response Headers: {dict(e.response.headers)}")
                else:
                    # yt-dlp embeds headers in error message, try to extract
                    if "headers:" in error_str.lower():
                        logger.warning(f"Error details: {error_str}")

                # Check if it's a rate limit error (429)
                if status_code == 429 or "429" in error_str or "Too Many Requests" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        # Try to extract Retry-After from error message or headers
                        retry_after = None

                        # First try exception attributes
                        if hasattr(e, 'headers') and 'Retry-After' in e.headers:
                            try:
                                retry_after = int(e.headers['Retry-After'])
                            except (ValueError, KeyError):
                                pass

                        # Fall back to parsing error message
                        if retry_after is None and "Retry-After:" in error_str:
                            try:
                                # Extract number from "Retry-After: XX"
                                parts = error_str.split("Retry-After:")
                                if len(parts) > 1:
                                    retry_after = int(parts[1].strip().split()[0])
                            except (ValueError, IndexError):
                                pass

                        wait_time = retry_after if retry_after else backoff
                        logger.warning(
                            f"Rate limit hit, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{MAX_RETRIES})"
                            f"{' (from Retry-After header)' if retry_after else ''}"
                        )
                        time.sleep(wait_time)
                        backoff *= BACKOFF_MULTIPLIER
                        continue
                # Not a rate limit error or exhausted retries
                raise

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
        self, channel_url: str, limit: Optional[int] = None,
        existing_video_ids: Optional[set[str]] = None
    ) -> List[Dict[str, Any]]:
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
            # First pass: Get just IDs with extract_flat
            flat_opts = ydl_opts.copy()
            flat_opts.update({
                "extract_flat": "in_playlist",  # Just get video IDs, no metadata
                "playlistend": limit if limit else None,
                "ignoreerrors": True,
            })

            logger.debug("First pass: fetching video IDs only (extract_flat)")
            with yt_dlp.YoutubeDL(flat_opts) as ydl_flat:
                try:
                    info = ydl_flat.extract_info(channel_url, download=False)
                    if not info or not info.get("entries"):
                        logger.warning("No videos found in channel")
                        return []

                    # Filter to find new video IDs
                    all_entries = list(info.get("entries", []))
                    new_video_ids = []
                    consecutive_existing = 0

                    for entry in all_entries:
                        if not entry or not entry.get("id"):
                            continue

                        video_id = entry["id"]
                        if video_id in existing_video_ids:
                            logger.debug(f"Skipping existing video: {video_id}")
                            consecutive_existing += 1
                            if consecutive_existing >= 10:
                                logger.info(f"Stopping: found 10 consecutive existing videos")
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
                full_opts = ydl_opts.copy()
                full_opts.update({
                    "ignoreerrors": True,
                    "no_warnings": False,
                })

                videos = []
                with yt_dlp.YoutubeDL(full_opts) as ydl_full:
                    for video_id in new_video_ids:
                        try:
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                            video_info = ydl_full.extract_info(video_url, download=False)
                            if video_info:
                                videos.append(video_info)
                        except Exception as e:
                            logger.warning(f"Failed to fetch metadata for {video_id}: {e}")

                logger.info(f"Successfully fetched metadata for {len(videos)} new video(s)")
                return videos

        # Regular extraction (initial backup or fallback)
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
                # In incremental mode, stop when we hit consecutive existing videos
                videos = []
                consecutive_existing = 0
                max_consecutive_existing = 10  # Stop after 10 consecutive existing videos

                for entry in entries:
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
        self, playlist_url: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get videos from a playlist.

        Args:
            playlist_url: YouTube playlist URL
            limit: Optional limit for number of videos (most recent)

        Returns:
            List of video metadata dictionaries
        """
        logger.info(f"Fetching videos from playlist: {playlist_url}")

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
                # Extract playlist info (gets full metadata for all videos)
                info = ydl.extract_info(playlist_url, download=False)

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
                logger.error(f"Failed to fetch playlist videos: {e}", exc_info=True)
                return []

    def get_playlist_metadata(self, playlist_url: str) -> Optional[Playlist]:
        """Get metadata for a playlist.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            Playlist model instance or None if failed
        """
        logger.debug(f"Fetching playlist metadata: {playlist_url}")

        ydl_opts = self._get_ydl_opts(download=False)
        ydl_opts["extract_flat"] = True  # Don't fetch individual videos

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(playlist_url, download=False)

                if not info:
                    return None

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
                    updated_at=datetime.now(),
                )

            except Exception as e:
                logger.error(f"Failed to fetch playlist metadata: {e}")
                return None

    def get_channel_playlists(self, channel_url: str) -> List[Dict[str, Any]]:
        """Get all playlists from a channel.

        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channel)

        Returns:
            List of playlist dicts with: id, title, url, video_count
        """
        logger.debug(f"Discovering playlists from channel: {channel_url}")

        # Construct playlists tab URL
        playlists_url = channel_url.rstrip("/") + "/playlists"

        ydl_opts = self._get_ydl_opts(download=False)
        ydl_opts["extract_flat"] = True  # Don't fetch individual playlist videos

        playlists = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlists_url, download=False)

                if not info or "entries" not in info:
                    logger.warning(f"No playlists found for channel: {channel_url}")
                    return []

                for entry in info["entries"]:
                    if entry and entry.get("_type") == "url" and entry.get("ie_key") == "YoutubeTab":
                        # Extract playlist ID from URL
                        playlist_id = None
                        url = entry.get("url", "")
                        if "list=" in url:
                            playlist_id = url.split("list=")[1].split("&")[0]

                        playlists.append({
                            "id": playlist_id or entry.get("id"),
                            "title": entry.get("title", "Unknown"),
                            "url": url,
                            "video_count": entry.get("playlist_count", 0),
                        })

                logger.info(f"Discovered {len(playlists)} playlists from {channel_url}")
                return playlists

        except Exception as e:
            logger.error(f"Failed to fetch channel playlists: {e}")
            return []

    def get_channel_podcasts(self, channel_url: str) -> List[Dict[str, Any]]:
        """Get all podcasts from a channel's Podcasts tab.

        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channel)

        Returns:
            List of podcast dicts with: id, title, url, video_count
        """
        logger.debug(f"Discovering podcasts from channel: {channel_url}")

        # Construct podcasts tab URL
        podcasts_url = channel_url.rstrip("/") + "/podcasts"

        ydl_opts = self._get_ydl_opts(download=False)
        ydl_opts["extract_flat"] = True

        podcasts = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(podcasts_url, download=False)

                if not info or "entries" not in info:
                    logger.debug(f"No podcasts found for channel: {channel_url}")
                    return []

                for entry in info["entries"]:
                    if entry and entry.get("_type") == "url" and entry.get("ie_key") == "YoutubeTab":
                        # Extract playlist ID from URL
                        playlist_id = None
                        url = entry.get("url", "")
                        if "list=" in url:
                            playlist_id = url.split("list=")[1].split("&")[0]

                        podcasts.append({
                            "id": playlist_id or entry.get("id"),
                            "title": entry.get("title", "Unknown"),
                            "url": url,
                            "video_count": entry.get("playlist_count", 0),
                        })

                logger.info(f"Discovered {len(podcasts)} podcasts from {channel_url}")
                return podcasts

        except Exception as e:
            logger.debug(f"Failed to fetch channel podcasts (may not have podcasts): {e}")
            return []

    def get_video_metadata(self, video_url: str) -> Optional[Dict[str, Any]]:
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

        ydl_opts = self._get_ydl_opts(download=False)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                return info
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

    def download_captions(
        self, video_id: str, output_dir: Path, language_pattern: str = ".*"
    ) -> List[Dict[str, Any]]:
        """Download captions for a video, filtered by language pattern.

        Args:
            video_id: YouTube video ID
            output_dir: Directory to save captions
            language_pattern: Regex pattern for filtering caption languages
                             (default: ".*" for all languages)
                             Examples: "en.*" for English variants,
                                      "en|es|fr" for specific languages

        Returns:
            List of caption metadata dictionaries with keys:
            - language_code: Language code (e.g., 'en', 'es')
            - auto_generated: Whether caption is auto-generated
            - file_path: Path to caption file
            - fetched_at: ISO 8601 timestamp when fetched
        """
        logger.info(f"Downloading captions for: {video_id} (filter: {language_pattern})")

        output_dir.mkdir(parents=True, exist_ok=True)

        # First, get video info to see available captions
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            # Get available captions without downloading
            ydl_opts_info = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(video_url, download=False)

            if not info:
                logger.warning(f"No info available for video: {video_id}")
                return []

            # Get available subtitles
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            all_available = set(list(subtitles.keys()) + list(automatic_captions.keys()))

            if not all_available:
                logger.info(f"No captions available for video: {video_id}")
                return []

            # Filter by language pattern
            pattern = re.compile(language_pattern)
            matching_langs = [lang for lang in all_available if pattern.match(lang)]

            if not matching_langs:
                logger.info(
                    f"No captions matching pattern '{language_pattern}' "
                    f"(available: {sorted(all_available)})"
                )
                return []

            logger.info(
                f"Found {len(matching_langs)} matching caption(s): {sorted(matching_langs)} "
                f"(from {len(all_available)} available)"
            )

            # Download only matching captions
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": matching_langs,
                "subtitlesformat": "vtt",
                "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            }

            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Download subtitles
                    ydl.download([video_url])

            # Retry on rate limits
            self._retry_on_rate_limit(_download)

            # Find downloaded caption files
            caption_files = list(output_dir.glob(f"{video_id}.*.vtt"))

            # Build metadata for each caption
            captions_metadata = []
            fetched_at = datetime.now().isoformat()

            for caption_file in caption_files:
                # Extract language code from filename (video_id.lang.vtt)
                lang_code = caption_file.stem.split(".")[-1]

                # Determine if auto-generated
                is_auto = lang_code in automatic_captions

                captions_metadata.append({
                    'language_code': lang_code,
                    'auto_generated': is_auto,
                    'file_path': str(caption_file.relative_to(output_dir.parent.parent)),  # Relative to repo root
                    'fetched_at': fetched_at
                })

            logger.info(f"Downloaded {len(captions_metadata)} caption(s): {[c['language_code'] for c in captions_metadata]}")
            return captions_metadata

        except Exception as e:
            logger.error(f"Failed to download captions: {e}")
            return []

    def download_comments(self, video_id: str, output_path: Path, max_depth: Optional[int] = None) -> bool:
        """Download comments for a video with smart incremental fetching.

        Fetches ALL comments by default (no limit). If comments.json already exists,
        merges new comments with existing ones (deduplicates by comment_id).

        Args:
            video_id: YouTube video ID
            output_path: Path to save comments JSON file
            max_depth: Maximum number of comments to fetch (None = unlimited, 0 = disabled)

        Returns:
            True if successful, False otherwise
        """
        if max_depth == 0:
            logger.debug(f"Comments disabled (max_depth=0) for: {video_id}")
            return False

        # Load existing comments for incremental update
        existing_comments = {}
        if output_path.exists():
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    existing_list = json.load(f)
                    existing_comments = {c['comment_id']: c for c in existing_list if c.get('comment_id')}
                    logger.info(f"Loaded {len(existing_comments)} existing comments for incremental update")
            except Exception as e:
                logger.warning(f"Failed to load existing comments: {e}")

        max_str = max_depth if max_depth else "unlimited"
        logger.info(f"Downloading comments for: {video_id} (max: {max_str})")

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "getcomments": True,
            "writeinfojson": False,  # Don't write info json
        }

        # Only set max_comments if specified (otherwise fetch all)
        if max_depth:
            ydl_opts["max_comments"] = max_depth

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info with comments
                info = ydl.extract_info(video_url, download=False)
                return info

        try:
            # Retry on rate limits
            info = self._retry_on_rate_limit(_download)

            if not info:
                logger.warning(f"No info available for video: {video_id}")
                return False

            # Extract comments
            comments = info.get('comments', [])

            if not comments and not existing_comments:
                logger.info(f"No comments available for video: {video_id}")
                # Still save empty comments file for consistency
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2)
                return True

            # Debug: Log sample comment fields to understand what yt-dlp provides
            if comments and logger.isEnabledFor(5):  # DEBUG level
                sample = comments[0]
                logger.debug(f"Sample comment fields: {list(sample.keys())}")
                logger.debug(f"Sample timestamp type: {type(sample.get('timestamp'))}, value: {sample.get('timestamp')}")

            # Format comments for storage
            new_count = 0
            updated_count = 0
            for comment in comments:
                comment_id = comment.get('id', '')
                if not comment_id:
                    continue

                # Check if this is a new comment
                if comment_id not in existing_comments:
                    # New comment - add all fields
                    new_count += 1

                    # Normalize timestamp: ensure it's an integer (Unix timestamp from API)
                    # yt-dlp provides timestamp as Unix epoch seconds (should be stable)
                    timestamp = comment.get('timestamp')
                    if timestamp is not None:
                        # Convert to int if it's a float (removes sub-second precision variations)
                        timestamp = int(timestamp)

                    existing_comments[comment_id] = {
                        'comment_id': comment_id,
                        'author': comment.get('author', ''),
                        'author_id': comment.get('author_id', ''),
                        'text': comment.get('text', ''),
                        'timestamp': timestamp,  # Unix timestamp from YouTube API (stable)
                        'like_count': comment.get('like_count', 0),
                        'is_favorited': comment.get('is_favorited', False),
                        'parent': comment.get('parent', 'root'),  # 'root' or parent comment ID
                    }
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
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_comments, f, indent=2, ensure_ascii=False)

            if new_count > 0 or updated_count > 0:
                parts = []
                if new_count > 0:
                    parts.append(f"{new_count} new")
                if updated_count > 0:
                    parts.append(f"{updated_count} updated")
                logger.info(f"Comments: {', '.join(parts)}, total: {len(final_comments)}")
            else:
                logger.info(f"No comment changes, {len(final_comments)} existing comment(s)")
            return True

        except Exception as e:
            logger.error(f"Failed to download comments: {e}")
            return False

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

        # Get available caption languages (sorted for deterministic ordering)
        subtitles = metadata.get("subtitles", {})
        auto_captions = metadata.get("automatic_captions", {})
        all_captions = sorted(set(list(subtitles.keys()) + list(auto_captions.keys())))

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
            captions_available=all_captions,  # Already sorted list
            has_auto_captions=len(auto_captions) > 0,
            download_status="not_downloaded",
            source_url=metadata.get("webpage_url", f"https://www.youtube.com/watch?v={metadata['id']}"),
            fetched_at=datetime.now(),
            updated_at=datetime.now(),
        )
