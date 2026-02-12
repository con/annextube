"""YouTube API quota management with automatic retry until midnight Pacific Time.

Handles quota exceeded errors by calculating when quota will reset and
sleeping until that time, with periodic progress updates and cancellation support.
"""

import time
from collections.abc import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


class QuotaExceededError(Exception):
    """Raised when YouTube API quota is exceeded and cannot be retried."""
    pass


class QuotaManager:
    """Manages YouTube API quota limits and automatic retry logic."""

    def __init__(
        self,
        max_wait_hours: int = 48,
        check_interval_seconds: int = 1800,
        enabled: bool = True
    ):
        """Initialize quota manager.

        Args:
            max_wait_hours: Maximum hours to wait before giving up (default: 48)
            check_interval_seconds: Seconds between quota checks (default: 1800 = 30min)
            enabled: Enable automatic waiting (default: True)
        """
        self.max_wait_hours = max_wait_hours
        self.check_interval_seconds = check_interval_seconds
        self.enabled = enabled

    def calculate_next_quota_reset(self, now: datetime | None = None) -> datetime:
        """Calculate next midnight Pacific Time when quota resets.

        YouTube API quotas reset at midnight Pacific Time, which can be either:
        - PST (UTC-8): November - March (Standard Time)
        - PDT (UTC-7): March - November (Daylight Saving Time)

        The zoneinfo library handles DST transitions automatically.

        Args:
            now: Current time (default: datetime.now(timezone.utc))

        Returns:
            Datetime of next midnight Pacific Time (timezone-aware)

        Examples:
            >>> # If now is 2026-02-07 14:30 PST (22:30 UTC)
            >>> next_reset = calculate_next_quota_reset()
            >>> # Returns: 2026-02-08 00:00 PST (08:00 UTC)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Convert to Pacific Time
        pacific = ZoneInfo("America/Los_Angeles")
        now_pt = now.astimezone(pacific)

        # Calculate next midnight PT
        # If it's already past midnight, get tomorrow's midnight
        next_midnight_pt = now_pt.replace(hour=0, minute=0, second=0, microsecond=0)

        # If we're already past midnight, add a day
        if next_midnight_pt <= now_pt:
            from datetime import timedelta
            next_midnight_pt = next_midnight_pt + timedelta(days=1)

        # Return as UTC for consistency
        return next_midnight_pt.astimezone(timezone.utc)

    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string like "5h 23m" or "45m" or "23h 15m"

        Examples:
            >>> format_duration(3600)
            '1h 0m'
            >>> format_duration(5430)
            '1h 30m'
            >>> format_duration(90)
            '1m'
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def sleep_with_progress(
        self,
        wait_seconds: float,
        check_interval: int | None = None,
        check_callback: Callable[[], bool] | None = None
    ) -> None:
        """Sleep with periodic progress updates and early exit support.

        Args:
            wait_seconds: Total seconds to sleep
            check_interval: Seconds between progress logs (default: self.check_interval_seconds)
            check_callback: Optional callback to test if quota is available early.
                           Should return True if quota is available, False otherwise.

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C during sleep

        Example:
            >>> def test_quota():
            ...     # Try a lightweight API call
            ...     try:
            ...         api.videos().list(part='id', id='test').execute()
            ...         return True
            ...     except HttpError:
            ...         return False
            >>> manager.sleep_with_progress(3600, check_callback=test_quota)
        """
        if check_interval is None:
            check_interval = self.check_interval_seconds

        start_time = time.time()
        end_time = start_time + wait_seconds

        logger.info(
            f"Sleeping until quota reset ({self.format_duration(wait_seconds)} from now). "
            "Press Ctrl+C to cancel."
        )

        try:
            while time.time() < end_time:
                remaining = end_time - time.time()

                if remaining <= 0:
                    break

                # Sleep for check_interval or remaining time, whichever is shorter
                sleep_time = min(check_interval, remaining)
                time.sleep(sleep_time)

                # Log progress
                remaining = end_time - time.time()
                if remaining > 0:
                    logger.info(f"Quota resets in {self.format_duration(remaining)}")

                    # Test if quota is available early (manual increase, etc.)
                    if check_callback:
                        try:
                            if check_callback():
                                logger.info("Quota appears to be available! Resuming operations.")
                                return
                        except Exception as e:
                            logger.debug(f"Quota check failed (will retry): {e}")

            logger.info("Quota reset time reached. Resuming operations.")

        except KeyboardInterrupt:
            logger.warning("Sleep interrupted by user (Ctrl+C)")
            raise

    def handle_quota_exceeded(
        self,
        error_message: str,
        check_callback: Callable[[], bool] | None = None
    ) -> None:
        """Handle quota exceeded error by waiting until midnight Pacific Time.

        Args:
            error_message: Error message from YouTube API (for logging)
            check_callback: Optional callback to test quota availability

        Raises:
            QuotaExceededError: If waiting is disabled or wait time exceeds max
            KeyboardInterrupt: If user cancels during wait

        Example:
            >>> try:
            ...     response = api_call()
            ... except HttpError as e:
            ...     if e.resp.status == 403 and 'quotaExceeded' in str(e):
            ...         quota_manager.handle_quota_exceeded(str(e))
            ...         # Retries operation after quota resets
        """
        if not self.enabled:
            raise QuotaExceededError(
                f"YouTube API quota exceeded: {error_message}\n"
                "Quota resets at midnight Pacific Time. "
                "Set [api] quota_auto_wait = true in config to enable automatic retry."
            )

        # Calculate wait time
        now = datetime.now(timezone.utc)
        next_reset = self.calculate_next_quota_reset(now)
        wait_seconds = (next_reset - now).total_seconds()
        wait_hours = wait_seconds / 3600

        logger.warning(f"YouTube API quota exceeded: {error_message}")
        logger.warning(f"Quota resets at: {next_reset.astimezone(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # Check if wait time is reasonable
        if wait_hours > self.max_wait_hours:
            raise QuotaExceededError(
                f"Quota exceeded. Reset time is {wait_hours:.1f} hours away "
                f"(max configured: {self.max_wait_hours} hours). "
                "Aborting to avoid excessive wait."
            )

        # Wait until quota resets
        self.sleep_with_progress(wait_seconds, check_callback=check_callback)
