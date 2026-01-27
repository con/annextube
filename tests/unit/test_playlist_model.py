"""Unit tests for Playlist model - updated_at field removal."""

import pytest
from datetime import datetime
from annextube.models.playlist import Playlist


@pytest.mark.ai_generated
def test_playlist_model_no_updated_at_field() -> None:
    """Verify Playlist model does not have updated_at field in dataclass definition."""
    # Check that updated_at is not in the dataclass fields
    field_names = [f.name for f in Playlist.__dataclass_fields__.values()]
    assert "updated_at" not in field_names, "updated_at field should be removed from Playlist model"


@pytest.mark.ai_generated
def test_playlist_to_dict_no_updated_at() -> None:
    """Verify Playlist.to_dict() does not include updated_at field."""
    playlist = Playlist(
        playlist_id="PL123",
        title="Test Playlist",
        description="Test playlist description",
        channel_id="channel123",
        channel_name="Test Channel",
        video_count=10,
        privacy_status="public",
        last_modified=datetime(2026, 1, 25, 15, 0, 0),
        video_ids=["vid1", "vid2", "vid3"],
        thumbnail_url="https://example.com/playlist_thumb.jpg",
        fetched_at=datetime(2026, 1, 26, 10, 0, 0),
    )

    playlist_dict = playlist.to_dict()

    # Verify updated_at is not in the dictionary
    assert "updated_at" not in playlist_dict, "updated_at should not be in Playlist.to_dict() output"

    # Verify fetched_at is still present
    assert "fetched_at" in playlist_dict, "fetched_at should still be present"
    assert playlist_dict["fetched_at"] == "2026-01-26T10:00:00"


@pytest.mark.ai_generated
def test_playlist_from_dict_no_updated_at_required() -> None:
    """Verify Playlist can be created from dict without updated_at field."""
    data = {
        "playlist_id": "PL123",
        "title": "Test Playlist",
        "description": "Test playlist description",
        "channel_id": "channel123",
        "channel_name": "Test Channel",
        "video_count": 10,
        "privacy_status": "public",
        "last_modified": "2026-01-25T15:00:00",
        "video_ids": ["vid1", "vid2", "vid3"],
        "thumbnail_url": "https://example.com/playlist_thumb.jpg",
        "fetched_at": "2026-01-26T10:00:00",
        # Note: no updated_at field
    }

    # Should successfully create Playlist without updated_at (if from_dict exists)
    # Note: Playlist model doesn't have from_dict in the file read earlier,
    # so we'll just verify the dataclass can be instantiated
    playlist = Playlist(
        playlist_id=data["playlist_id"],
        title=data["title"],
        description=data["description"],
        channel_id=data["channel_id"],
        channel_name=data["channel_name"],
        video_count=data["video_count"],
        privacy_status=data["privacy_status"],
        last_modified=datetime.fromisoformat(data["last_modified"]),
        video_ids=data["video_ids"],
        thumbnail_url=data["thumbnail_url"],
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
    )

    assert playlist.playlist_id == "PL123"
    assert playlist.fetched_at == datetime(2026, 1, 26, 10, 0, 0)
    # Verify no updated_at attribute exists
    assert not hasattr(playlist, "updated_at"), "Playlist instance should not have updated_at attribute"
