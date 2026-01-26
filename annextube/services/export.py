"""Export service for generating TSV metadata files."""

import json
from pathlib import Path
from typing import List, Dict, Any

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

    def generate_videos_tsv(self, output_path: Path = None) -> Path:
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
        videos = []
        for video_dir in sorted(videos_dir.iterdir()):
            if not video_dir.is_dir():
                continue

            metadata_path = video_dir / "metadata.json"
            if not metadata_path.exists():
                logger.warning(f"No metadata.json in {video_dir.name}, skipping")
                continue

            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                # Count available captions
                captions_available = metadata.get("captions_available", [])
                caption_count = len(captions_available) if isinstance(captions_available, list) else 0

                # Extract key fields for TSV (title-first column order)
                video_entry = {
                    "title": metadata.get("title", ""),
                    "channel": metadata.get("channel_name", ""),
                    "published": metadata.get("published_at", ""),  # Full ISO 8601 datetime
                    "duration": str(metadata.get("duration", 0)),
                    "views": str(metadata.get("view_count", 0)),
                    "likes": str(metadata.get("like_count", 0)),
                    "comments": str(metadata.get("comment_count", 0)),
                    "captions": str(caption_count),  # Count, not boolean
                    "path": video_dir.name,  # Relative to videos/ directory
                    "video_id": metadata.get("video_id", ""),
                }
                videos.append(video_entry)

            except Exception as e:
                logger.error(f"Failed to read metadata from {video_dir.name}: {e}")

        # Write TSV file
        self._write_videos_tsv(output_path, videos)
        logger.info(f"Generated videos.tsv with {len(videos)} entries")

        return output_path

    def generate_playlists_tsv(self, output_path: Path = None) -> Path:
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
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                # Count symlinks (videos in playlist)
                video_count = sum(1 for item in playlist_dir.iterdir()
                                  if item.is_symlink() and item.name != "playlist.json")

                # Calculate total duration from symlinked videos
                total_duration = self._calculate_playlist_duration(playlist_dir)

                # Extract key fields for TSV (title-first column order)
                playlist_entry = {
                    "title": metadata.get("title", ""),
                    "channel": metadata.get("channel_name", ""),
                    "video_count": str(video_count),
                    "total_duration": str(total_duration),
                    "last_updated": metadata.get("last_modified") or metadata.get("updated_at") or "",  # Full ISO 8601 datetime
                    "path": playlist_dir.name,  # Relative folder name
                    "playlist_id": metadata.get("playlist_id", ""),
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
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        total += metadata.get("duration", 0)
            except Exception as e:
                logger.debug(f"Could not read duration from {symlink.name}: {e}")

        return total

    def _write_videos_tsv(self, output_path: Path, videos: List[Dict[str, str]]) -> None:
        """Write videos to TSV file.

        Args:
            output_path: Path to output file
            videos: List of video dictionaries
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write header (title-first column order, path and video_id last)
            f.write("title\tchannel\tpublished\tduration\tviews\tlikes\tcomments\tcaptions\tpath\tvideo_id\n")

            # Write rows
            for video in videos:
                f.write(
                    f"{video['title']}\t"
                    f"{video['channel']}\t"
                    f"{video['published']}\t"
                    f"{video['duration']}\t"
                    f"{video['views']}\t"
                    f"{video['likes']}\t"
                    f"{video['comments']}\t"
                    f"{video['captions']}\t"
                    f"{video['path']}\t"
                    f"{video['video_id']}\n"
                )

    def _write_playlists_tsv(self, output_path: Path, playlists: List[Dict[str, str]]) -> None:
        """Write playlists to TSV file.

        Args:
            output_path: Path to output file
            playlists: List of playlist dictionaries
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write header (title-first column order, path and playlist_id last)
            f.write("title\tchannel\tvideo_count\ttotal_duration\tlast_updated\tpath\tplaylist_id\n")

            # Write rows
            for playlist in playlists:
                f.write(
                    f"{playlist['title']}\t"
                    f"{playlist['channel']}\t"
                    f"{playlist['video_count']}\t"
                    f"{playlist['total_duration']}\t"
                    f"{playlist['last_updated']}\t"
                    f"{playlist['path']}\t"
                    f"{playlist['playlist_id']}\n"
                )

    def _write_empty_videos_tsv(self, output_path: Path) -> None:
        """Write empty videos.tsv with header only.

        Args:
            output_path: Path to output file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("video_id\ttitle\tchannel\tpublished\tduration\tviews\tlikes\tcomments\thas_captions\tfile_path\n")

    def _write_empty_playlists_tsv(self, output_path: Path) -> None:
        """Write empty playlists.tsv with header only.

        Args:
            output_path: Path to output file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("folder_name\tplaylist_id\ttitle\tchannel\tvideo_count\ttotal_duration\tlast_updated\n")
