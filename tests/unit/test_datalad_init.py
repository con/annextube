"""Unit tests for DataLad dataset initialization."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_has_datalad = importlib.util.find_spec("datalad") is not None


@pytest.mark.ai_generated
def test_datalad_init_flag_creates_dataset(tmp_path: Path):
    """Test that --datalad flag creates a DataLad dataset."""
    if not _has_datalad:
        pytest.skip("DataLad not installed (optional dependency)")

    repo_path = tmp_path / "datalad-archive"

    # Initialize with --datalad flag
    result = subprocess.run(
        [
            sys.executable, "-m", "annextube", "init",
            str(repo_path),
            "--datalad",
            "--no-videos",
            "--comments-depth", "0",
            "--no-captions",
            "--no-thumbnails",
        ],
        capture_output=True,
        text=True,
    )

    # Check that init succeeded
    assert result.returncode == 0, f"Init failed: {result.stderr}"
    assert "DataLad dataset" in result.stdout

    # Verify DataLad-specific files exist
    assert (repo_path / ".datalad").exists(), ".datalad directory should exist"
    assert (repo_path / ".datalad" / "config").exists(), ".datalad/config should exist"

    # Verify git-annex was initialized
    assert (repo_path / ".git").exists(), ".git directory should exist"
    assert (repo_path / ".git" / "annex").exists(), ".git/annex directory should exist"

    # Verify .gitattributes was configured
    assert (repo_path / ".gitattributes").exists(), ".gitattributes should exist"
    gitattributes_content = (repo_path / ".gitattributes").read_text()
    assert "annextube file tracking configuration" in gitattributes_content

    # Verify .annextube config was created
    assert (repo_path / ".annextube").exists(), ".annextube directory should exist"
    assert (repo_path / ".annextube" / "config.toml").exists(), "config.toml should exist"


@pytest.mark.ai_generated
def test_datalad_init_without_datalad_installed_fails(tmp_path: Path):
    """Test that --datalad flag fails gracefully when DataLad is not installed."""
    # This test can only run if DataLad is NOT installed
    if _has_datalad:
        pytest.skip("DataLad is installed, cannot test failure case")

    repo_path = tmp_path / "datalad-archive"

    # Try to initialize with --datalad flag (should fail)
    # Use sys.executable to stay within the same venv as the test process
    # (uv run would use the project .venv which may have datalad installed)
    result = subprocess.run(
        [
            sys.executable, "-m", "annextube", "init",
            str(repo_path),
            "--datalad",
        ],
        capture_output=True,
        text=True,
    )

    # Should fail with ImportError
    assert result.returncode != 0
    assert "DataLad is not installed" in result.stderr or "ImportError" in result.stderr


@pytest.mark.ai_generated
def test_datalad_flag_with_source_url(tmp_path: Path):
    """Test that --datalad flag works with source URLs."""
    if not _has_datalad:
        pytest.skip("DataLad not installed (optional dependency)")

    repo_path = tmp_path / "datalad-archive"

    # Initialize with --datalad flag and source URL
    result = subprocess.run(
        [
            sys.executable, "-m", "annextube", "init",
            str(repo_path),
            "https://www.youtube.com/@AnnexTubeTesting",
            "--datalad",
            "--no-videos",
            "--comments-depth", "0",
            "--no-captions",
            "--no-thumbnails",
            "--limit", "1",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Init failed: {result.stderr}"
    assert "DataLad dataset" in result.stdout

    # Verify config contains the source URL
    config_content = (repo_path / ".annextube" / "config.toml").read_text()
    assert "youtube.com/@AnnexTubeTesting" in config_content
