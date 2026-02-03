"""Unit tests for Video model - updated_at field removal."""

from datetime import datetime

import pytest

from annextube.models.video import Video


@pytest.mark.ai_generated
def test_video_model_no_updated_at_field() -> None:
    """Verify Video model does not have updated_at field in dataclass definition."""
    # Check that updated_at is not in the dataclass fields
    field_names = [f.name for f in Video.__dataclass_fields__.values()]
    assert "updated_at" not in field_names, "updated_at field should be removed from Video model"


@pytest.mark.ai_generated
def test_video_to_dict_no_updated_at() -> None:
    """Verify Video.to_dict() does not include updated_at field."""
    video = Video(
        video_id="test123",
        title="Test Video",
        description="Test description",
        channel_id="channel123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 1, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=50,
        comment_count=10,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=["test", "video"],
        categories=["Science & Technology"],
        captions_available=["en"],
        has_auto_captions=True,
        download_status="not_downloaded",
        source_url="https://www.youtube.com/watch?v=test123",
        fetched_at=datetime(2026, 1, 26, 10, 0, 0),
    )

    video_dict = video.to_dict()

    # Verify updated_at is not in the dictionary
    assert "updated_at" not in video_dict, "updated_at should not be in Video.to_dict() output"

    # Verify fetched_at is still present
    assert "fetched_at" in video_dict, "fetched_at should still be present"
    assert video_dict["fetched_at"] == "2026-01-26T10:00:00"


@pytest.mark.ai_generated
def test_video_from_dict_no_updated_at_required() -> None:
    """Verify Video.from_dict() works without updated_at field."""
    data = {
        "video_id": "test123",
        "title": "Test Video",
        "description": "Test description",
        "channel_id": "channel123",
        "channel_name": "Test Channel",
        "published_at": "2026-01-01T12:00:00",
        "duration": 300,
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
        "thumbnail_url": "https://example.com/thumb.jpg",
        "license": "standard",
        "privacy_status": "public",
        "availability": "public",
        "tags": ["test", "video"],
        "categories": ["Science & Technology"],
        "language": "en",
        "captions_available": ["en"],
        "has_auto_captions": True,
        "download_status": "not_downloaded",
        "source_url": "https://www.youtube.com/watch?v=test123",
        "fetched_at": "2026-01-26T10:00:00",
        # Note: no updated_at field
    }

    # Should successfully create Video without updated_at
    video = Video.from_dict(data)

    assert video.video_id == "test123"
    assert video.fetched_at == datetime(2026, 1, 26, 10, 0, 0)
    # Verify no updated_at attribute exists
    assert not hasattr(video, "updated_at"), "Video instance should not have updated_at attribute"
