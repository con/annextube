"""Unit tests for YouTube API quota estimation."""

import pytest

from annextube.services.youtube_api import QuotaEstimator


@pytest.mark.ai_generated
def test_estimate_video_metadata_cost() -> None:
    """Test quota cost calculation for video metadata with batching."""
    # 0 videos = 0 units
    assert QuotaEstimator.estimate_video_metadata_cost(0) == 0

    # 1 video = 1 request = 1 unit
    assert QuotaEstimator.estimate_video_metadata_cost(1) == 1

    # 50 videos = 1 request = 1 unit (max batch size)
    assert QuotaEstimator.estimate_video_metadata_cost(50) == 1

    # 51 videos = 2 requests = 2 units
    assert QuotaEstimator.estimate_video_metadata_cost(51) == 2

    # 100 videos = 2 requests = 2 units
    assert QuotaEstimator.estimate_video_metadata_cost(100) == 2

    # 1,000 videos = 20 requests = 20 units
    assert QuotaEstimator.estimate_video_metadata_cost(1_000) == 20

    # 2,000 videos = 40 requests = 40 units
    assert QuotaEstimator.estimate_video_metadata_cost(2_000) == 40


@pytest.mark.ai_generated
def test_estimate_comments_cost() -> None:
    """Test quota cost calculation for comment requests."""
    # 0 requests = 0 units
    assert QuotaEstimator.estimate_comments_cost(0) == 0

    # 1 request = 1 unit
    assert QuotaEstimator.estimate_comments_cost(1) == 1

    # 5 requests = 5 units
    assert QuotaEstimator.estimate_comments_cost(5) == 5

    # 100 requests = 100 units
    assert QuotaEstimator.estimate_comments_cost(100) == 100


@pytest.mark.ai_generated
def test_can_fit_in_free_tier() -> None:
    """Test free tier capacity checking."""
    # With batching, 10,000 videos = 200 requests = 200 units (easily fits)
    assert QuotaEstimator.can_fit_in_free_tier(10_000) is True

    # Even very large numbers fit because of batching
    assert QuotaEstimator.can_fit_in_free_tier(500_000) is True  # 10,000 requests = 10,000 units

    # 500,001 videos = 10,001 requests (exceeds free tier)
    assert QuotaEstimator.can_fit_in_free_tier(500_001) is False

    # Videos + comment requests
    assert QuotaEstimator.can_fit_in_free_tier(100, num_comments=5) is True  # 2 + 5 = 7 units

    # Exactly at limit: 499,950 videos (9,999 requests) + 1 comment request = 10,000 units
    assert QuotaEstimator.can_fit_in_free_tier(499_950, num_comments=1) is True

    # Over limit: 500,000 videos (10,000 requests) + 1 comment request = 10,001 units
    assert QuotaEstimator.can_fit_in_free_tier(500_000, num_comments=1) is False


@pytest.mark.ai_generated
def test_format_cost_report_videos_only() -> None:
    """Test cost report generation for videos only."""
    # 1,000 videos = 20 requests (fits in free tier)
    report = QuotaEstimator.format_cost_report(1_000)

    assert "YouTube API Quota Estimation" in report
    assert "1,000" in report
    assert "20 request(s)" in report
    assert "Daily free quota: 10,000 units/day" in report
    assert "[ok] Fits within free tier" in report

    # Should not include pricing info when within free tier
    assert "Paid Quota Pricing" not in report
    assert "Estimated cost" not in report


@pytest.mark.ai_generated
def test_format_cost_report_exceeds_free_tier() -> None:
    """Test cost report when exceeding free tier."""
    # 1,000,000 videos = 20,000 requests (exceeds free tier)
    report = QuotaEstimator.format_cost_report(1_000_000)

    assert "1,000,000" in report
    assert "[!] Exceeds free tier by 10,000 units" in report
    assert "Requires 2 day(s) at free tier rate" in report

    # Should include pricing info
    assert "Paid Quota Pricing (if purchased)" in report
    assert "Overage units:    10,000 units" in report


@pytest.mark.ai_generated
def test_format_cost_report_with_comments() -> None:
    """Test cost report with videos and comments."""
    # 100 videos + 5 comment requests
    report = QuotaEstimator.format_cost_report(100, num_comments=5)

    assert "100" in report
    assert "Comment requests:" in report


@pytest.mark.ai_generated
def test_format_cost_report_no_pricing() -> None:
    """Test cost report without pricing information."""
    # Large number with pricing disabled
    report = QuotaEstimator.format_cost_report(1_000_000, include_pricing=False)

    assert "[!] Exceeds free tier" in report

    # Should NOT include pricing section
    assert "Paid Quota Pricing" not in report
    assert "Estimated cost" not in report


@pytest.mark.ai_generated
def test_quota_constants() -> None:
    """Verify quota constant values match YouTube API documentation."""
    assert QuotaEstimator.COST_PER_VIDEO_REQUEST == 1
    assert QuotaEstimator.COST_PER_COMMENT_REQUEST == 1
    assert QuotaEstimator.VIDEOS_PER_REQUEST == 50
    assert QuotaEstimator.COMMENTS_PER_REQUEST == 100
    assert QuotaEstimator.FREE_TIER_DAILY_QUOTA == 10_000
