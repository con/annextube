"""Tests for annextube.lib.ytdlp_ratelimit — rate-limit detection and retry."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from annextube.lib.ytdlp_ratelimit import (
    DEFAULT_BAN_WAIT_SECONDS,
    RateLimitDetector,
    YouTubeRateLimitError,
    is_rate_limit_message,
    parse_wait_seconds,
    retry_on_ytdlp_rate_limit,
)  # noqa: I001

# ---------------------------------------------------------------------------
# YouTubeRateLimitError
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestYouTubeRateLimitError:
    def test_default_wait(self):
        exc = YouTubeRateLimitError("banned")
        assert exc.wait_seconds == DEFAULT_BAN_WAIT_SECONDS
        assert "banned" in str(exc)

    def test_custom_wait(self):
        exc = YouTubeRateLimitError("slow down", wait_seconds=120)
        assert exc.wait_seconds == 120


# ---------------------------------------------------------------------------
# parse_wait_seconds
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestParseWaitSeconds:
    def test_retry_after_header(self):
        assert parse_wait_seconds("HTTP 429 Retry-After: 60") == 60

    def test_wait_keyword(self):
        assert parse_wait_seconds("please wait 120 seconds") == 120

    def test_no_match_returns_default(self):
        assert parse_wait_seconds("some random error") == DEFAULT_BAN_WAIT_SECONDS

    def test_zero_becomes_one(self):
        assert parse_wait_seconds("retry after 0") == 1

    def test_english_an_hour(self):
        assert parse_wait_seconds("for up to an hour") == 3600

    def test_english_30_minutes(self):
        assert parse_wait_seconds("for up to 30 minutes") == 1800

    def test_english_2_hours(self):
        assert parse_wait_seconds("for up to 2 hours") == 7200

    def test_english_full_ytdlp_message(self):
        msg = (
            "This content isn't available, try again later. "
            "Your account has been rate-limited by YouTube for up to an hour."
        )
        assert parse_wait_seconds(msg) == 3600


# ---------------------------------------------------------------------------
# is_rate_limit_message
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestIsRateLimitMessage:
    @pytest.mark.parametrize(
        "msg",
        [
            "ERROR: [youtube] XYZ: Sign in to confirm you're not a bot",
            "rate limit exceeded",
            "You are not a bot, right?",
            "HTTP Error 429: Too Many Requests",
        ],
    )
    def test_matches(self, msg):
        assert is_rate_limit_message(msg)

    @pytest.mark.parametrize(
        "msg",
        [
            "Video unavailable",
            "Private video",
            "Network error",
        ],
    )
    def test_no_match(self, msg):
        assert not is_rate_limit_message(msg)


# ---------------------------------------------------------------------------
# RateLimitDetector
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestRateLimitDetector:
    def test_passthrough_debug(self):
        base = MagicMock(spec=logging.Logger)
        det = RateLimitDetector(base)
        det.debug("hello")
        base.debug.assert_called_once_with("hello")
        assert not det.rate_limited

    def test_passthrough_info(self):
        base = MagicMock(spec=logging.Logger)
        det = RateLimitDetector(base)
        det.info("hello")
        base.info.assert_called_once_with("hello")
        assert not det.rate_limited

    def test_error_triggers_rate_limit(self):
        base = MagicMock(spec=logging.Logger)
        det = RateLimitDetector(base)
        det.error("ERROR: [youtube] XYZ: Sign in to confirm you're not a bot")
        assert det.rate_limited
        assert "Sign in" in det.rate_limit_message
        base.error.assert_called_once()

    def test_warning_triggers_rate_limit(self):
        base = MagicMock(spec=logging.Logger)
        det = RateLimitDetector(base)
        det.warning("rate limit hit — retry after 120")
        assert det.rate_limited
        assert det.wait_seconds == 120

    def test_normal_error_does_not_trigger(self):
        base = MagicMock(spec=logging.Logger)
        det = RateLimitDetector(base)
        det.error("Video unavailable: private")
        assert not det.rate_limited


# ---------------------------------------------------------------------------
# retry_on_ytdlp_rate_limit
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestRetryOnYtdlpRateLimit:
    def test_success_no_retry(self):
        result = retry_on_ytdlp_rate_limit(lambda: 42, max_retries=3)
        assert result == 42

    @patch("annextube.lib.ytdlp_ratelimit.time.sleep")
    @patch("annextube.lib.ytdlp_ratelimit.QuotaManager.sleep_with_progress")
    def test_retries_on_rate_limit_error(self, mock_progress, mock_sleep):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise YouTubeRateLimitError("banned", wait_seconds=10)
            return "ok"

        result = retry_on_ytdlp_rate_limit(flaky, max_retries=3, max_wait_seconds=100)
        assert result == "ok"
        assert call_count == 3

    @patch("annextube.lib.ytdlp_ratelimit.time.sleep")
    def test_retries_on_429_exception(self, mock_sleep):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("HTTP Error 429: Too Many Requests")
            return "ok"

        result = retry_on_ytdlp_rate_limit(flaky, max_retries=3, max_wait_seconds=100)
        assert result == "ok"
        assert call_count == 2
        mock_sleep.assert_called()

    def test_non_rate_limit_error_propagates(self):
        def fail():
            raise ValueError("something else")

        with pytest.raises(ValueError, match="something else"):
            retry_on_ytdlp_rate_limit(fail, max_retries=3)

    @patch("annextube.lib.ytdlp_ratelimit.time.sleep")
    @patch("annextube.lib.ytdlp_ratelimit.QuotaManager.sleep_with_progress")
    def test_exhausted_retries_raises(self, mock_progress, mock_sleep):
        def always_fail():
            raise YouTubeRateLimitError("permanent ban", wait_seconds=10)

        with pytest.raises(YouTubeRateLimitError, match="permanent ban"):
            retry_on_ytdlp_rate_limit(
                always_fail, max_retries=2, max_wait_seconds=100
            )

    @patch("annextube.lib.ytdlp_ratelimit.time.sleep")
    @patch("annextube.lib.ytdlp_ratelimit.QuotaManager.sleep_with_progress")
    def test_max_wait_seconds_caps_wait(self, mock_progress, mock_sleep):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise YouTubeRateLimitError("banned", wait_seconds=99999)
            return "ok"

        result = retry_on_ytdlp_rate_limit(
            flaky, max_retries=3, max_wait_seconds=60
        )
        assert result == "ok"
        # sleep_with_progress should have been called with capped wait
        mock_progress.assert_called_once()
        actual_wait = mock_progress.call_args[0][0]
        assert actual_wait <= 60
