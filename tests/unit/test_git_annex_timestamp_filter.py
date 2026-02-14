"""Unit tests for git-annex timestamp-only change filtering."""

import json
import subprocess
from pathlib import Path

import pytest

from annextube.services.git_annex import GitAnnexService


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)

    # Initialize git-annex
    subprocess.run(["git", "annex", "init", "test-repo"], cwd=repo_path, check=True, capture_output=True)

    return repo_path


@pytest.mark.ai_generated
def test_filter_no_changes(git_repo: Path) -> None:
    """Test _filter_timestamp_only_changes with no changes returns False."""
    service = GitAnnexService(git_repo)

    # Create and commit a file
    test_file = git_repo / "metadata.json"
    test_file.write_text(json.dumps({"video_id": "test123", "fetched_at": "2026-01-01T00:00:00"}))
    subprocess.run(["git", "add", "metadata.json"], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo, check=True, capture_output=True)

    # No changes since commit
    result = service._filter_timestamp_only_changes()

    assert result is False, "Should return False when no changes exist"


@pytest.mark.ai_generated
def test_filter_timestamp_only_changes_detected(git_repo: Path) -> None:
    """Test _filter_timestamp_only_changes detects and restores timestamp-only changes."""
    service = GitAnnexService(git_repo)

    # Create and commit initial file
    test_file = git_repo / "metadata.json"
    initial_data = {"video_id": "test123", "title": "Test Video", "fetched_at": "2026-01-01T00:00:00"}
    test_file.write_text(json.dumps(initial_data, indent=2))
    subprocess.run(["git", "add", "metadata.json"], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo, check=True, capture_output=True)

    # Modify only timestamp
    updated_data = {"video_id": "test123", "title": "Test Video", "fetched_at": "2026-01-26T10:00:00"}
    test_file.write_text(json.dumps(updated_data, indent=2))

    # Check for changes
    result = service._filter_timestamp_only_changes()

    # Should detect and restore timestamp-only changes
    assert result is False, "Should return False after restoring timestamp-only changes"

    # Verify file was restored
    diff_result = subprocess.run(["git", "diff", "--name-only"], cwd=git_repo, capture_output=True, text=True)
    assert diff_result.stdout.strip() == "", "File should be restored with no changes"


@pytest.mark.ai_generated
def test_filter_real_changes_preserved(git_repo: Path) -> None:
    """Test _filter_timestamp_only_changes preserves real content changes."""
    service = GitAnnexService(git_repo)

    # Create and commit initial file
    test_file = git_repo / "metadata.json"
    initial_data = {"video_id": "test123", "title": "Test Video", "fetched_at": "2026-01-01T00:00:00"}
    test_file.write_text(json.dumps(initial_data, indent=2))
    subprocess.run(["git", "add", "metadata.json"], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo, check=True, capture_output=True)

    # Modify title AND timestamp
    updated_data = {"video_id": "test123", "title": "Updated Title", "fetched_at": "2026-01-26T10:00:00"}
    test_file.write_text(json.dumps(updated_data, indent=2))

    # Check for changes
    result = service._filter_timestamp_only_changes()

    # Should detect real changes and return True
    assert result is True, "Should return True when real changes exist"

    # Verify file still has changes
    diff_result = subprocess.run(["git", "diff", "--name-only"], cwd=git_repo, capture_output=True, text=True)
    assert "metadata.json" in diff_result.stdout, "Real changes should be preserved"


@pytest.mark.ai_generated
def test_filter_mixed_files(git_repo: Path) -> None:
    """Test _filter_timestamp_only_changes with mix of timestamp-only and real changes."""
    service = GitAnnexService(git_repo)

    # Create and commit two files
    file1 = git_repo / "video1" / "metadata.json"
    file2 = git_repo / "video2" / "metadata.json"
    file1.parent.mkdir(parents=True)
    file2.parent.mkdir(parents=True)

    data1 = {"video_id": "vid1", "title": "Video 1", "fetched_at": "2026-01-01T00:00:00"}
    data2 = {"video_id": "vid2", "title": "Video 2", "fetched_at": "2026-01-01T00:00:00"}

    file1.write_text(json.dumps(data1, indent=2))
    file2.write_text(json.dumps(data2, indent=2))

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo, check=True, capture_output=True)

    # File1: timestamp-only change
    data1_updated = {"video_id": "vid1", "title": "Video 1", "fetched_at": "2026-01-26T10:00:00"}
    file1.write_text(json.dumps(data1_updated, indent=2))

    # File2: real change (title + timestamp)
    data2_updated = {"video_id": "vid2", "title": "Updated Title", "fetched_at": "2026-01-26T10:00:00"}
    file2.write_text(json.dumps(data2_updated, indent=2))

    # Check for changes
    result = service._filter_timestamp_only_changes()

    # Should preserve file2, restore file1
    assert result is True, "Should return True when at least one file has real changes"

    # Verify only file2 has changes
    diff_result = subprocess.run(["git", "diff", "--name-only"], cwd=git_repo, capture_output=True, text=True)
    assert "video1/metadata.json" not in diff_result.stdout, "Timestamp-only file should be restored"
    assert "video2/metadata.json" in diff_result.stdout, "Real changes should be preserved"


@pytest.mark.ai_generated
def test_filter_tsv_last_updated_column(git_repo: Path) -> None:
    """Test _filter_timestamp_only_changes handles TSV last_updated column."""
    service = GitAnnexService(git_repo)

    # Create and commit TSV file
    tsv_file = git_repo / "videos.tsv"
    initial_tsv = "title\tchannel\tlast_updated\tpath\nvideo1\tChannel A\t2026-01-01T00:00:00\tvideos/vid1\n"
    tsv_file.write_text(initial_tsv)

    subprocess.run(["git", "add", "videos.tsv"], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo, check=True, capture_output=True)

    # Modify only last_updated
    updated_tsv = "title\tchannel\tlast_updated\tpath\nvideo1\tChannel A\t2026-01-26T10:00:00\tvideos/vid1\n"
    tsv_file.write_text(updated_tsv)

    # Check for changes
    result = service._filter_timestamp_only_changes()

    # Should detect and restore timestamp-only TSV changes
    assert result is False, "Should return False after restoring timestamp-only TSV changes"

    # Verify file was restored
    diff_result = subprocess.run(["git", "diff", "--name-only"], cwd=git_repo, capture_output=True, text=True)
    assert diff_result.stdout.strip() == "", "TSV file should be restored with no changes"


@pytest.mark.ai_generated
def test_filter_playlist_last_modified(git_repo: Path) -> None:
    """Test _filter_timestamp_only_changes handles playlist last_modified field."""
    service = GitAnnexService(git_repo)

    # Create and commit playlist metadata
    playlist_file = git_repo / "playlists" / "PL123" / "metadata.json"
    playlist_file.parent.mkdir(parents=True)

    initial_data = {
        "playlist_id": "PL123",
        "title": "Test Playlist",
        "last_modified": "2026-01-01T00:00:00",
        "fetched_at": "2026-01-01T00:00:00"
    }
    playlist_file.write_text(json.dumps(initial_data, indent=2))

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_repo, check=True, capture_output=True)

    # Modify only timestamps
    updated_data = {
        "playlist_id": "PL123",
        "title": "Test Playlist",
        "last_modified": "2026-01-26T09:00:00",
        "fetched_at": "2026-01-26T10:00:00"
    }
    playlist_file.write_text(json.dumps(updated_data, indent=2))

    # Check for changes
    result = service._filter_timestamp_only_changes()

    # Should detect and restore timestamp-only changes
    assert result is False, "Should return False after restoring timestamp-only playlist changes"

    # Verify file was restored
    diff_result = subprocess.run(["git", "diff", "--name-only"], cwd=git_repo, capture_output=True, text=True)
    assert diff_result.stdout.strip() == "", "Playlist file should be restored with no changes"
