"""Service for tracking and aggregating author information."""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..models.author import Author

logger = logging.getLogger(__name__)


class AuthorsService:
    """Service for generating authors.tsv from videos and comments."""

    def __init__(self, repo_path: Path):
        """Initialize AuthorsService.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path
        self.videos_dir = repo_path / "videos"

    def generate_authors_tsv(self) -> Path:
        """Generate authors.tsv aggregating all unique authors.

        Scans all video metadata and comments to build comprehensive
        author database with counts and timestamps.

        Returns:
            Path to generated authors.tsv file
        """
        logger.info("Generating authors.tsv")

        # Collect all authors
        authors = self._collect_authors()

        # Write TSV
        output_path = self.repo_path / "authors.tsv"
        self._write_tsv(authors, output_path)

        logger.info(f"Generated authors.tsv with {len(authors)} authors")
        return output_path

    def _collect_authors(self) -> Dict[str, Author]:
        """Collect all unique authors from videos and comments.

        Returns:
            Dictionary mapping author_id to Author objects
        """
        authors: Dict[str, Author] = {}

        if not self.videos_dir.exists():
            logger.warning(f"Videos directory not found: {self.videos_dir}")
            return authors

        # Scan all video directories
        for video_dir in sorted(self.videos_dir.iterdir()):
            if not video_dir.is_dir():
                continue

            # Process video metadata (uploader)
            metadata_path = video_dir / "metadata.json"
            if metadata_path.exists():
                self._process_video_metadata(metadata_path, authors)

            # Process comments
            comments_path = video_dir / "comments.json"
            if comments_path.exists():
                self._process_comments(comments_path, authors)

        return authors

    def _process_video_metadata(self, metadata_path: Path, authors: Dict[str, Author]) -> None:
        """Process video metadata to extract uploader information.

        Args:
            metadata_path: Path to metadata.json
            authors: Dictionary to update with author information
        """
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            channel_id = metadata.get('channel_id')
            channel_name = metadata.get('channel_name')
            published_at_str = metadata.get('published_at')

            if not channel_id:
                return

            published_at = None
            if published_at_str:
                try:
                    published_at = datetime.fromisoformat(published_at_str)
                except (ValueError, TypeError):
                    pass

            # Update or create author
            if channel_id not in authors:
                authors[channel_id] = Author(
                    author_id=channel_id,
                    name=channel_name or "Unknown",
                    channel_url=f"https://www.youtube.com/channel/{channel_id}",
                    first_seen=published_at,
                    last_seen=published_at,
                    video_count=1,
                    comment_count=0,
                )
            else:
                author = authors[channel_id]
                author.video_count += 1
                # Update name if we have a better one
                if channel_name and author.name == "Unknown":
                    author.name = channel_name
                # Update timestamps
                if published_at:
                    if not author.first_seen or published_at < author.first_seen:
                        author.first_seen = published_at
                    if not author.last_seen or published_at > author.last_seen:
                        author.last_seen = published_at

        except Exception as e:
            logger.warning(f"Failed to process video metadata {metadata_path}: {e}")

    def _process_comments(self, comments_path: Path, authors: Dict[str, Author]) -> None:
        """Process comments to extract commenter information.

        Args:
            comments_path: Path to comments.json
            authors: Dictionary to update with author information
        """
        try:
            with open(comments_path, 'r', encoding='utf-8') as f:
                comments = json.load(f)

            for comment in comments:
                author_id = comment.get('author_id')
                author_name = comment.get('author')
                timestamp = comment.get('timestamp')

                if not author_id:
                    continue

                comment_time = None
                if timestamp:
                    try:
                        comment_time = datetime.fromtimestamp(timestamp)
                    except (ValueError, TypeError, OSError):
                        pass

                # Update or create author
                if author_id not in authors:
                    channel_url = f"https://www.youtube.com/channel/{author_id}"
                    authors[author_id] = Author(
                        author_id=author_id,
                        name=author_name or "Unknown",
                        channel_url=channel_url,
                        first_seen=comment_time,
                        last_seen=comment_time,
                        video_count=0,
                        comment_count=1,
                    )
                else:
                    author = authors[author_id]
                    author.comment_count += 1
                    # Update name if we have a better one
                    if author_name and author.name == "Unknown":
                        author.name = author_name
                    # Update timestamps
                    if comment_time:
                        if not author.first_seen or comment_time < author.first_seen:
                            author.first_seen = comment_time
                        if not author.last_seen or comment_time > author.last_seen:
                            author.last_seen = comment_time

        except Exception as e:
            logger.warning(f"Failed to process comments {comments_path}: {e}")

    def _write_tsv(self, authors: Dict[str, Author], output_path: Path) -> None:
        """Write authors to TSV file.

        Args:
            authors: Dictionary of authors
            output_path: Path to output TSV file
        """
        # Sort authors by author_id for deterministic output
        sorted_authors = sorted(authors.values(), key=lambda a: a.author_id)

        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("author_id\tname\tchannel_url\tfirst_seen\tlast_seen\tvideo_count\tcomment_count\n")

            # Write data rows
            for author in sorted_authors:
                first_seen = author.first_seen.isoformat() if author.first_seen else ""
                last_seen = author.last_seen.isoformat() if author.last_seen else ""
                channel_url = author.channel_url or ""

                f.write(
                    f"{author.author_id}\t"
                    f"{author.name}\t"
                    f"{channel_url}\t"
                    f"{first_seen}\t"
                    f"{last_seen}\t"
                    f"{author.video_count}\t"
                    f"{author.comment_count}\n"
                )
