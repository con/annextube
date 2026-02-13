"""Test timestamp filtering for channel.json files."""

import json
import subprocess

import pytest

from annextube.services.git_annex import GitAnnexService


@pytest.mark.ai_generated
def test_channel_json_timestamp_only_changes_not_committed(tmp_path):
    """Test that channel.json with only timestamp changes doesn't create commits."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo("Test repo")

    # Configure gitattributes so channel.json goes to git, not annex
    git_annex.configure_gitattributes()

    # Create initial channel.json
    channel_json = tmp_path / "channel.json"
    initial_data = {
        "channel_id": "UC_TEST_ID",
        "name": "Test Channel",
        "description": "Test description",
        "video_count": 10,
        "last_sync": "2026-02-09T19:00:00.000000",
        "fetched_at": "2026-02-09T19:00:00.000000",
        "archive_stats": {
            "total_videos_archived": 10,
        }
    }
    with open(channel_json, 'w') as f:
        json.dump(initial_data, f, indent=2)

    # Commit initial version
    result = git_annex.add_and_commit("Initial channel.json")
    assert result is True  # Should commit

    # Get initial commit count
    initial_commits = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()

    # Update only timestamps
    updated_data = initial_data.copy()
    updated_data["last_sync"] = "2026-02-09T20:00:00.000000"
    updated_data["fetched_at"] = "2026-02-09T20:00:00.000000"

    with open(channel_json, 'w') as f:
        json.dump(updated_data, f, indent=2)

    # Try to commit - should be filtered out
    result = git_annex.add_and_commit("Update channel.json timestamps")
    assert result is False  # Should NOT commit (timestamp-only changes)

    # Verify no new commit was created
    final_commits = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()

    assert initial_commits == final_commits  # No new commits

    # Verify file was restored to original state
    with open(channel_json) as f:
        current_data = json.load(f)

    assert current_data == initial_data  # Timestamps reverted


@pytest.mark.ai_generated
def test_channel_json_real_changes_are_committed(tmp_path):
    """Test that channel.json with real changes (not just timestamps) is committed."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo("Test repo")
    git_annex.configure_gitattributes()

    # Create initial channel.json
    channel_json = tmp_path / "channel.json"
    initial_data = {
        "channel_id": "UC_TEST_ID",
        "name": "Test Channel",
        "video_count": 10,
        "last_sync": "2026-02-09T19:00:00.000000",
        "fetched_at": "2026-02-09T19:00:00.000000",
    }
    with open(channel_json, 'w') as f:
        json.dump(initial_data, f, indent=2)

    # Commit initial version
    git_annex.add_and_commit("Initial channel.json")

    # Get initial commit count
    initial_commits = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()

    # Update with real change + timestamps
    updated_data = initial_data.copy()
    updated_data["video_count"] = 15  # Real change
    updated_data["last_sync"] = "2026-02-09T20:00:00.000000"
    updated_data["fetched_at"] = "2026-02-09T20:00:00.000000"

    with open(channel_json, 'w') as f:
        json.dump(updated_data, f, indent=2)

    # Try to commit - should succeed (has real changes)
    result = git_annex.add_and_commit("Update video count")
    assert result is True  # Should commit

    # Verify new commit was created
    final_commits = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()

    assert int(final_commits) == int(initial_commits) + 1  # One new commit

    # Verify file has updated content
    with open(channel_json) as f:
        current_data = json.load(f)

    assert current_data["video_count"] == 15


@pytest.mark.ai_generated
def test_multiple_timestamp_fields_filtered(tmp_path):
    """Test that all timestamp fields (last_sync, fetched_at) are filtered together."""
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo("Test repo")
    git_annex.configure_gitattributes()

    channel_json = tmp_path / "channel.json"
    initial_data = {
        "channel_id": "UC_TEST_ID",
        "last_sync": "2026-02-09T19:00:00.000000",
        "fetched_at": "2026-02-09T19:00:00.000000",
        "last_modified": "2026-02-09T19:00:00.000000",  # Another timestamp field
    }
    with open(channel_json, 'w') as f:
        json.dump(initial_data, f, indent=2)

    git_annex.add_and_commit("Initial")

    # Update ALL timestamp fields
    updated_data = initial_data.copy()
    updated_data["last_sync"] = "2026-02-09T20:00:00.000000"
    updated_data["fetched_at"] = "2026-02-09T20:00:00.000000"
    updated_data["last_modified"] = "2026-02-09T20:00:00.000000"

    with open(channel_json, 'w') as f:
        json.dump(updated_data, f, indent=2)

    # Should not commit (all changes are timestamps)
    result = git_annex.add_and_commit("Update all timestamps")
    assert result is False

    # Verify file was restored
    with open(channel_json) as f:
        current_data = json.load(f)

    assert current_data == initial_data
