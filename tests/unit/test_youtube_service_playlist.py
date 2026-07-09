"""Unit tests for YouTubeService.get_playlist_metadata API cross-check."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from annextube.services.youtube import YouTubeService


def _make_service(api_client: MagicMock | None = None) -> YouTubeService:
    """Build a YouTubeService without triggering __init__ side effects."""
    service = object.__new__(YouTubeService)
    service.archive_file = None
    service.cookies_file = None
    service.cookies_from_browser = None
    service.proxy = None
    service.limit_rate = None
    service.sleep_interval = None
    service.max_sleep_interval = None
    service.extractor_args = {}
    service.remote_components = None
    service._last_unavailable_ids = set()
    service.api_client = api_client
    service._rate_limit_max_wait_seconds = 60
    service._semaphore = None
    return service


def _yt_info(
    playlist_id: str = "PL_test",
    playlist_count: int | None = 144,
    entry_count: int = 100,
) -> dict:
    """Build a fake yt-dlp extract_info payload."""
    return {
        "id": playlist_id,
        "title": "Test",
        "description": "",
        "channel_id": "UC_test",
        "channel": "Test Channel",
        "playlist_count": playlist_count,
        "availability": "public",
        "thumbnail": None,
        "modified_date": None,
        "entries": [{"id": f"vid{i:03d}"} for i in range(entry_count)],
    }


@pytest.mark.ai_generated
def test_get_playlist_metadata_uses_api_when_ytdlp_truncated() -> None:
    """When yt-dlp truncates, get_playlist_metadata pulls the full list from the API."""
    api = MagicMock()
    api.get_playlist_video_ids.return_value = [f"vid{i:03d}" for i in range(144)]
    service = _make_service(api_client=api)

    with patch.object(
        service, "_with_rate_limit_retry",
        return_value=_yt_info(playlist_count=144, entry_count=100),
    ):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )

    assert result is not None
    assert len(result.video_ids) == 144
    assert result.video_count == 144
    api.get_playlist_video_ids.assert_called_once_with("PL_test")


@pytest.mark.ai_generated
def test_get_playlist_metadata_keeps_ytdlp_when_no_api_client() -> None:
    """Without an API client the guard downstream must handle truncation.

    ``get_playlist_metadata`` itself returns the truncated list; the
    archiver's ``_save_playlist_metadata`` guard is what refuses to persist.
    """
    service = _make_service(api_client=None)
    with patch.object(
        service, "_with_rate_limit_retry",
        return_value=_yt_info(playlist_count=144, entry_count=100),
    ):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )

    assert result is not None
    assert len(result.video_ids) == 100
    assert result.video_count == 144  # authoritative count survives


@pytest.mark.ai_generated
def test_get_playlist_metadata_keeps_ytdlp_when_api_returns_none() -> None:
    """If the API cross-check fails (network etc.), fall through to yt-dlp."""
    api = MagicMock()
    api.get_playlist_video_ids.return_value = None
    service = _make_service(api_client=api)

    with patch.object(
        service, "_with_rate_limit_retry",
        return_value=_yt_info(playlist_count=144, entry_count=100),
    ):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )

    assert result is not None
    assert len(result.video_ids) == 100
    assert result.video_count == 144


@pytest.mark.ai_generated
def test_get_playlist_metadata_keeps_ytdlp_when_api_returns_fewer() -> None:
    """API omits deleted/private videos; yt-dlp's superset is preserved."""
    api = MagicMock()
    api.get_playlist_video_ids.return_value = [f"vid{i:03d}" for i in range(96)]
    service = _make_service(api_client=api)

    with patch.object(
        service, "_with_rate_limit_retry",
        return_value=_yt_info(playlist_count=100, entry_count=100),
    ):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )

    assert result is not None
    # yt-dlp saw 100, api saw 96, guard says len(new)=100 !< reported=100
    # so API cross-check is not even invoked.
    api.get_playlist_video_ids.assert_not_called()
    assert len(result.video_ids) == 100


@pytest.mark.ai_generated
def test_get_playlist_metadata_no_cross_check_when_counts_match() -> None:
    """The API is not called when yt-dlp already delivered playlist_count entries."""
    api = MagicMock()
    service = _make_service(api_client=api)

    with patch.object(
        service, "_with_rate_limit_retry",
        return_value=_yt_info(playlist_count=144, entry_count=144),
    ):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )

    assert result is not None
    assert len(result.video_ids) == 144
    api.get_playlist_video_ids.assert_not_called()


@pytest.mark.ai_generated
def test_get_playlist_metadata_coerces_string_playlist_count() -> None:
    """yt-dlp has been known to return counts as strings; we must coerce."""
    api = MagicMock()
    api.get_playlist_video_ids.return_value = [f"vid{i:03d}" for i in range(144)]
    service = _make_service(api_client=api)

    info = _yt_info(playlist_count=144, entry_count=100)
    info["playlist_count"] = "144"  # simulate untyped yt-dlp regression

    with patch.object(service, "_with_rate_limit_retry", return_value=info):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )

    assert result is not None
    assert result.video_count == 144  # coerced to int
    # Truncation guard therefore still fires → API cross-check happens.
    api.get_playlist_video_ids.assert_called_once()
    assert len(result.video_ids) == 144


@pytest.mark.ai_generated
def test_get_playlist_metadata_race_gained_video_preserved() -> None:
    """A video added mid-fetch (entries > playlist_count) must not be dropped."""
    service = _make_service(api_client=None)
    with patch.object(
        service, "_with_rate_limit_retry",
        return_value=_yt_info(playlist_count=3, entry_count=4),
    ):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )

    assert result is not None
    assert len(result.video_ids) == 4
    # video_count reflects yt-dlp's reported (raced) header value.
    assert result.video_count == 3


@pytest.mark.ai_generated
def test_get_playlist_metadata_returns_none_when_extract_fails() -> None:
    """Extraction returning None short-circuits to None."""
    service = _make_service(api_client=None)
    with patch.object(service, "_with_rate_limit_retry", return_value=None):
        result = service.get_playlist_metadata(
            "https://www.youtube.com/playlist?list=PL_test",
        )
    assert result is None


@pytest.mark.ai_generated
def test_get_playlist_metadata_parses_modified_date() -> None:
    """Well-formed modified_date is parsed; malformed falls through silently."""
    service = _make_service(api_client=None)

    info = _yt_info(playlist_count=1, entry_count=1)
    info["modified_date"] = "20260701"
    with patch.object(service, "_with_rate_limit_retry", return_value=info):
        result = service.get_playlist_metadata("https://www.youtube.com/playlist?list=PL_test")
    assert result is not None
    assert result.last_modified == datetime(2026, 7, 1)

    info["modified_date"] = "not-a-date"
    with patch.object(service, "_with_rate_limit_retry", return_value=info):
        result = service.get_playlist_metadata("https://www.youtube.com/playlist?list=PL_test")
    assert result is not None
    assert result.last_modified is None
