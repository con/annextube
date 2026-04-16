"""Contract tests for backup command JSON output mode (T030).

Tests verify the --json flag produces structured JSON output matching
the CLI contract specification (cli-contract.md).  The archiver service
layer is mocked so no real YouTube or git-annex operations occur.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from annextube.cli.__main__ import cli

runner = CliRunner()


def _extract_json(output: str) -> dict:
    """Extract the JSON result object from CLI output.

    The output may contain JSON log lines (one per line) before the final
    JSON result.  The result is the last top-level JSON object — one whose
    opening '{' starts at the very beginning of a line (column 0, no indent).
    """
    lines = output.rstrip().split("\n")
    # Find last '}' at column 0 (end of top-level object)
    end_idx = len(lines) - 1
    while end_idx >= 0 and lines[end_idx] != "}":
        end_idx -= 1
    if end_idx < 0:
        raise ValueError(f"No JSON object found in output:\n{output}")
    # Find matching '{' at column 0
    start_idx = end_idx - 1
    while start_idx >= 0 and lines[start_idx] != "{":
        start_idx -= 1
    if start_idx < 0:
        raise ValueError(f"No JSON object start found in output:\n{output}")
    json_text = "\n".join(lines[start_idx:end_idx + 1])
    return json.loads(json_text)


def _make_archive_dir(tmp_path):
    """Create minimal annextube archive directory structure."""
    config_dir = tmp_path / ".annextube"
    config_dir.mkdir()
    config_toml = config_dir / "config.toml"
    config_toml.write_text(
        '[[sources]]\nurl = "https://www.youtube.com/@Test"\ntype = "channel"\nenabled = true\n'
    )
    # Minimal git repo for archive discovery
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "annex").mkdir()
    return tmp_path


def _mock_stats(videos: int = 5, errors: list | None = None, warnings: list | None = None):
    """Build a stats dict like Archiver.backup_channel returns."""
    return {
        "channel_url": "https://www.youtube.com/@Test",
        "videos_processed": videos,
        "videos_tracked": videos,
        "metadata_saved": videos,
        "captions_downloaded": videos * 2,
        "errors": errors or [],
        "warnings": warnings or [],
    }


@pytest.mark.ai_generated
def test_backup_json_success(tmp_path):
    """--json flag produces valid JSON with 'success' status on clean backup."""
    archive = _make_archive_dir(tmp_path)

    with (
        patch("annextube.cli.backup.discover_annextube") as mock_discover,
        patch("annextube.cli.backup.Archiver") as MockArchiver,
        patch("annextube.cli.backup.ExportService"),
    ):
        mock_info = MagicMock()
        mock_info.type = "single-channel"
        mock_discover.return_value = mock_info

        archiver_instance = MockArchiver.return_value
        archiver_instance.backup_channel.return_value = _mock_stats(5)

        result = runner.invoke(
            cli,
            ["--json", "backup", "--output-dir", str(archive),
             "https://www.youtube.com/@Test"],
        )

    assert result.exit_code == 0, f"stderr: {result.stderr}\noutput: {result.output}"
    data = _extract_json(result.output)
    assert data["status"] == "success"
    assert data["command"] == "backup"
    assert "timestamp" in data
    assert data["sources_processed"] == 1
    assert len(data["sources"]) == 1
    assert data["sources"][0]["url"] == "https://www.youtube.com/@Test"
    assert data["sources"][0]["type"] == "channel"
    assert data["sources"][0]["videos_tracked"] == 5
    assert data["summary"]["videos_tracked"] == 5
    assert data["summary"]["captions_downloaded"] == 10
    assert "duration_seconds" in data["summary"]


@pytest.mark.ai_generated
def test_backup_json_with_errors(tmp_path):
    """--json flag includes errors list and 'error' status when backup has errors."""
    archive = _make_archive_dir(tmp_path)

    with (
        patch("annextube.cli.backup.discover_annextube") as mock_discover,
        patch("annextube.cli.backup.Archiver") as MockArchiver,
        patch("annextube.cli.backup.ExportService"),
    ):
        mock_info = MagicMock()
        mock_info.type = "single-channel"
        mock_discover.return_value = mock_info

        archiver_instance = MockArchiver.return_value
        archiver_instance.backup_channel.return_value = _mock_stats(
            3, errors=["Failed to fetch video xyz"]
        )

        result = runner.invoke(
            cli,
            ["--json", "backup", "--output-dir", str(archive),
             "https://www.youtube.com/@Test"],
        )

    # Exit code 1 for errors
    assert result.exit_code == 1
    data = _extract_json(result.output)
    assert data["status"] == "error"
    assert "errors" in data
    assert len(data["errors"]) == 1
    assert "xyz" in data["errors"][0]


@pytest.mark.ai_generated
def test_backup_json_config_mode(tmp_path):
    """--json works with config-based multi-source backup."""
    archive = _make_archive_dir(tmp_path)

    with (
        patch("annextube.cli.backup.discover_annextube") as mock_discover,
        patch("annextube.cli.backup.Archiver") as MockArchiver,
        patch("annextube.cli.backup.load_config") as mock_config,
        patch("annextube.cli.backup.ExportService"),
    ):
        mock_info = MagicMock()
        mock_info.type = "single-channel"
        mock_discover.return_value = mock_info

        # Configure two sources
        source1 = MagicMock()
        source1.url = "https://www.youtube.com/@Channel1"
        source1.type = "channel"
        source1.enabled = True

        source2 = MagicMock()
        source2.url = "https://www.youtube.com/playlist?list=PLxxx"
        source2.type = "playlist"
        source2.enabled = True

        config = MagicMock()
        config.sources = [source1, source2]
        config.filters.limit = None
        config.search.enabled = False
        config.user.yt_dlp_max_parallel = 1
        mock_config.return_value = config

        archiver_instance = MockArchiver.return_value
        archiver_instance.backup_channel.return_value = _mock_stats(10)
        archiver_instance.backup_playlist.return_value = _mock_stats(3)

        result = runner.invoke(
            cli,
            ["--json", "backup", "--output-dir", str(archive)],
        )

    assert result.exit_code == 0, f"stderr: {result.stderr}\noutput: {result.output}"
    data = _extract_json(result.output)
    assert data["status"] == "success"
    assert data["sources_processed"] == 2
    assert len(data["sources"]) == 2
    assert data["sources"][0]["type"] == "channel"
    assert data["sources"][1]["type"] == "playlist"
    assert data["summary"]["videos_tracked"] == 13


@pytest.mark.ai_generated
def test_backup_json_not_archive(tmp_path):
    """--json outputs structured error when directory is not an archive."""
    with patch("annextube.cli.backup.discover_annextube", return_value=None):
        result = runner.invoke(
            cli,
            ["--json", "backup", "--output-dir", str(tmp_path),
             "https://www.youtube.com/@Test"],
        )

    assert result.exit_code != 0
    data = _extract_json(result.output)
    assert data["status"] == "error"
    assert data["error"]["code"] == 4
    assert "not an annextube archive" in data["error"]["message"]


@pytest.mark.ai_generated
def test_backup_no_json_flag_gives_human_readable(tmp_path):
    """Without --json, backup outputs human-readable text (no JSON)."""
    archive = _make_archive_dir(tmp_path)

    with (
        patch("annextube.cli.backup.discover_annextube") as mock_discover,
        patch("annextube.cli.backup.Archiver") as MockArchiver,
        patch("annextube.cli.backup.ExportService"),
    ):
        mock_info = MagicMock()
        mock_info.type = "single-channel"
        mock_discover.return_value = mock_info

        archiver_instance = MockArchiver.return_value
        archiver_instance.backup_channel.return_value = _mock_stats(5)

        result = runner.invoke(
            cli,
            ["backup", "--output-dir", str(archive),
             "https://www.youtube.com/@Test"],
        )

    assert result.exit_code == 0
    # Should contain human-readable output, not JSON
    assert "[ok] Backup complete!" in result.output
    # Should not be parseable as a single JSON object
    try:
        json.loads(result.output)
        pytest.fail("Output should not be valid JSON in non-JSON mode")
    except json.JSONDecodeError:
        pass  # Expected
