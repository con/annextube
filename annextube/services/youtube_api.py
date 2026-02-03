#!/usr/bin/env python3
"""
YouTube Data API Comments Service

Alternative to yt-dlp for fetching comments with proper reply threading.
Requires YouTube Data API v3 key.
"""

import os
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)

class YouTubeAPICommentsService:
    """Fetch comments using YouTube Data API v3 (supports replies)."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API v3 key. If not provided, reads from YOUTUBE_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key required. Set YOUTUBE_API_KEY environment variable.")

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def fetch_comments(
        self,
        video_id: str,
        max_comments: int | None = None,
        max_replies_per_thread: int = 100
    ) -> list[dict]:
        """
        Fetch comments with replies for a video.
        
        Args:
            video_id: YouTube video ID
            max_comments: Maximum number of top-level comments to fetch (None = all)
            max_replies_per_thread: Maximum replies to fetch per comment thread
        
        Returns:
            List of comment dictionaries in annextube format:
            {
                'comment_id': str,
                'author': str,
                'author_id': str,
                'text': str,
                'timestamp': int,  # Unix timestamp
                'like_count': int,
                'is_favorited': bool,
                'parent': str  # 'root' or parent comment ID
            }
        
        Raises:
            HttpError: If API request fails
        """
        all_comments = []
        next_page_token = None
        fetched_threads = 0

        try:
            while True:
                # Fetch comment threads (top-level comments + their replies)
                request = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=min(100, max_comments - fetched_threads) if max_comments else 100,
                    pageToken=next_page_token,
                    textFormat='plainText',
                    order='time'  # Newest first
                )

                response = request.execute()

                for item in response.get('items', []):
                    # Extract top-level comment
                    top_snippet = item['snippet']['topLevelComment']['snippet']
                    top_comment_id = item['snippet']['topLevelComment']['id']

                    # Add top-level comment
                    all_comments.append({
                        'comment_id': top_comment_id,
                        'author': top_snippet.get('authorDisplayName', ''),
                        'author_id': top_snippet.get('authorChannelId', {}).get('value', ''),
                        'text': top_snippet.get('textDisplay', ''),
                        'timestamp': self._parse_timestamp(top_snippet.get('publishedAt')),
                        'like_count': top_snippet.get('likeCount', 0),
                        'is_favorited': False,  # API doesn't provide this
                        'parent': 'root'
                    })

                    # Extract replies if present
                    if 'replies' in item:
                        replies = item['replies']['comments']
                        # Limit replies per thread
                        for reply in replies[:max_replies_per_thread]:
                            reply_snippet = reply['snippet']
                            all_comments.append({
                                'comment_id': reply['id'],
                                'author': reply_snippet.get('authorDisplayName', ''),
                                'author_id': reply_snippet.get('authorChannelId', {}).get('value', ''),
                                'text': reply_snippet.get('textDisplay', ''),
                                'timestamp': self._parse_timestamp(reply_snippet.get('publishedAt')),
                                'like_count': reply_snippet.get('likeCount', 0),
                                'is_favorited': False,
                                'parent': reply_snippet.get('parentId', top_comment_id)
                            })

                fetched_threads += len(response.get('items', []))

                # Check if we should continue
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break  # No more pages
                if max_comments and fetched_threads >= max_comments:
                    break  # Reached limit

                # Rate limiting - be nice to the API
                time.sleep(0.1)

            return all_comments

        except HttpError as e:
            if e.resp.status == 403:
                # Comments disabled or quota exceeded
                if 'commentsDisabled' in str(e):
                    return []  # Video has comments disabled
                raise  # Other 403 error (quota, permissions)
            elif e.resp.status == 404:
                # Video not found
                return []
            raise

    def _parse_timestamp(self, iso_timestamp: str) -> int:
        """Convert ISO 8601 timestamp to Unix timestamp."""
        from datetime import datetime
        if not iso_timestamp:
            return 0
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except:
            return 0

    def get_quota_cost(self, num_threads: int) -> int:
        """
        Estimate API quota cost for fetching comments.
        
        YouTube Data API v3 quota costs:
        - commentThreads.list: 1 unit per request
        - Each request returns up to 100 comment threads
        
        Args:
            num_threads: Number of comment threads to fetch
        
        Returns:
            Estimated quota units
        """
        # 1 unit per request, 100 threads per request
        requests_needed = (num_threads + 99) // 100
        return requests_needed
