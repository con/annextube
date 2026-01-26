"""TSV reading utilities for deriving sync state from data files."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


class TSVReader:
    """Utilities for reading state from TSV files (single source of truth)."""

    @staticmethod
    def get_latest_video_datetime(videos_tsv_path: Path) -> Optional[datetime]:
        """Get the latest video publication datetime from videos.tsv.

        Args:
            videos_tsv_path: Path to videos.tsv file

        Returns:
            Latest published datetime, or None if file doesn't exist/is empty
        """
        if not videos_tsv_path.exists():
            logger.debug(f"videos.tsv not found at {videos_tsv_path}")
            return None

        try:
            with open(videos_tsv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                latest = None

                for row in reader:
                    published_str = row.get('published')
                    if not published_str:
                        continue

                    try:
                        # Try ISO 8601 datetime first
                        published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    except ValueError:
                        # Fall back to date-only format (backward compatibility)
                        try:
                            published = datetime.strptime(published_str, '%Y-%m-%d')
                        except ValueError:
                            logger.warning(f"Invalid published format: {published_str}")
                            continue

                    if latest is None or published > latest:
                        latest = published

                if latest:
                    logger.info(f"Latest video datetime from TSV: {latest.isoformat()}")
                return latest

        except Exception as e:
            logger.error(f"Failed to read videos.tsv: {e}")
            return None

    @staticmethod
    def get_latest_playlist_update(playlists_tsv_path: Path, playlist_id: str) -> Optional[datetime]:
        """Get the last_updated datetime for a specific playlist.

        Args:
            playlists_tsv_path: Path to playlists.tsv file
            playlist_id: YouTube playlist ID

        Returns:
            Last updated datetime, or None if not found
        """
        if not playlists_tsv_path.exists():
            return None

        try:
            with open(playlists_tsv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')

                for row in reader:
                    if row.get('playlist_id') == playlist_id:
                        last_updated_str = row.get('last_updated')
                        if last_updated_str:
                            try:
                                return datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                            except ValueError:
                                logger.warning(f"Invalid last_updated format: {last_updated_str}")
                        return None

                return None

        except Exception as e:
            logger.error(f"Failed to read playlists.tsv: {e}")
            return None

    @staticmethod
    def get_latest_comment_datetime(comments_json_path: Path) -> Optional[datetime]:
        """Get the latest comment timestamp from comments.json.

        Args:
            comments_json_path: Path to comments.json file

        Returns:
            Latest comment datetime, or None if file doesn't exist/is empty
        """
        if not comments_json_path.exists():
            return None

        try:
            with open(comments_json_path, 'r', encoding='utf-8') as f:
                comments = json.load(f)

            if not comments:
                return None

            latest = None
            for comment in comments:
                timestamp_str = comment.get('timestamp')
                if not timestamp_str:
                    continue

                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if latest is None or timestamp > latest:
                        latest = timestamp
                except ValueError:
                    continue

            return latest

        except Exception as e:
            logger.error(f"Failed to read comments.json: {e}")
            return None

    @staticmethod
    def get_video_count(videos_tsv_path: Path) -> int:
        """Count number of videos in videos.tsv.

        Args:
            videos_tsv_path: Path to videos.tsv file

        Returns:
            Number of videos (excluding header)
        """
        if not videos_tsv_path.exists():
            return 0

        try:
            with open(videos_tsv_path, 'r', encoding='utf-8') as f:
                # Skip header, count remaining lines
                return sum(1 for _ in f) - 1
        except Exception as e:
            logger.error(f"Failed to count videos in TSV: {e}")
            return 0
