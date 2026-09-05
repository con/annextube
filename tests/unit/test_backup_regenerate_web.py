"""Wiring for ``annextube backup``'s web/ auto-regeneration.

Verifies that ``backup`` calls ``check_and_regenerate_web()`` according to
the ``--regenerate-web/--no-regenerate-web`` flag and the ``[web]
auto_regenerate`` config default, without exercising the real check.
"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from annextube.cli.__main__ import cli

runner = CliRunner()


def _make_archive_dir(tmp_path):
    config_dir = tmp_path / ".annextube"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        '[[sources]]\nurl = "https://www.youtube.com/@Test"\ntype = "channel"\nenabled = true\n'
    )
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "annex").mkdir()
    return tmp_path


def _mock_stats(videos: int = 5):
    return {
        "channel_url": "https://www.youtube.com/@Test",
        "videos_processed": videos,
        "videos_tracked": videos,
        "metadata_saved": videos,
        "captions_downloaded": 0,
        "errors": [],
        "warnings": [],
    }


def _run(tmp_path, extra_args, config_mock=None):
    archive = _make_archive_dir(tmp_path)

    with ExitStack() as stack:
        mock_discover = stack.enter_context(patch("annextube.cli.backup.discover_annextube"))
        MockArchiver = stack.enter_context(patch("annextube.cli.backup.Archiver"))
        stack.enter_context(patch("annextube.cli.backup.ExportService"))
        mock_regen = stack.enter_context(patch("annextube.cli.backup.check_and_regenerate_web"))
        if config_mock is not None:
            stack.enter_context(patch("annextube.cli.backup.load_config", return_value=config_mock))

        mock_info = MagicMock()
        mock_info.type = "single-channel"
        mock_discover.return_value = mock_info
        MockArchiver.return_value.backup_channel.return_value = _mock_stats()

        result = runner.invoke(
            cli,
            ["backup", "--output-dir", str(archive),
             "https://www.youtube.com/@Test", *extra_args],
        )

    return result, mock_regen


@pytest.mark.ai_generated
def test_regenerate_web_called_by_default(tmp_path):
    """With no flag and default [web] config, the check runs."""
    result, mock_regen = _run(tmp_path, [])
    assert result.exit_code == 0, result.output
    mock_regen.assert_called_once()


@pytest.mark.ai_generated
def test_no_regenerate_web_flag_skips_check(tmp_path):
    """--no-regenerate-web skips the check regardless of config."""
    result, mock_regen = _run(tmp_path, ["--no-regenerate-web"])
    assert result.exit_code == 0, result.output
    mock_regen.assert_not_called()


@pytest.mark.ai_generated
def test_regenerate_web_flag_forces_check_over_config(tmp_path):
    """--regenerate-web runs the check even if [web] auto_regenerate=false."""
    config = MagicMock()
    config.sources = []
    config.filters.limit = None
    config.search.enabled = False
    config.web.auto_regenerate = False
    config.user.yt_dlp_max_parallel = 1

    result, mock_regen = _run(tmp_path, ["--regenerate-web"], config_mock=config)
    assert result.exit_code == 0, result.output
    mock_regen.assert_called_once()


@pytest.mark.ai_generated
def test_config_auto_regenerate_false_skips_check_without_flag(tmp_path):
    """[web] auto_regenerate=false skips the check when no CLI flag is given."""
    config = MagicMock()
    config.sources = []
    config.filters.limit = None
    config.search.enabled = False
    config.web.auto_regenerate = False
    config.user.yt_dlp_max_parallel = 1

    result, mock_regen = _run(tmp_path, [], config_mock=config)
    assert result.exit_code == 0, result.output
    mock_regen.assert_not_called()
