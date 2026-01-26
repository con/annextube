"""Integration test for incremental backup functionality."""

import tempfile
from pathlib import Path
import subprocess
import pytest


@pytest.mark.ai_generated
def test_incremental_backup_no_reprocessing():
    """Test that running backup twice doesn't reprocess existing videos.

    This test verifies that the incremental update mode correctly identifies
    and skips already-downloaded videos, ensuring efficiency.
    """
    # Use a small, stable test channel (Lex Fridman has many videos)
    test_channel = "https://www.youtube.com/@lexfridman"
    limit = 3  # Just 3 videos for fast testing

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize repository
        result = subprocess.run(
            ["uv", "run", "annextube", "init", str(repo_path), test_channel,
             "--no-videos", "--comments", "0", "--no-captions"],
            capture_output=True,
            text=True,
            check=True
        )
        assert "Initialized YouTube archive" in result.stdout
        assert test_channel in result.stdout

        # First backup - should process videos
        result1 = subprocess.run(
            ["uv", "run", "annextube", "backup",
             "--output-dir", str(repo_path),
             "--limit", str(limit)],
            capture_output=True,
            text=True,
            check=True
        )

        # Verify videos were processed
        assert "videos processed" in result1.stdout.lower() or "Processing video" in result1.stderr

        # Check that videos.tsv was created and has entries
        videos_tsv = repo_path / "videos" / "videos.tsv"
        assert videos_tsv.exists(), "videos.tsv should be created after first backup"

        with open(videos_tsv) as f:
            lines = f.readlines()
            # Should have header + 3 video entries
            assert len(lines) >= 4, f"Expected at least 4 lines (header + 3 videos), got {len(lines)}"

        # Second backup - should NOT reprocess any videos
        result2 = subprocess.run(
            ["uv", "run", "annextube", "backup",
             "--output-dir", str(repo_path),
             "--limit", str(limit)],
            capture_output=True,
            text=True,
            check=True
        )

        # Verify incremental mode was used
        assert "videos-incremental" in result2.stdout, "Should use incremental mode by default"

        # Verify videos were filtered out
        stderr_lower = result2.stderr.lower()
        assert ("filtered out" in stderr_lower or
                "skipping existing video" in stderr_lower or
                "0 video(s) in channel" in stderr_lower), \
            "Second run should filter out existing videos"

        # Verify no new videos were processed (all filtered)
        # The output should show 0 videos processed or similar
        stdout_lower = result2.stdout.lower()

        # Check for indicators that nothing was processed
        # This could be "0 videos processed" or no "processing video" messages
        processing_msgs = result2.stderr.count("Processing video")
        assert processing_msgs == 0, \
            f"Second run should not process any videos, but found {processing_msgs} processing messages"


@pytest.mark.ai_generated
def test_incremental_backup_detects_new_videos():
    """Test that incremental backup correctly detects and fetches new videos.

    This test uses a larger limit on the second run to simulate new videos
    being available.
    """
    test_channel = "https://www.youtube.com/@lexfridman"

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize repository
        subprocess.run(
            ["uv", "run", "annextube", "init", str(repo_path), test_channel,
             "--no-videos", "--comments", "0", "--no-captions"],
            check=True,
            capture_output=True
        )

        # First backup - get 2 videos
        subprocess.run(
            ["uv", "run", "annextube", "backup",
             "--output-dir", str(repo_path),
             "--limit", "2"],
            check=True,
            capture_output=True
        )

        # Verify 2 videos in TSV
        videos_tsv = repo_path / "videos" / "videos.tsv"
        with open(videos_tsv) as f:
            first_count = len(f.readlines()) - 1  # Exclude header
        assert first_count == 2, f"Expected 2 videos after first backup, got {first_count}"

        # Second backup - increase limit to 5 (simulates 3 "new" videos)
        result = subprocess.run(
            ["uv", "run", "annextube", "backup",
             "--output-dir", str(repo_path),
             "--limit", "5"],
            capture_output=True,
            text=True,
            check=True
        )

        # Verify incremental mode detected and processed new videos
        assert "videos-incremental" in result.stdout

        # Verify 5 videos total in TSV now
        with open(videos_tsv) as f:
            second_count = len(f.readlines()) - 1
        assert second_count == 5, f"Expected 5 videos after second backup, got {second_count}"

        # Should have processed 3 new videos (5 - 2)
        # The exact message format may vary, but there should be indication of new videos
        stderr_text = result.stderr
        assert "Filtered out 2" in stderr_text or "existing videos" in stderr_text, \
            "Should indicate 2 existing videos were filtered out"
