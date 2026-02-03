"""Integration test for updating annexed files."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from annextube.lib.file_utils import AtomicFileWriter


@pytest.mark.ai_generated
def test_atomic_write_then_git_annex_add() -> None:
    """Test that atomic write + git annex add doesn't race.

    Reproduces the bug:
    1. Create annexed file
    2. Update with AtomicFileWriter
    3. Call git annex add

    Should not fail with "does not exist" or "changed while being added".
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Initialize git-annex repo
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "annex", "init"], cwd=tmpdir, check=True, capture_output=True)

        # Configure .gitattributes to annex .json files
        gitattributes = tmpdir / ".gitattributes"
        gitattributes.write_text("*.json annex.largefiles=anything\n")
        subprocess.run(["git", "add", ".gitattributes"], cwd=tmpdir, check=True)
        subprocess.run(["git", "commit", "-m", "Add .gitattributes"], cwd=tmpdir, check=True)

        # Create initial file
        test_file = tmpdir / "test.json"
        test_file.write_text('{"version": 1}')

        # Add to annex
        subprocess.run(["git", "annex", "add", str(test_file)], cwd=tmpdir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir, check=True)

        # Verify it's annexed
        assert test_file.is_symlink()

        # Update file with AtomicFileWriter (simulates our code)
        with AtomicFileWriter(test_file) as f:
            f.write('{"version": 2}')

        # File should now be a regular file, not symlink
        assert not test_file.is_symlink()
        assert test_file.read_text() == '{"version": 2}'

        # Now try to add with git annex (this is where the bug happens)
        result = subprocess.run(
            ["git", "annex", "add", str(test_file)],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        # Should succeed
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            pytest.fail(f"git annex add failed: {result.stderr}")

        # Commit
        subprocess.run(["git", "commit", "-m", "Updated"], cwd=tmpdir, check=True)

        # Verify file is still annexed
        assert test_file.is_symlink()


@pytest.mark.ai_generated
def test_multiple_files_update_race_condition() -> None:
    """Test updating multiple annexed files doesn't cause race condition.

    Simulates the real-world scenario where we update:
    - comments.json
    - captions.tsv
    - video.ru.vtt

    All in quick succession, then call git annex add.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Initialize
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "annex", "init"], cwd=tmpdir, check=True, capture_output=True)

        # Configure to annex .json and .vtt files
        gitattributes = tmpdir / ".gitattributes"
        gitattributes.write_text(
            "*.json annex.largefiles=anything\n"
            "*.vtt annex.largefiles=anything\n"
        )
        subprocess.run(["git", "add", ".gitattributes"], cwd=tmpdir, check=True)
        subprocess.run(["git", "commit", "-m", "Config"], cwd=tmpdir, check=True)

        # Create initial files
        video_dir = tmpdir / "video1"
        video_dir.mkdir()

        comments_file = video_dir / "comments.json"
        captions_tsv = video_dir / "captions.tsv"
        caption_vtt = video_dir / "video.ru.vtt"

        comments_file.write_text('[{"id": "1"}]')
        captions_tsv.write_text("lang\tfile\n")
        caption_vtt.write_text("WEBVTT\n")

        # Add and commit
        subprocess.run(["git", "annex", "add", "."], cwd=tmpdir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir, check=True)

        # Verify annexed (based on .gitattributes rules)
        # Note: .tsv files use default rule which may annex them if large enough
        assert comments_file.is_symlink()
        assert caption_vtt.is_symlink()

        # Update all files (simulating real backup scenario)
        with AtomicFileWriter(comments_file) as f:
            f.write('[{"id": "1"}, {"id": "2"}]')

        with AtomicFileWriter(captions_tsv) as f:
            f.write("lang\tfile\nru\tvideo.ru.vtt\n")

        with AtomicFileWriter(caption_vtt) as f:
            f.write("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTest")

        # All files are now regular files
        assert not comments_file.is_symlink()
        assert not caption_vtt.is_symlink()

        # Try to add all at once (this is where the bug happens in real code)
        result = subprocess.run(
            ["git", "annex", "add", "."],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            pytest.fail(f"git annex add failed with multiple files: {result.stderr}")

        # Commit
        subprocess.run(["git", "commit", "-m", "Updated"], cwd=tmpdir, check=True)

        # Verify files are annexed again
        assert comments_file.is_symlink()
        assert caption_vtt.is_symlink()
