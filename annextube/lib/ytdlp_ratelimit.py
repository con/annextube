"""yt-dlp rate-limit detection and retry logic.

Detects YouTube session bans ("Sign in to confirm you're not a bot") and
HTTP 429 rate limits, then waits with progress reporting before retrying.
Reuses QuotaManager.sleep_with_progress() for long waits.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import Any, TypeVar

from annextube.lib.logging_config import get_logger
from annextube.lib.quota_manager import QuotaManager

logger = get_logger(__name__)

T = TypeVar("T")

# Patterns that indicate a YouTube rate-limit / session ban
_RATE_LIMIT_PATTERNS = re.compile(
    r"rate.limit|Sign in to confirm|not a bot|Too Many Requests",
    re.IGNORECASE,
)

# Try to extract a wait duration from the error message (e.g. "retry after 3600 seconds")
_WAIT_SECONDS_PATTERN = re.compile(
    r"(?:retry[- ]?after|wait)\s*[:=]?\s*(\d+)",
    re.IGNORECASE,
)

# Default wait when YouTube bans the session (~1 hour)
DEFAULT_BAN_WAIT_SECONDS = 3600


class YouTubeRateLimitError(Exception):
    """Raised when YouTube rate-limits or session-bans a request."""

    def __init__(self, message: str, wait_seconds: int = DEFAULT_BAN_WAIT_SECONDS):
        super().__init__(message)
        self.wait_seconds = wait_seconds


def parse_wait_seconds(message: str) -> int:
    """Extract wait duration from an error message.

    Falls back to DEFAULT_BAN_WAIT_SECONDS if nothing parseable is found.

    Args:
        message: Error message string from yt-dlp or HTTP response.

    Returns:
        Number of seconds to wait before retrying.
    """
    m = _WAIT_SECONDS_PATTERN.search(message)
    if m:
        try:
            return max(int(m.group(1)), 1)
        except (ValueError, OverflowError):
            pass
    return DEFAULT_BAN_WAIT_SECONDS


def is_rate_limit_message(message: str) -> bool:
    """Check whether *message* matches a known rate-limit pattern."""
    return bool(_RATE_LIMIT_PATTERNS.search(message))


class RateLimitDetector:
    """Logger adapter injected into yt-dlp to intercept rate-limit errors.

    yt-dlp with ``ignoreerrors=True`` logs errors instead of raising them.
    This wrapper watches ``error()`` calls and sets a flag when a rate-limit
    pattern is detected so the caller can react.

    Usage::

        detector = RateLimitDetector(existing_logger)
        ydl_opts["logger"] = detector
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if detector.rate_limited:
            raise YouTubeRateLimitError(detector.rate_limit_message,
                                        detector.wait_seconds)
    """

    def __init__(self, wrapped_logger: logging.Logger) -> None:
        self._logger = wrapped_logger
        self.rate_limited: bool = False
        self.rate_limit_message: str = ""
        self.wait_seconds: int = DEFAULT_BAN_WAIT_SECONDS

    # yt-dlp calls debug/info/warning/error on its logger
    def debug(self, msg: str) -> None:
        self._logger.debug(msg)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._check(msg)
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._check(msg)
        self._logger.error(msg)

    def _check(self, msg: str) -> None:
        if is_rate_limit_message(msg):
            self.rate_limited = True
            self.rate_limit_message = msg
            self.wait_seconds = parse_wait_seconds(msg)


def retry_on_ytdlp_rate_limit(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    max_wait_seconds: int = 7200,
    cookies_file: str | None = None,
    **kwargs: Any,
) -> T:
    """Call *func* and retry on rate-limit errors with progressive backoff.

    Handles both:
    - ``YouTubeRateLimitError`` (raised by caller after RateLimitDetector fires)
    - HTTP 429 / "Too Many Requests" embedded in generic exceptions

    Long waits use ``QuotaManager.sleep_with_progress()`` so the user sees
    periodic log lines instead of silence.

    Args:
        func: Callable to invoke.
        *args: Positional args forwarded to *func*.
        max_retries: Maximum number of retry attempts (default 3).
        max_wait_seconds: Cap on total wait per retry (default 7200 = 2 h).
        cookies_file: Informational only; logged so the user knows which
            cookie file is affected.
        **kwargs: Keyword args forwarded to *func*.

    Returns:
        Whatever *func* returns.

    Raises:
        YouTubeRateLimitError: If all retries are exhausted.
        Exception: Re-raises non-rate-limit errors immediately.
    """
    quota_mgr = QuotaManager(max_wait_hours=max_wait_seconds // 3600 + 1)
    backoff = 5  # initial short backoff for HTTP 429

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except YouTubeRateLimitError as exc:
            wait = min(exc.wait_seconds, max_wait_seconds)
            if attempt >= max_retries - 1:
                raise
            _log_and_sleep(quota_mgr, wait, attempt, max_retries, cookies_file)

        except Exception as exc:
            error_str = str(exc)
            if is_rate_limit_message(error_str) or _is_http_429(exc, error_str):
                wait = min(parse_wait_seconds(error_str), max_wait_seconds)
                # For plain 429 with no large wait hint, use short backoff
                if wait == DEFAULT_BAN_WAIT_SECONDS and _is_http_429(exc, error_str):
                    wait = min(backoff, max_wait_seconds)
                    backoff *= 2
                if attempt >= max_retries - 1:
                    raise YouTubeRateLimitError(error_str, wait) from exc
                _log_and_sleep(quota_mgr, wait, attempt, max_retries, cookies_file)
            else:
                raise

    # Should not reach here, but satisfy type-checker
    raise YouTubeRateLimitError("rate-limit retries exhausted")  # pragma: no cover


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_http_429(exc: Exception, error_str: str) -> bool:
    """Return True if *exc* looks like an HTTP 429."""
    if hasattr(exc, "code") and exc.code == 429:
        return True
    return "429" in error_str or "Too Many Requests" in error_str


def _log_and_sleep(
    quota_mgr: QuotaManager,
    wait: int,
    attempt: int,
    max_retries: int,
    cookies_file: str | None,
) -> None:
    cookie_info = f" (cookies: {cookies_file})" if cookies_file else ""
    logger.warning(
        "YouTube rate limit hit%s — waiting %s before retry %d/%d",
        cookie_info,
        quota_mgr.format_duration(wait),
        attempt + 1,
        max_retries,
    )
    if wait >= 60:
        # Long wait: use progress reporter
        quota_mgr.sleep_with_progress(wait, check_interval=min(300, wait))
    else:
        time.sleep(wait)
