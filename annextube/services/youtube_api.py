#!/usr/bin/env python3
"""YouTube Data API Services.

This module provides direct access to YouTube's Data API v3 for:
1. Fetching comments with proper reply threading (alternative to yt-dlp)
2. Extracting enhanced video metadata not available through yt-dlp:
   - Accurate license information (youtube vs creativeCommon)
   - Licensed content status
   - Recording location and date
   - Technical details (HD/SD, 2D/3D, projection type)
   - Geographic restrictions and content ratings

Requires YouTube Data API v3 key from:
https://console.cloud.google.com/apis/credentials
"""

import os
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from annextube.lib.logging_config import get_logger
from annextube.lib.quota_manager import QuotaManager

logger = get_logger(__name__)

class YouTubeAPICommentsService:
    """Fetch comments using YouTube Data API v3 (supports replies)."""

    def __init__(self, api_key: str | None = None, quota_manager: QuotaManager | None = None):
        """
        Initialize YouTube API client.

        Args:
            api_key: YouTube Data API v3 key. If not provided, reads from YOUTUBE_API_KEY env var.
            quota_manager: QuotaManager instance for handling quota exceeded errors (default: enabled with 48h max wait)
        """
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key required. Set YOUTUBE_API_KEY environment variable.")

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.quota_manager = quota_manager or QuotaManager()

    def fetch_comments(
        self,
        video_id: str,
        max_comments: int | None = None,
        max_replies_per_thread: int = 100,
        existing_comment_ids: set[str] | None = None
    ) -> list[dict]:
        """
        Fetch comments with replies for a video.

        Supports incremental fetching with early stopping: when existing_comment_ids
        is provided, pagination stops as soon as we encounter a comment we already
        have. This is very efficient for incremental updates since comments are
        ordered by time (newest first).

        Args:
            video_id: YouTube video ID
            max_comments: Maximum number of top-level comments to fetch (None = all)
            max_replies_per_thread: Maximum replies to fetch per comment thread
            existing_comment_ids: Set of comment IDs we already have (for early stopping)

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
        all_comments: list[dict] = []
        next_page_token = None
        fetched_threads = 0
        existing_ids = existing_comment_ids or set()
        stopped_early = False

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

                    # EARLY STOPPING: Hit a comment we already have
                    if top_comment_id in existing_ids:
                        logger.info(
                            f"Early stopping: encountered existing comment {top_comment_id} "
                            f"after fetching {len(all_comments)} new comments"
                        )
                        stopped_early = True
                        break

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
                            reply_id = reply['id']

                            # Skip reply if we already have it
                            if reply_id in existing_ids:
                                continue

                            all_comments.append({
                                'comment_id': reply_id,
                                'author': reply_snippet.get('authorDisplayName', ''),
                                'author_id': reply_snippet.get('authorChannelId', {}).get('value', ''),
                                'text': reply_snippet.get('textDisplay', ''),
                                'timestamp': self._parse_timestamp(reply_snippet.get('publishedAt')),
                                'like_count': reply_snippet.get('likeCount', 0),
                                'is_favorited': False,
                                'parent': reply_snippet.get('parentId', top_comment_id)
                            })

                # Break if we hit existing comment (early stopping)
                if stopped_early:
                    break

                fetched_threads += len(response.get('items', []))

                # Check if we should continue
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break  # No more pages
                if max_comments and fetched_threads >= max_comments:
                    break  # Reached limit

                # Rate limiting - be nice to the API
                time.sleep(0.1)

            if stopped_early:
                logger.info(f"Incremental fetch complete: {len(all_comments)} new comments")
            return all_comments

        except HttpError as e:
            if e.resp.status == 403:
                # Comments disabled or quota exceeded
                if 'commentsDisabled' in str(e):
                    return []  # Video has comments disabled
                elif 'quotaExceeded' in str(e):
                    # Handle quota exceeded - wait until midnight PT or raise error
                    self.quota_manager.handle_quota_exceeded(str(e))
                    # If we get here, quota has reset - retry the operation
                    return self.fetch_comments(video_id, max_comments, max_replies_per_thread, existing_comment_ids)
                raise  # Other 403 error (permissions, etc.)
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
        except Exception:
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


class YouTubeAPIMetadataClient:
    """Client for YouTube Data API v3 enhanced video metadata extraction."""

    # API parts to request (total quota cost: 10 units per video)
    # - snippet: 2 units (title, description, tags, etc.)
    # - status: 2 units (license, embeddable, madeForKids)
    # - contentDetails: 2 units (licensedContent, definition, restrictions)
    # - statistics: 2 units (views, likes, comments)
    # - recordingDetails: 2 units (location, recording date)
    DEFAULT_PARTS = [
        "snippet",
        "status",
        "contentDetails",
        "statistics",
        "recordingDetails",
    ]

    def __init__(self, api_key: str | None = None, quota_manager: QuotaManager | None = None):
        """Initialize YouTube API metadata client.

        Args:
            api_key: YouTube Data API v3 key. If not provided, reads from YOUTUBE_API_KEY env var.
            quota_manager: QuotaManager instance for handling quota exceeded errors (default: enabled with 48h max wait)

        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key required. Set YOUTUBE_API_KEY environment variable.")

        self.youtube = build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)
        self.quota_manager = quota_manager or QuotaManager()
        logger.info("YouTube API metadata client initialized (quota cost: 10 units/video)")

    def get_video_details(
        self,
        video_ids: list[str] | str,
        parts: list[str] | None = None,
    ) -> dict[str, dict]:
        """Fetch detailed metadata for one or more videos.

        Args:
            video_ids: Single video ID or list of video IDs (max 50 per request)
            parts: List of API parts to fetch (default: all useful parts)

        Returns:
            Dictionary mapping video_id -> API response data
            Returns empty dict if API call fails

        Raises:
            ValueError: If more than 50 video IDs provided
        """
        # Normalize to list
        if isinstance(video_ids, str):
            video_ids = [video_ids]

        if not video_ids:
            logger.warning("get_video_details called with empty video_ids list")
            return {}

        if len(video_ids) > 50:
            raise ValueError(f"Maximum 50 video IDs per request, got {len(video_ids)}")

        # Use default parts if not specified
        parts = parts or self.DEFAULT_PARTS

        try:
            # Build request
            request = self.youtube.videos().list(
                part=",".join(parts),
                id=",".join(video_ids),
                maxResults=50,
            )

            # Execute request
            logger.info(
                f"Fetching YouTube API metadata for {len(video_ids)} video(s) "
                f"(parts: {', '.join(parts)})"
            )
            response = request.execute()

            # Parse response into dict
            result = {}
            for item in response.get("items", []):
                video_id = item["id"]
                result[video_id] = item
                logger.debug(f"Fetched API metadata for video {video_id}")

            # Check for missing videos
            fetched_ids = set(result.keys())
            requested_ids = set(video_ids)
            missing_ids = requested_ids - fetched_ids

            if missing_ids:
                logger.warning(
                    f"YouTube API did not return metadata for {len(missing_ids)} "
                    f"video(s): {', '.join(sorted(missing_ids)[:5])}..."
                )

            logger.info(f"Successfully fetched API metadata for {len(result)} video(s)")
            return result

        except HttpError as e:
            # Check if this is a quota exceeded error
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                # Handle quota exceeded - wait until midnight PT or raise error
                self.quota_manager.handle_quota_exceeded(str(e))
                # If we get here, quota has reset - retry the operation
                return self.get_video_details(video_ids, parts)

            logger.error(
                f"YouTube API HTTP error: {e.resp.status} - {e.content.decode()}",
                exc_info=True,
            )
            return {}

        except Exception as e:
            logger.error(f"Failed to fetch YouTube API metadata: {e}", exc_info=True)
            return {}

    def get_video_statistics(
        self,
        video_ids: list[str] | str,
    ) -> dict[str, dict[str, int]]:
        """Fetch only statistics for one or more videos (efficient for incremental updates).

        This method fetches only the statistics part (2 quota units per request),
        making it very efficient for checking if social data has changed.

        Args:
            video_ids: Single video ID or list of video IDs (max 50 per request)

        Returns:
            Dictionary mapping video_id -> statistics dict with keys:
            - viewCount: int
            - likeCount: int
            - commentCount: int
            Returns empty dict if API call fails

        Example:
            >>> client.get_video_statistics(["video1", "video2"])
            {
                "video1": {"viewCount": 1000, "likeCount": 50, "commentCount": 10},
                "video2": {"viewCount": 2000, "likeCount": 100, "commentCount": 20}
            }
        """
        # Fetch only statistics part (2 quota units total for up to 50 videos)
        api_data = self.get_video_details(video_ids, parts=["statistics"])

        # Extract statistics from response
        result = {}
        for video_id, data in api_data.items():
            if "statistics" in data:
                stats = data["statistics"]
                result[video_id] = {
                    "viewCount": int(stats.get("viewCount", 0)),
                    "likeCount": int(stats.get("likeCount", 0)),
                    "commentCount": int(stats.get("commentCount", 0)),
                }
                logger.debug(
                    f"Statistics for {video_id}: "
                    f"views={result[video_id]['viewCount']}, "
                    f"likes={result[video_id]['likeCount']}, "
                    f"comments={result[video_id]['commentCount']}"
                )

        return result

    def extract_enhanced_metadata(self, api_data: dict) -> dict:
        """Extract enhanced metadata fields from API response.

        Args:
            api_data: Raw YouTube API response for a single video

        Returns:
            Dictionary with extracted metadata fields for Video model
        """
        result = {}

        # Extract status fields (license, embeddable, madeForKids)
        if "status" in api_data:
            status = api_data["status"]
            result["license"] = status.get("license", "youtube")
            result["embeddable"] = status.get("embeddable")
            result["made_for_kids"] = status.get("madeForKids")
            logger.debug(f"Status: license={result['license']}, embeddable={result['embeddable']}")

        # Extract contentDetails (licensedContent, definition, dimension, etc.)
        if "contentDetails" in api_data:
            content = api_data["contentDetails"]

            result["licensed_content"] = content.get("licensedContent")
            result["definition"] = content.get("definition")
            result["dimension"] = content.get("dimension")
            result["projection"] = content.get("projection")

            # Region restrictions
            if "regionRestriction" in content:
                result["region_restriction"] = {
                    "allowed": content["regionRestriction"].get("allowed", []),
                    "blocked": content["regionRestriction"].get("blocked", []),
                }

            # Content rating (age restrictions)
            if "contentRating" in content:
                result["content_rating"] = content["contentRating"]

            logger.debug(
                f"ContentDetails: def={result.get('definition')}, "
                f"dim={result.get('dimension')}, "
                f"licensed={result.get('licensed_content')}"
            )

        # Extract recordingDetails (location, recording date)
        if "recordingDetails" in api_data:
            recording = api_data["recordingDetails"]

            if "recordingDate" in recording:
                result["recording_date"] = recording["recordingDate"]

            if "location" in recording:
                loc = recording["location"]
                result["recording_location"] = {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                    "altitude": loc.get("altitude"),
                }

            if "locationDescription" in recording:
                result["location_description"] = recording["locationDescription"]

            if result.get("recording_location") or result.get("recording_date"):
                logger.debug(
                    f"Recording: date={result.get('recording_date')}, "
                    f"location={result.get('location_description')}"
                )

        # Extract topicDetails (Wikipedia categories)
        if "topicDetails" in api_data:
            topics = api_data["topicDetails"]
            result["topic_categories"] = topics.get("topicCategories", [])

        return result

    def enhance_video_metadata(
        self,
        video_ids: list[str] | str,
    ) -> dict[str, dict]:
        """Fetch and extract enhanced metadata for videos.

        This is a convenience method that combines get_video_details() and
        extract_enhanced_metadata() to return ready-to-use metadata.

        Args:
            video_ids: Single video ID or list of video IDs

        Returns:
            Dictionary mapping video_id -> extracted metadata fields
        """
        api_data = self.get_video_details(video_ids)

        result = {}
        for video_id, data in api_data.items():
            result[video_id] = self.extract_enhanced_metadata(data)

        return result

    def get_channel_details(self, channel_id: str) -> dict | None:
        """Fetch channel metadata from YouTube API.

        Args:
            channel_id: YouTube channel ID (e.g., "UCxxxxxx")

        Returns:
            Dictionary with channel metadata:
            {
                'channel_id': str,
                'channel_name': str,
                'description': str,
                'custom_url': str,
                'avatar_url': str,
                'banner_url': str,
                'country': str,
                'subscriber_count': int,
                'video_count': int,
                'created_at': str (ISO format),
            }
            Returns None if API call fails or channel not found.

        Quota cost: 3 units (snippet + statistics + brandingSettings)
        """
        try:
            # Request channel details
            request = self.youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                id=channel_id,
                maxResults=1,
            )

            logger.info(f"Fetching channel metadata from YouTube API for {channel_id}")
            response = request.execute()

            items = response.get("items", [])
            if not items:
                logger.warning(f"Channel not found: {channel_id}")
                return None

            item = items[0]
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            branding = item.get("brandingSettings", {}).get("image", {})

            # Extract avatar URL (use highest resolution)
            thumbnails = snippet.get("thumbnails", {})
            avatar_url = ""
            if "high" in thumbnails:
                avatar_url = thumbnails["high"]["url"]
            elif "medium" in thumbnails:
                avatar_url = thumbnails["medium"]["url"]
            elif "default" in thumbnails:
                avatar_url = thumbnails["default"]["url"]

            # Extract banner URL
            banner_url = branding.get("bannerExternalUrl", "")

            metadata = {
                "channel_id": item["id"],
                "channel_name": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "custom_url": snippet.get("customUrl", ""),
                "avatar_url": avatar_url,
                "banner_url": banner_url,
                "country": snippet.get("country", ""),
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
                "video_count": int(statistics.get("videoCount", 0)),
                "created_at": snippet.get("publishedAt", ""),
            }

            logger.info(
                f"Fetched channel metadata: {metadata['channel_name']} "
                f"({metadata['subscriber_count']} subscribers, {metadata['video_count']} videos)"
            )
            return metadata

        except HttpError as e:
            # Check if this is a quota exceeded error
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                self.quota_manager.handle_quota_exceeded(str(e))
                # If we get here, quota has reset - retry the operation
                return self.get_channel_details(channel_id)

            logger.error(
                f"YouTube API HTTP error: {e.resp.status} - {e.content.decode()}",
                exc_info=True,
            )
            return None

        except Exception as e:
            logger.error(f"Failed to fetch channel metadata from YouTube API: {e}", exc_info=True)
            return None


def create_api_client(api_key: str | None) -> YouTubeAPIMetadataClient | None:
    """Create YouTube API metadata client if API key is provided.

    Args:
        api_key: YouTube Data API v3 key (optional)

    Returns:
        YouTubeAPIMetadataClient instance if key provided, None otherwise
    """
    if not api_key or not api_key.strip():
        logger.info("No YouTube API key provided - API-enhanced metadata disabled")
        return None

    try:
        client = YouTubeAPIMetadataClient(api_key)
        logger.info("YouTube API metadata client created successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create YouTube API metadata client: {e}")
        return None


class QuotaEstimator:
    """Estimate and track YouTube Data API v3 quota usage.

    YouTube API Quota Costs:
    - videos.list (with 5 parts): 10 units per video
    - commentThreads.list: 1 unit per 100 comments
    - Free tier: 10,000 units/day
    - Paid tier: Additional quota available for purchase
    """

    # Quota costs per operation
    COST_PER_VIDEO_METADATA = 10  # snippet + status + contentDetails + statistics + recordingDetails
    COST_PER_100_COMMENTS = 1

    # Daily quotas
    FREE_TIER_DAILY_QUOTA = 10_000

    @classmethod
    def estimate_video_metadata_cost(cls, num_videos: int) -> int:
        """Estimate quota cost for fetching video metadata.

        Args:
            num_videos: Number of videos to fetch metadata for

        Returns:
            Estimated quota units required
        """
        return num_videos * cls.COST_PER_VIDEO_METADATA

    @classmethod
    def estimate_comments_cost(cls, num_comment_threads: int) -> int:
        """Estimate quota cost for fetching comments.

        Args:
            num_comment_threads: Number of top-level comment threads

        Returns:
            Estimated quota units required
        """
        # 1 unit per 100 comment threads
        return (num_comment_threads + 99) // 100

    @classmethod
    def format_cost_report(
        cls,
        num_videos: int,
        num_comments: int = 0,
        include_pricing: bool = True,
    ) -> str:
        """Generate formatted cost estimation report.

        Args:
            num_videos: Number of videos
            num_comments: Number of comment threads (optional)
            include_pricing: Whether to include pricing information

        Returns:
            Formatted multi-line report string
        """
        video_cost = cls.estimate_video_metadata_cost(num_videos)
        comment_cost = cls.estimate_comments_cost(num_comments) if num_comments > 0 else 0
        total_cost = video_cost + comment_cost

        # Calculate how many days needed at free tier
        days_needed = (total_cost + cls.FREE_TIER_DAILY_QUOTA - 1) // cls.FREE_TIER_DAILY_QUOTA

        # Calculate overage if exceeds free tier
        if total_cost > cls.FREE_TIER_DAILY_QUOTA:
            overage = total_cost - cls.FREE_TIER_DAILY_QUOTA
            overage_cost_usd = (overage / 100) * 0.10  # $0.10 per 100 quota units
        else:
            overage = 0
            overage_cost_usd = 0.0

        report_lines = [
            "YouTube API Quota Estimation",
            "=" * 50,
            f"Videos:           {num_videos:,} × 10 units = {video_cost:,} units",
        ]

        if num_comments > 0:
            report_lines.append(
                f"Comment threads:  {num_comments:,} ÷ 100 = {comment_cost:,} units"
            )
            report_lines.append(f"{'':17} {'-' * 30}")
            report_lines.append(f"Total:            {total_cost:,} units")
        else:
            report_lines.append(f"{'':17} {'-' * 30}")
            report_lines.append(f"Total:            {total_cost:,} units")

        report_lines.extend([
            "",
            "Free Tier Analysis",
            "-" * 50,
            f"Daily free quota: {cls.FREE_TIER_DAILY_QUOTA:,} units/day",
        ])

        if total_cost <= cls.FREE_TIER_DAILY_QUOTA:
            report_lines.append(f"[ok] Fits within free tier ({total_cost / cls.FREE_TIER_DAILY_QUOTA * 100:.1f}% of daily quota)")
        else:
            report_lines.extend([
                f"[!] Exceeds free tier by {overage:,} units",
                f"  Requires {days_needed} day(s) at free tier rate",
            ])

        if include_pricing and overage > 0:
            report_lines.extend([
                "",
                "Paid Quota Pricing (if purchased)",
                "-" * 50,
                f"Overage units:    {overage:,} units",
                "Cost per 100:     $0.10 USD",
                f"Estimated cost:   ${overage_cost_usd:.2f} USD",
                "",
                "Note: Additional quota must be requested from Google Cloud Console.",
                "See: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas",
            ])

        return "\n".join(report_lines)

    @classmethod
    def can_fit_in_free_tier(cls, num_videos: int, num_comments: int = 0) -> bool:
        """Check if operation fits within daily free tier.

        Args:
            num_videos: Number of videos
            num_comments: Number of comment threads

        Returns:
            True if operation fits in free tier, False otherwise
        """
        total_cost = (
            cls.estimate_video_metadata_cost(num_videos) +
            cls.estimate_comments_cost(num_comments)
        )
        return total_cost <= cls.FREE_TIER_DAILY_QUOTA
