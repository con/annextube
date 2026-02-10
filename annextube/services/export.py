"""Export service for generating TSV metadata files."""

import json
from pathlib import Path

from annextube.lib.logging_config import get_logger

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

    def generate_videos_tsv(self, output_path: Path | None = None) -> Path:
        """Generate videos/videos.tsv with summary metadata for all videos.

        Scans videos/ directory and extracts key metadata from each
        video's metadata.json file.

        Args:
            output_path: Optional custom output path (default: repo_path/videos/videos.tsv)

        Returns:
            Path to generated TSV file
        """
        if output_path is None:
            output_path = self.repo_path / "videos" / "videos.tsv"

        logger.info(f"Generating videos.tsv at {output_path}")

        videos_dir = self.repo_path / "videos"
        if not videos_dir.exists():
            logger.warning("Videos directory does not exist, creating empty TSV")
            self._write_empty_videos_tsv(output_path)
            return output_path

        # Collect video metadata
        # Find all video directories by looking for metadata.json files
        # This supports both flat and hierarchical directory structures
        videos = []
        for metadata_path in sorted(videos_dir.rglob("metadata.json")):
            video_dir = metadata_path.parent

            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)

                # Extract key fields for TSV (frontend-compatible format)
                video_id = metadata.get("video_id", "")

                # Get relative path from videos/ directory (supports hierarchical layouts)
                relative_path = video_dir.relative_to(videos_dir)

                # Determine download status by checking git-annex state
                # video.mkv states:
                # 1. Missing: metadata_only (no video file)
                # 2. Symlink exists but target missing: metadata_only (broken link)
                # 3. Symlink target exists and small (<1MB): tracked (URL-only, can stream from YouTube)
                # 4. Symlink target exists and large (>1MB): downloaded (actual video content)
                video_file = video_dir / "video.mkv"
                if not video_file.exists():
                    download_status = "metadata_only"
                elif video_file.is_symlink():
                    try:
                        # Check if symlink target actually exists
                        target_path = video_file.resolve()
                        if not target_path.exists():
                            download_status = "metadata_only"
                        else:
                            # Check file size to distinguish URL-only vs actual content
                            # URL-only: typically < 1KB
                            # Video content: typically > 1MB
                            file_size = target_path.stat().st_size
                            if file_size > 1024 * 1024:  # > 1MB
                                download_status = "downloaded"
                            else:
                                download_status = "tracked"
                    except (OSError, RuntimeError):
                        # Broken symlink or error reading
                        download_status = "metadata_only"
                else:
                    # Regular file (not symlink) - definitely downloaded
                    download_status = "downloaded"

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
                logger.error(f"Failed to read metadata from {video_dir.relative_to(videos_dir)}: {e}")

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
        1. Extracts fresh channel metadata from YouTube (description, avatar, etc.)
        2. Calculates archive stats from TSV files and actual video files

        Returns:
            Path to generated channel.json
        """
        import csv
        from datetime import datetime

        from annextube.lib.config import load_config
        from annextube.services.youtube import YouTubeService

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

        # Extract fresh channel metadata from YouTube
        youtube = YouTubeService()
        channel_meta = youtube.get_channel_metadata(channel_source.url)

        # Fallback to parsing from URL and videos if extraction fails
        if not channel_meta or not channel_meta.get("channel_id"):
            logger.warning("Failed to extract channel metadata from YouTube, using fallback")
            url = channel_source.url
            custom_url = None
            channel_id = None
            channel_name = ""

            if "@" in url:
                custom_url = url.split("@")[-1].split("/")[0].split("?")[0]
            elif "/channel/" in url:
                channel_id = url.split("/channel/")[-1].split("/")[0].split("?")[0]

            # Try to get channel name from existing video
            videos_dir = self.repo_path / "videos"
            if videos_dir.exists():
                for metadata_file in videos_dir.rglob("metadata.json"):
                    try:
                        with open(metadata_file, encoding='utf-8') as f:
                            video_data = json.load(f)
                            channel_id = channel_id or video_data.get("channel_id", "")
                            channel_name = video_data.get("channel_name", "")
                            break
                    except Exception:
                        continue

            channel_meta = {
                "channel_id": channel_id or "",
                "channel_name": channel_name,
                "description": "",
                "custom_url": custom_url or "",
                "avatar_url": "",
                "subscriber_count": 0,
                "video_count": 0,
            }

        # Compute archive stats from videos.tsv and actual files
        videos_tsv = self.repo_path / "videos" / "videos.tsv"
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
            "avatar_url": channel_meta.get("avatar_url", ""),
            "banner_url": "",  # Not available from yt-dlp
            "country": "",  # Not available from yt-dlp
            "videos": [],
            "playlists": [],
            "playlist_count": playlist_count,
            "last_sync": now,
            "created_at": "",
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
        """Write videos to TSV file.

        Args:
            output_path: Path to output file
            videos: List of video dictionaries
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write header (frontend-compatible format)
            f.write("video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\t"
                    "duration\tview_count\tlike_count\tcomment_count\t"
                    "thumbnail_url\tdownload_status\tsource_url\tpath\n")

            # Write rows
            for video in videos:
                f.write(
                    f"{video['video_id']}\t"
                    f"{video['title']}\t"
                    f"{video['channel_id']}\t"
                    f"{video['channel_name']}\t"
                    f"{video['published_at']}\t"
                    f"{video['duration']}\t"
                    f"{video['view_count']}\t"
                    f"{video['like_count']}\t"
                    f"{video['comment_count']}\t"
                    f"{video['thumbnail_url']}\t"
                    f"{video['download_status']}\t"
                    f"{video['source_url']}\t"
                    f"{video['path']}\n"
                )

    def _write_playlists_tsv(self, output_path: Path, playlists: list[dict[str, str]]) -> None:
        """Write playlists to TSV file.

        Args:
            output_path: Path to output file
            playlists: List of playlist dictionaries
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write header (frontend-compatible format)
            f.write("playlist_id\ttitle\tchannel_id\tchannel_name\tvideo_count\t"
                    "total_duration\tprivacy_status\tcreated_at\tlast_sync\tpath\n")

            # Write rows
            for playlist in playlists:
                f.write(
                    f"{playlist['playlist_id']}\t"
                    f"{playlist['title']}\t"
                    f"{playlist['channel_id']}\t"
                    f"{playlist['channel_name']}\t"
                    f"{playlist['video_count']}\t"
                    f"{playlist['total_duration']}\t"
                    f"{playlist['privacy_status']}\t"
                    f"{playlist['created_at']}\t"
                    f"{playlist['last_sync']}\t"
                    f"{playlist['path']}\n"
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
