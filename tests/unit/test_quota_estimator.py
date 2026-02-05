"""Unit tests for YouTube API quota estimation."""

import pytest

from annextube.services.youtube_api import QuotaEstimator


@pytest.mark.ai_generated
def test_estimate_video_metadata_cost() -> None:
    """Test quota cost calculation for video metadata."""
    # Single video
    assert QuotaEstimator.estimate_video_metadata_cost(1) == 10

    # 100 videos = 1,000 units (fits in free tier)
    assert QuotaEstimator.estimate_video_metadata_cost(100) == 1_000

    # 1,000 videos = 10,000 units (exactly free tier limit)
    assert QuotaEstimator.estimate_video_metadata_cost(1_000) == 10_000

    # 2,000 videos = 20,000 units (exceeds free tier)
    assert QuotaEstimator.estimate_video_metadata_cost(2_000) == 20_000


@pytest.mark.ai_generated
def test_estimate_comments_cost() -> None:
    """Test quota cost calculation for comments."""
    # 0 comments = 0 units
    assert QuotaEstimator.estimate_comments_cost(0) == 0

    # 1-100 comments = 1 unit
    assert QuotaEstimator.estimate_comments_cost(1) == 1
    assert QuotaEstimator.estimate_comments_cost(50) == 1
    assert QuotaEstimator.estimate_comments_cost(100) == 1

    # 101 comments = 2 units
    assert QuotaEstimator.estimate_comments_cost(101) == 2

    # 200 comments = 2 units
    assert QuotaEstimator.estimate_comments_cost(200) == 2

    # 10,000 comments = 100 units
    assert QuotaEstimator.estimate_comments_cost(10_000) == 100


@pytest.mark.ai_generated
def test_can_fit_in_free_tier() -> None:
    """Test free tier capacity checking."""
    # 1,000 videos fits exactly (10,000 units)
    assert QuotaEstimator.can_fit_in_free_tier(1_000) is True

    # 999 videos fits with room to spare
    assert QuotaEstimator.can_fit_in_free_tier(999) is True

    # 1,001 videos exceeds free tier
    assert QuotaEstimator.can_fit_in_free_tier(1_001) is False

    # 500 videos + 10,000 comments = 5,000 + 100 = 5,100 units (fits)
    assert QuotaEstimator.can_fit_in_free_tier(500, num_comments=10_000) is True

    # 1,000 videos + 1 comment = 10,000 + 1 = 10,001 units (exceeds)
    assert QuotaEstimator.can_fit_in_free_tier(1_000, num_comments=1) is False


@pytest.mark.ai_generated
def test_format_cost_report_videos_only() -> None:
    """Test cost report generation for videos only."""
    # 1,000 videos (fits in free tier)
    report = QuotaEstimator.format_cost_report(1_000)

    assert "YouTube API Quota Estimation" in report
    assert "1,000 × 10 units = 10,000 units" in report
    assert "Daily free quota: 10,000 units/day" in report
    assert "[ok] Fits within free tier" in report
    assert "100.0% of daily quota" in report

    # Should not include pricing info when within free tier
    assert "Paid Quota Pricing" not in report
    assert "Estimated cost" not in report


@pytest.mark.ai_generated
def test_format_cost_report_exceeds_free_tier() -> None:
    """Test cost report when exceeding free tier."""
    # 2,000 videos (exceeds free tier)
    report = QuotaEstimator.format_cost_report(2_000)

    assert "2,000 × 10 units = 20,000 units" in report
    assert "[!] Exceeds free tier by 10,000 units" in report
    assert "Requires 2 day(s) at free tier rate" in report

    # Should include pricing info
    assert "Paid Quota Pricing (if purchased)" in report
    assert "Overage units:    10,000 units" in report
    assert "Cost per 100:     $0.10 USD" in report
    assert "Estimated cost:   $10.00 USD" in report
    assert "Additional quota must be requested" in report


@pytest.mark.ai_generated
def test_format_cost_report_with_comments() -> None:
    """Test cost report with videos and comments."""
    # 500 videos + 10,000 comments
    report = QuotaEstimator.format_cost_report(500, num_comments=10_000)

    assert "500 × 10 units = 5,000 units" in report
    assert "10,000 ÷ 100 = 100 units" in report
    assert "Total:            5,100 units" in report
    assert "[ok] Fits within free tier (51.0% of daily quota)" in report


@pytest.mark.ai_generated
def test_format_cost_report_no_pricing() -> None:
    """Test cost report without pricing information."""
    # 2,000 videos with pricing disabled
    report = QuotaEstimator.format_cost_report(2_000, include_pricing=False)

    assert "2,000 × 10 units = 20,000 units" in report
    assert "[!] Exceeds free tier by 10,000 units" in report

    # Should NOT include pricing section
    assert "Paid Quota Pricing" not in report
    assert "Estimated cost" not in report


@pytest.mark.ai_generated
def test_format_cost_report_large_overage() -> None:
    """Test cost report with large overage amounts."""
    # 10,000 videos = 100,000 units
    report = QuotaEstimator.format_cost_report(10_000)

    assert "10,000 × 10 units = 100,000 units" in report
    assert "[!] Exceeds free tier by 90,000 units" in report
    assert "Requires 10 day(s) at free tier rate" in report
    assert "Estimated cost:   $90.00 USD" in report


@pytest.mark.ai_generated
def test_quota_constants() -> None:
    """Verify quota constant values match YouTube API documentation."""
    assert QuotaEstimator.COST_PER_VIDEO_METADATA == 10
    assert QuotaEstimator.COST_PER_100_COMMENTS == 1
    assert QuotaEstimator.FREE_TIER_DAILY_QUOTA == 10_000
