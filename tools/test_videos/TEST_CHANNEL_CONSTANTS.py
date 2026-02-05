"""
Test channel constants for annextube integration tests.

Add these to tests/conftest.py or use directly in test files.

Channel: https://www.youtube.com/channel/UCHpuDwi3IorJ_Uez2e7pqHA
Upload Date: 2026-02-04
Total Videos: 10 (2 pending due to upload limit)
"""

# Test Channel Information
TEST_CHANNEL_URL = "https://www.youtube.com/channel/UCHpuDwi3IorJ_Uez2e7pqHA"
TEST_CHANNEL_ID = "UCHpuDwi3IorJ_Uez2e7pqHA"
TEST_CHANNEL_NAME = "AnnexTube Test Channel"

# Video IDs by License Type

TEST_VIDEOS_STANDARD_LICENSE = [
    "ma84N_6Mybs",  # Test Video - Standard License 1 (1s, red)
    "hWIfEDjYFVY",  # Test Video - Standard License 2 (2s, green)
    "Yr5-9l0euPg",  # Test Video - Standard License 3 (3s, blue)
    "rN7TFeaTsKY",  # Test Video - English Captions (5s, with EN captions)
    "CPfZiBffVQs",  # Test Video - NYC Location (3s, NYC GPS)
]

TEST_VIDEOS_CREATIVE_COMMONS = [
    "GhGQV_enM8M",  # Test Video - Creative Commons 1 (1s, yellow)
    "BZeKDYqsuj0",  # Test Video - Creative Commons 2 (2s, magenta)
    "2zCuyKp6-Ws",  # Test Video - Creative Commons 3 (3s, cyan)
    "s4J8b9qNJ6U",  # Test Video - Multilingual Captions (5s, EN/ES/DE)
    "KB8yRMmZkkM",  # Test Video - London Location (3s, London GPS)
]

# Videos with Captions (language -> video_ids)
TEST_VIDEOS_WITH_CAPTIONS = {
    "en": ["rN7TFeaTsKY", "s4J8b9qNJ6U"],
    "es": ["s4J8b9qNJ6U"],
    "de": ["s4J8b9qNJ6U"],
}

# Videos with Location Metadata
TEST_VIDEOS_WITH_LOCATION = {
    "CPfZiBffVQs": {
        "location": "New York City, NY",
        "country": "US",
        "coordinates": {"latitude": 40.7128, "longitude": -74.0060},
    },
    "KB8yRMmZkkM": {
        "location": "London, UK",
        "country": "UK",
        "coordinates": {"latitude": 51.5074, "longitude": -0.1278},
    },
}

# All Test Videos
TEST_CHANNEL_VIDEOS = TEST_VIDEOS_STANDARD_LICENSE + TEST_VIDEOS_CREATIVE_COMMONS

# Playlists (with overlapping videos for comprehensive testing)
TEST_CHANNEL_PLAYLISTS = {
    "All Standard License Videos": "PLQg3etb9oyYgj0OpGuC7CX6f4MeYm9ofO",  # 5 videos
    "All Creative Commons Videos": "PLQg3etb9oyYibGgyxpj2qyllYRgfNIWcl",  # 5 videos
    "Mixed License Videos": "PLQg3etb9oyYiTXLE5NHTWVuxtD7nMCoLm",  # All 10 videos
    "Videos with Captions": "PLQg3etb9oyYg7EjBqjlvbFZxYA20pOQC0",  # 2 videos
    "Videos with Location Metadata": "PLQg3etb9oyYi4HoXWFLb-DZBpAsPqK0HV",  # 2 videos
}

# Playlist URLs
TEST_PLAYLIST_URLS = {
    "standard": f"https://www.youtube.com/playlist?list={TEST_CHANNEL_PLAYLISTS['All Standard License Videos']}",
    "creative_commons": f"https://www.youtube.com/playlist?list={TEST_CHANNEL_PLAYLISTS['All Creative Commons Videos']}",
    "mixed": f"https://www.youtube.com/playlist?list={TEST_CHANNEL_PLAYLISTS['Mixed License Videos']}",
    "captions": f"https://www.youtube.com/playlist?list={TEST_CHANNEL_PLAYLISTS['Videos with Captions']}",
    "location": f"https://www.youtube.com/playlist?list={TEST_CHANNEL_PLAYLISTS['Videos with Location Metadata']}",
}

# Video Details (for comprehensive testing)
TEST_VIDEO_DETAILS = {
    # Standard License Videos
    "ma84N_6Mybs": {
        "title": "Test Video - Standard License 1",
        "license": "youtube",
        "duration": 1,
        "color": "red",
    },
    "hWIfEDjYFVY": {
        "title": "Test Video - Standard License 2",
        "license": "youtube",
        "duration": 2,
        "color": "green",
    },
    "Yr5-9l0euPg": {
        "title": "Test Video - Standard License 3",
        "license": "youtube",
        "duration": 3,
        "color": "blue",
    },
    "rN7TFeaTsKY": {
        "title": "Test Video - English Captions",
        "license": "youtube",
        "duration": 5,
        "captions": ["en"],
    },
    "CPfZiBffVQs": {
        "title": "Test Video - NYC Location",
        "license": "youtube",
        "duration": 3,
        "location": "New York City, NY",
    },
    # Creative Commons Videos
    "GhGQV_enM8M": {
        "title": "Test Video - Creative Commons 1",
        "license": "creativeCommon",
        "duration": 1,
        "color": "yellow",
    },
    "BZeKDYqsuj0": {
        "title": "Test Video - Creative Commons 2",
        "license": "creativeCommon",
        "duration": 2,
        "color": "magenta",
    },
    "2zCuyKp6-Ws": {
        "title": "Test Video - Creative Commons 3",
        "license": "creativeCommon",
        "duration": 3,
        "color": "cyan",
    },
    "s4J8b9qNJ6U": {
        "title": "Test Video - Multilingual Captions",
        "license": "creativeCommon",
        "duration": 5,
        "captions": ["en", "es", "de"],
    },
    "KB8yRMmZkkM": {
        "title": "Test Video - London Location",
        "license": "creativeCommon",
        "duration": 3,
        "location": "London, UK",
    },
}


# Example Usage in Tests
"""
import pytest
from annextube.services.youtube import YouTubeService
from .test_videos.TEST_CHANNEL_CONSTANTS import (
    TEST_CHANNEL_URL,
    TEST_VIDEOS_STANDARD_LICENSE,
    TEST_VIDEOS_CREATIVE_COMMONS,
)


def test_license_detection_standard(youtube_api_key: str) -> None:
    '''Test standard YouTube license detection.'''
    service = YouTubeService(youtube_api_key=youtube_api_key)

    for video_id in TEST_VIDEOS_STANDARD_LICENSE:
        video = service.get_video_metadata(video_id)
        assert video.license == "youtube", f"Video {video_id} should have standard license"


def test_license_detection_creative_commons(youtube_api_key: str) -> None:
    '''Test Creative Commons license detection.'''
    service = YouTubeService(youtube_api_key=youtube_api_key)

    for video_id in TEST_VIDEOS_CREATIVE_COMMONS:
        video = service.get_video_metadata(video_id)
        assert video.license == "creativeCommon", f"Video {video_id} should have CC license"


def test_backup_test_channel(tmp_git_annex_repo: Path) -> None:
    '''Test backing up entire test channel.'''
    archiver = Archiver(tmp_git_annex_repo, config)

    result = archiver.backup_channel(TEST_CHANNEL_URL)

    assert result["videos_processed"] == 10  # Reliable count!
    assert result["videos_failed"] == 0


def test_backup_playlist_mixed_licenses(tmp_git_annex_repo: Path) -> None:
    '''Test backing up playlist with both standard and CC licensed videos.'''
    from .test_videos.TEST_CHANNEL_CONSTANTS import TEST_PLAYLIST_URLS

    archiver = Archiver(tmp_git_annex_repo, config)

    result = archiver.backup_playlist(TEST_PLAYLIST_URLS["mixed"])

    # Mixed playlist contains all 10 videos
    assert result["videos_processed"] == 10
    # Should have both license types
    videos = list(tmp_git_annex_repo.glob("*.mp4"))
    assert len(videos) == 10


def test_playlist_overlap_detection(tmp_git_annex_repo: Path) -> None:
    '''Test handling of overlapping playlists (same videos in multiple playlists).'''
    from .test_videos.TEST_CHANNEL_CONSTANTS import TEST_PLAYLIST_URLS

    archiver = Archiver(tmp_git_annex_repo, config)

    # Backup standard license playlist
    result1 = archiver.backup_playlist(TEST_PLAYLIST_URLS["standard"])
    assert result1["videos_processed"] == 4

    # Backup mixed playlist (contains some of the same videos)
    result2 = archiver.backup_playlist(TEST_PLAYLIST_URLS["mixed"])

    # Should skip already-downloaded videos
    assert result2["videos_skipped"] >= 4
"""
