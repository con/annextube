"""Export service for generating TSV metadata files."""

import json
import os
import urllib.request
from pathlib import Path

import magic

from annextube.lib.logging_config import get_logger
from annextube.lib.tsv_utils import escape_tsv_field

from .authors import AuthorsService

logger = get_logger(__name__)


class ExportService:
    """Service for exporting archive metadata to TSV format."""

    def __init__(self, repo_path: Path):
        """Initialize ExportService.

        Args:
            repo_path: Path to archive repository
        """
        self.repo_path = repo_path

    def generate_videos_tsv(self, output_path: Path | None = None,
                            base_dir: Path | None = None) -> Path:
        """Generate videos.tsv with summary metadata for all videos in a directory.

        Scans base_dir for metadata.json files (follows symlinks) and extracts
        key metadata. Works for both videos/ directory and playlist directories
        containing symlinks to video directories.

        Args:
            output_path: Optional custom output path (default: base_dir/videos.tsv)
            base_dir: Directory to scan for metadata.json files
                      (default: repo_path/videos/)

        Returns:
            Path to generated TSV file
        """
        if base_dir is None:
            base_dir = self.repo_path / "videos"

        if output_path is None:
            output_path = base_dir / "videos.tsv"

        logger.info(f"Generating videos.tsv at {output_path}")

        if not base_dir.exists():
            logger.warning(f"Directory {base_dir} does not exist, creating empty TSV")
            self._write_empty_videos_tsv(output_path)
            return output_path

        # Collect video metadata
        # Find all video directories by looking for metadata.json files
        # This supports both flat and hierarchical directory structures
        # Use os.walk with followlinks=True because Path.rglob does NOT
        # follow directory symlinks (playlist dirs contain symlinks to video dirs)
        videos = []
        metadata_paths: list[Path] = []
        for root, _dirs, files in os.walk(base_dir, followlinks=True):
            if "metadata.json" in files:
                metadata_paths.append(Path(root) / "metadata.json")
        for metadata_path in sorted(metadata_paths):
            video_dir = metadata_path.parent

            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)

                # Reconcile captions_available with actual VTT files on disk.
                # Captions may exist but not be listed in metadata.json if they
                # were downloaded after the initial metadata was saved.
                vtt_langs = sorted(
                    p.stem.split(".", 1)[1]       # "video.en" → "en"
                    for p in video_dir.glob("video.*.vtt")
                    if "." in p.stem               # skip "video.vtt" (no lang)
                )
                stored_captions = metadata.get("captions_available", [])
                if vtt_langs and sorted(stored_captions) != vtt_langs:
                    metadata["captions_available"] = vtt_langs
                    with open(metadata_path, "w", encoding="utf-8") as fw:
                        json.dump(metadata, fw, indent=2)
                    logger.info(
                        f"Updated captions_available for {metadata.get('video_id', '?')}: "
                        f"{stored_captions} → {vtt_langs}"
                    )

                # Merge extra_metadata.json into metadata.json (if present).
                # extra_metadata.json is user-managed; fields are additive only
                # (never overwrite archiver-managed fields in metadata.json).
                extra_path = video_dir / "extra_metadata.json"
                if extra_path.exists():
                    try:
                        with open(extra_path) as ef:
                            extra = json.load(ef)
                        changed = False
                        for key, value in extra.items():
                            if key not in metadata:
                                metadata[key] = value
                                changed = True
                        if changed:
                            with open(metadata_path, "w", encoding="utf-8") as fw:
                                json.dump(metadata, fw, indent=2)
                            logger.info(
                                f"Merged extra_metadata.json for "
                                f"{metadata.get('video_id', '?')}"
                            )
                    except (json.JSONDecodeError, OSError) as exc:
                        logger.warning(
                            f"Could not read extra_metadata.json for "
                            f"{metadata.get('video_id', '?')}: {exc}"
                        )

                # Extract key fields for TSV (frontend-compatible format)
                video_id = metadata.get("video_id", "")

                # Get relative path from base directory
                # For videos/: gives "2026/01/video_name"
                # For playlists/: gives "0001_video_name" (symlink name)
                relative_path = video_dir.relative_to(base_dir)

                # Use download_status from metadata.json - reflects ACTION taken, not current availability
                # Availability (whether content is present) is git-annex's domain.
                # Frontend checks actual file availability via HEAD request.
                # Map spec values to frontend-friendly values:
                #   downloaded → downloaded
                #   not_downloaded/failed/tracked → metadata_only
                raw_status = metadata.get("download_status", "not_downloaded")
                if raw_status == "downloaded":
                    download_status = "downloaded"
                else:
                    download_status = "metadata_only"

                video_entry = {
                    "video_id": video_id,
                    "title": metadata.get("title", ""),
                    "channel_id": metadata.get("channel_id", ""),
                    "channel_name": metadata.get("channel_name", ""),
                    "published_at": metadata.get("published_at", ""),
                    "duration": str(metadata.get("duration", 0)),
                    "view_count": str(metadata.get("view_count", 0)),
                    "like_count": str(metadata.get("like_count", 0)),
                    "comment_count": str(metadata.get("comment_count", 0)),
                    "thumbnail_url": metadata.get("thumbnail_url", ""),
                    "download_status": download_status,
                    "source_url": f"https://www.youtube.com/watch?v={video_id}",
                    "path": str(relative_path),  # Relative to videos/ directory (e.g., "2026/01/video_dir" for hierarchical)
                }
                videos.append(video_entry)

            except Exception as e:
                logger.error(f"Failed to read metadata from {video_dir.relative_to(base_dir)}: {e}")

        # Write TSV file
        self._write_videos_tsv(output_path, videos)
        logger.info(f"Generated videos.tsv with {len(videos)} entries")

        return output_path

    def generate_playlists_tsv(self, output_path: Path | None = None) -> Path:
        """Generate playlists/playlists.tsv mapping folder names to playlist metadata.

        Scans playlists/ directory and extracts metadata from each
        playlist's playlist.json file. Maps sanitized folder names to
        YouTube playlist IDs and other metadata.

        Args:
            output_path: Optional custom output path (default: repo_path/playlists/playlists.tsv)

        Returns:
            Path to generated TSV file
        """
        if output_path is None:
            output_path = self.repo_path / "playlists" / "playlists.tsv"

        logger.info(f"Generating playlists.tsv at {output_path}")

        playlists_dir = self.repo_path / "playlists"
        if not playlists_dir.exists():
            logger.warning("Playlists directory does not exist, creating empty TSV")
            self._write_empty_playlists_tsv(output_path)
            return output_path

        # Collect playlist metadata
        playlists = []
        for playlist_dir in sorted(playlists_dir.iterdir()):
            if not playlist_dir.is_dir():
                continue

            metadata_path = playlist_dir / "playlist.json"
            if not metadata_path.exists():
                logger.warning(f"No playlist.json in {playlist_dir.name}, skipping")
                continue

            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)

                # Count symlinks (videos in playlist)
                video_count = sum(1 for item in playlist_dir.iterdir()
                                  if item.is_symlink() and item.name != "playlist.json")

                # Calculate total duration from symlinked videos
                total_duration = self._calculate_playlist_duration(playlist_dir)

                # Use last_modified for both created_at and last_sync
                last_modified = metadata.get("last_modified") or ""

                # Extract key fields for TSV (frontend-compatible format)
                playlist_entry = {
                    "playlist_id": metadata.get("playlist_id", ""),
                    "title": metadata.get("title", ""),
                    "channel_id": metadata.get("channel_id", ""),
                    "channel_name": metadata.get("channel_name", ""),
                    "video_count": str(video_count),
                    "total_duration": str(total_duration),
                    "privacy_status": metadata.get("privacy_status") or "public",
                    "created_at": last_modified,
                    "last_sync": last_modified,
                    "path": playlist_dir.name,  # Directory name for loading playlist.json
                }
                playlists.append(playlist_entry)

                # Generate per-playlist videos.tsv
                self.generate_videos_tsv(base_dir=playlist_dir)

            except Exception as e:
                logger.error(f"Failed to read metadata from {playlist_dir.name}: {e}")

        # Write TSV file
        self._write_playlists_tsv(output_path, playlists)
        logger.info(f"Generated playlists.tsv with {len(playlists)} entries")

        return output_path

    def generate_all(self) -> tuple[Path, Path, Path]:
        """Generate videos.tsv, playlists.tsv, and authors.tsv.

        Returns:
            Tuple of (videos_tsv_path, playlists_tsv_path, authors_tsv_path)
        """
        videos_tsv = self.generate_videos_tsv()
        playlists_tsv = self.generate_playlists_tsv()

        # Generate authors.tsv
        authors_service = AuthorsService(self.repo_path)
        authors_tsv = authors_service.generate_authors_tsv()

        return videos_tsv, playlists_tsv, authors_tsv

    def generate_channel_json(self) -> Path:
        """Generate channel.json with channel metadata and archive statistics.

        Idempotent operation that:
        1. Extracts fresh channel metadata from YouTube API (preferred) or yt-dlp (fallback)
        2. Calculates archive stats from TSV files and actual video files

        Returns:
            Path to generated channel.json
        """
        import csv
        from datetime import datetime

        from annextube.lib.config import load_config

        logger.info(f"Generating channel.json at {self.repo_path}")

        # Load config to get channel info
        config = load_config(repo_path=self.repo_path)

        if not config.sources:
            raise ValueError("No sources configured. Cannot generate channel.json.")

        # Get first channel source
        channel_source = None
        for source in config.sources:
            if source.type == "channel":
                channel_source = source
                break

        if not channel_source:
            raise ValueError("No channel sources found in config.")

        # Extract channel metadata - try YouTube API first, then yt-dlp
        channel_meta = self._extract_channel_metadata(channel_source.url)

        # Compute archive stats from videos.tsv and actual files
        videos_dir = self.repo_path / "videos"
        videos_tsv = videos_dir / "videos.tsv"
        total_videos = 0
        first_date: str | None = None
        last_date: str | None = None
        total_duration = 0
        total_size = 0

        if videos_tsv.exists():
            try:
                with open(videos_tsv, encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter='\t')
                    rows = list(reader)

                    total_videos = len(rows)

                    if rows:
                        dates: list[str] = [
                            date for row in rows
                            if (date := row.get('published_at')) is not None
                        ]
                        if dates:
                            first_date = min(dates)
                            last_date = max(dates)

                        # Calculate duration from TSV and size from actual files
                        for row in rows:
                            try:
                                total_duration += int(row.get('duration', 0))
                            except (ValueError, TypeError):
                                pass

                            # Calculate actual file size from video.mkv
                            video_path_str = row.get('path', '')
                            if video_path_str:
                                video_file = videos_dir / video_path_str / "video.mkv"
                                if video_file.exists():
                                    try:
                                        if video_file.is_symlink():
                                            target_path = video_file.resolve()
                                            if target_path.exists():
                                                total_size += target_path.stat().st_size
                                        else:
                                            total_size += video_file.stat().st_size
                                    except (OSError, RuntimeError):
                                        pass
            except Exception as e:
                logger.warning(f"Error reading videos.tsv: {e}")

        # Count playlists from playlists directory
        playlist_count = 0
        playlists_dir = self.repo_path / "playlists"
        if playlists_dir.exists():
            playlist_count = sum(1 for item in playlists_dir.iterdir()
                                 if item.is_dir() and (item / "playlist.json").exists())

        archive_stats: dict[str, int | str | None] = {
            "total_videos_archived": total_videos,
            "first_video_date": first_date,
            "last_video_date": last_date,
            "total_duration_seconds": total_duration,
            "total_size_bytes": total_size,
        }

        # Build channel.json combining fresh metadata and archive stats
        now = datetime.now().isoformat()

        channel_data = {
            "channel_id": channel_meta.get("channel_id", ""),
            "name": channel_meta.get("channel_name", ""),
            "description": channel_meta.get("description", ""),
            "custom_url": channel_meta.get("custom_url", ""),
            "subscriber_count": channel_meta.get("subscriber_count", 0),
            "video_count": total_videos,  # Use actual count from archive, not YouTube's count
            "playlist_count": playlist_count,
            "avatar_url": channel_meta.get("avatar_url", ""),
            "banner_url": channel_meta.get("banner_url", ""),
            "country": channel_meta.get("country", ""),
            "created_at": channel_meta.get("created_at", ""),
            "last_sync": now,
            "fetched_at": now,
            "archive_stats": archive_stats,
        }

        # Write channel.json
        output_path = self.repo_path / "channel.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(channel_data, f, indent=2)

        logger.info(
            f"Generated channel.json: {total_videos} videos, "
            f"{playlist_count} playlists, "
            f"{total_size / (1024**3):.2f} GB total"
        )

        # Download channel avatar if available and not already present
        avatar_url = channel_meta.get("avatar_url", "")
        if avatar_url and isinstance(avatar_url, str):
            self._download_channel_avatar(avatar_url)

        return output_path

    def _calculate_playlist_duration(self, playlist_dir: Path) -> int:
        """Calculate total duration of all videos in playlist.

        Args:
            playlist_dir: Path to playlist directory

        Returns:
            Total duration in seconds
        """
        total = 0
        for symlink in playlist_dir.iterdir():
            if not symlink.is_symlink() or symlink.name == "playlist.json":
                continue

            try:
                # Resolve symlink to video directory
                video_dir = symlink.resolve()
                metadata_path = video_dir / "metadata.json"

                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                        total += metadata.get("duration", 0)
            except Exception as e:
                logger.debug(f"Could not read duration from {symlink.name}: {e}")

        return total

    def _write_videos_tsv(self, output_path: Path, videos: list[dict[str, str]]) -> None:
        """Write videos to TSV file with proper escaping.

        Args:
            output_path: Path to output file
            videos: List of video dictionaries
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write header (frontend-compatible format)
            f.write("video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\t"
                    "duration\tview_count\tlike_count\tcomment_count\t"
                    "thumbnail_url\tdownload_status\tsource_url\tpath\n")

            # Write rows (escape special characters in string fields)
            for video in videos:
                f.write(
                    f"{escape_tsv_field(video['video_id'])}\t"
                    f"{escape_tsv_field(video['title'])}\t"
                    f"{escape_tsv_field(video['channel_id'])}\t"
                    f"{escape_tsv_field(video['channel_name'])}\t"
                    f"{escape_tsv_field(video['published_at'])}\t"
                    f"{video['duration']}\t"
                    f"{video['view_count']}\t"
                    f"{video['like_count']}\t"
                    f"{video['comment_count']}\t"
                    f"{escape_tsv_field(video['thumbnail_url'])}\t"
                    f"{escape_tsv_field(video['download_status'])}\t"
                    f"{escape_tsv_field(video['source_url'])}\t"
                    f"{escape_tsv_field(video['path'])}\n"
                )

    def _write_playlists_tsv(self, output_path: Path, playlists: list[dict[str, str]]) -> None:
        """Write playlists to TSV file with proper escaping.

        Args:
            output_path: Path to output file
            playlists: List of playlist dictionaries
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write header (frontend-compatible format)
            f.write("playlist_id\ttitle\tchannel_id\tchannel_name\tvideo_count\t"
                    "total_duration\tprivacy_status\tcreated_at\tlast_sync\tpath\n")

            # Write rows (escape special characters in string fields)
            for playlist in playlists:
                f.write(
                    f"{escape_tsv_field(playlist['playlist_id'])}\t"
                    f"{escape_tsv_field(playlist['title'])}\t"
                    f"{escape_tsv_field(playlist['channel_id'])}\t"
                    f"{escape_tsv_field(playlist['channel_name'])}\t"
                    f"{playlist['video_count']}\t"
                    f"{playlist['total_duration']}\t"
                    f"{escape_tsv_field(playlist['privacy_status'])}\t"
                    f"{escape_tsv_field(playlist['created_at'])}\t"
                    f"{escape_tsv_field(playlist['last_sync'])}\t"
                    f"{escape_tsv_field(playlist['path'])}\n"
                )

    def _write_empty_videos_tsv(self, output_path: Path) -> None:
        """Write empty videos.tsv with header only.

        Args:
            output_path: Path to output file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\t"
                    "duration\tview_count\tlike_count\tcomment_count\t"
                    "thumbnail_url\tdownload_status\tsource_url\tpath\n")

    def _write_empty_playlists_tsv(self, output_path: Path) -> None:
        """Write empty playlists.tsv with header only.

        Args:
            output_path: Path to output file
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("playlist_id\ttitle\tchannel_id\tchannel_name\tvideo_count\t"
                    "total_duration\tprivacy_status\tcreated_at\tlast_sync\tpath\n")

    def _extract_channel_metadata(self, channel_url: str) -> dict[str, str | int]:
        """Extract channel metadata from YouTube API or yt-dlp (fallback).

        Tries YouTube API first (complete metadata), falls back to yt-dlp
        if no API key or API fails, then falls back to parsing URL and videos.

        Args:
            channel_url: YouTube channel URL

        Returns:
            Dictionary with channel metadata fields
        """
        import os

        from annextube.services.youtube import YouTubeService
        from annextube.services.youtube_api import create_api_client

        # Step 1: Try YouTube API (most complete metadata)
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            try:
                api_client = create_api_client(api_key)
                if api_client:
                    # Extract channel ID from URL
                    channel_id = self._parse_channel_id_from_url(channel_url)
                    if channel_id:
                        channel_meta = api_client.get_channel_details(channel_id)
                        if channel_meta:
                            logger.info("Using YouTube API for channel metadata (complete data)")
                            return channel_meta
            except Exception as e:
                logger.warning(f"YouTube API extraction failed, falling back to yt-dlp: {e}")

        # Step 2: Try yt-dlp (partial metadata)
        try:
            youtube = YouTubeService()
            channel_meta = youtube.get_channel_metadata(channel_url)
            if channel_meta and channel_meta.get("channel_id"):
                logger.info("Using yt-dlp for channel metadata (partial data)")
                return channel_meta
        except Exception as e:
            logger.warning(f"yt-dlp extraction failed, using fallback: {e}")

        # Step 3: Fallback - parse from URL and videos
        logger.warning("Using fallback method for channel metadata (minimal data)")

        # Parse custom URL from channel URL
        custom_url = ""
        if "@" in channel_url:
            custom_url = channel_url.split("@")[-1].split("/")[0].split("?")[0]

        # Get channel ID and name from helper
        channel_id = self._parse_channel_id_from_url(channel_url)
        channel_name = self._get_channel_name_from_videos()

        return {
            "channel_id": channel_id or "",
            "channel_name": channel_name,
            "description": "",
            "custom_url": custom_url,
            "avatar_url": "",
            "banner_url": "",
            "country": "",
            "subscriber_count": 0,
            "video_count": 0,
            "created_at": "",
        }

    def _parse_channel_id_from_url(self, channel_url: str) -> str | None:
        """Parse channel ID from URL or archive.

        Handles both @username and /channel/ID formats.
        For @username URLs, resolves by checking existing video metadata.

        Args:
            channel_url: YouTube channel URL

        Returns:
            Channel ID or None if not found
        """
        # Try to extract from /channel/ format
        if "/channel/" in channel_url:
            channel_id = channel_url.split("/channel/")[-1].split("/")[0].split("?")[0]
            return channel_id

        # For @username format, need to resolve - check existing videos
        videos_dir = self.repo_path / "videos"
        if videos_dir.exists():
            for metadata_file in videos_dir.rglob("metadata.json"):
                try:
                    with open(metadata_file, encoding='utf-8') as f:
                        video_data = json.load(f)
                        channel_id = video_data.get("channel_id")
                        if channel_id:
                            return str(channel_id)
                except Exception:
                    continue

        return None

    def _get_channel_name_from_videos(self) -> str:
        """Get channel name from existing video metadata.

        Returns:
            Channel name or empty string if not found
        """
        videos_dir = self.repo_path / "videos"
        if videos_dir.exists():
            for metadata_file in videos_dir.rglob("metadata.json"):
                try:
                    with open(metadata_file, encoding='utf-8') as f:
                        video_data = json.load(f)
                        channel_name = video_data.get("channel_name")
                        if channel_name:
                            return str(channel_name)
                except Exception:
                    continue
        return ""

    def _download_channel_avatar(self, avatar_url: str) -> Path | None:
        """Download channel avatar and add to git-annex.

        Downloads avatar image, detects MIME type, saves with proper extension,
        and adds to git-annex for non-redistributable content tracking.

        Args:
            avatar_url: URL to channel avatar image

        Returns:
            Path to downloaded avatar file, or None if download failed
        """
        if not avatar_url:
            logger.debug("No avatar URL provided, skipping download")
            return None

        # Check if avatar already exists
        existing_avatars = list(self.repo_path.glob("channel_avatar.*"))
        if existing_avatars:
            logger.debug(f"Channel avatar already exists: {existing_avatars[0]}")
            return existing_avatars[0]

        try:
            # Download avatar
            logger.info(f"Downloading channel avatar from {avatar_url}")
            with urllib.request.urlopen(avatar_url, timeout=30) as response:
                avatar_data = response.read()

            # Detect MIME type using libmagic
            mime = magic.Magic(mime=True)
            mime_type = mime.from_buffer(avatar_data)
            logger.debug(f"Detected MIME type: {mime_type}")

            # Determine file extension from MIME type
            extension = self._mime_to_extension(mime_type)
            if not extension:
                logger.warning(f"Unknown MIME type: {mime_type}, using .bin")
                extension = "bin"

            # Save avatar
            avatar_path = self.repo_path / f"channel_avatar.{extension}"
            with open(avatar_path, 'wb') as f:
                f.write(avatar_data)

            logger.info(f"Saved channel avatar: {avatar_path} ({len(avatar_data)} bytes)")

            # Add to git-annex (like other binary content)
            from annextube.services.git_annex import GitAnnexService
            git_annex = GitAnnexService(self.repo_path)
            try:
                git_annex.add_and_commit(f"Add channel avatar ({extension})")
                logger.debug("Added channel avatar to git-annex")
            except Exception as e:
                logger.warning(f"Could not add avatar to git-annex: {e}")

            return avatar_path

        except urllib.error.URLError as e:
            logger.warning(f"Failed to download channel avatar: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading channel avatar: {e}", exc_info=True)
            return None

    def _mime_to_extension(self, mime_type: str) -> str | None:
        """Map MIME type to file extension.

        Args:
            mime_type: MIME type string (e.g., 'image/jpeg')

        Returns:
            File extension without dot (e.g., 'jpg'), or None if unknown
        """
        # Common image MIME types for channel avatars
        mime_map = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "image/svg+xml": "svg",
            "image/x-icon": "ico",
            "image/vnd.microsoft.icon": "ico",
        }

        return mime_map.get(mime_type.lower())
