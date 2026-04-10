"""Contract tests for the collection CLI commands (add and backup).

Tests verify the CLI interface contract (options, arguments, exit codes,
output messages) by mocking the service layer.  No real YouTube, DataLad,
or git-annex operations are performed.

Covers:
  T023 - collection add
  T033 - collection backup
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from annextube.cli.__main__ import cli
from annextube.services.collection import ChannelResult

SERVICE_MODULE = "annextube.cli.collection"

runner = CliRunner()


# ---------------------------------------------------------------------------
# T023 - collection add
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
def test_add_requires_url() -> None:
    """Invoking 'collection add' without a URL must fail."""
    result = runner.invoke(cli, ["collection", "add"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stderr


@pytest.mark.ai_generated
def test_add_with_valid_url(tmp_path: object) -> None:
    """A successful add (mocked) must exit 0."""
    with patch(f"{SERVICE_MODULE}.add_channel") as mock_add:
        result = runner.invoke(
            cli,
            ["collection", "add", "https://www.youtube.com/@Test",
             "--output-dir", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output + result.stderr
    mock_add.assert_called_once()


@pytest.mark.ai_generated
def test_add_with_name_override(tmp_path: object) -> None:
    """--name value must be forwarded to add_channel."""
    with patch(f"{SERVICE_MODULE}.add_channel") as mock_add:
        result = runner.invoke(
            cli,
            ["collection", "add", "https://www.youtube.com/@Test",
             "--name", "custom-name",
             "--output-dir", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output + result.stderr
    mock_add.assert_called_once()
    _, kwargs = mock_add.call_args
    assert kwargs["name"] == "custom-name"


@pytest.mark.ai_generated
def test_add_with_no_backup(tmp_path: object) -> None:
    """--no-backup flag must be forwarded to add_channel."""
    with patch(f"{SERVICE_MODULE}.add_channel") as mock_add:
        result = runner.invoke(
            cli,
            ["collection", "add", "https://www.youtube.com/@Test",
             "--no-backup",
             "--output-dir", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output + result.stderr
    mock_add.assert_called_once()
    _, kwargs = mock_add.call_args
    assert kwargs["no_backup"] is True


@pytest.mark.ai_generated
def test_add_directory_conflict(tmp_path: object) -> None:
    """ValueError from add_channel must produce exit 1 and 'Error:' on stderr."""
    with patch(
        f"{SERVICE_MODULE}.add_channel",
        side_effect=ValueError("Directory already exists"),
    ):
        result = runner.invoke(
            cli,
            ["collection", "add", "https://www.youtube.com/@Test",
             "--output-dir", str(tmp_path)],
        )
    assert result.exit_code == 1
    assert "Error:" in result.stderr


@pytest.mark.ai_generated
def test_add_unrecognized_url(tmp_path: object) -> None:
    """ValueError for an unrecognised URL must produce exit 1."""
    with patch(
        f"{SERVICE_MODULE}.add_channel",
        side_effect=ValueError("Cannot extract handle"),
    ):
        result = runner.invoke(
            cli,
            ["collection", "add", "https://example.com/not-youtube",
             "--output-dir", str(tmp_path)],
        )
    assert result.exit_code == 1


@pytest.mark.ai_generated
def test_add_runtime_error(tmp_path: object) -> None:
    """RuntimeError from add_channel must produce exit 1."""
    with patch(
        f"{SERVICE_MODULE}.add_channel",
        side_effect=RuntimeError("init failed"),
    ):
        result = runner.invoke(
            cli,
            ["collection", "add", "https://www.youtube.com/@Test",
             "--output-dir", str(tmp_path)],
        )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# T033 - collection backup
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
def test_backup_default(tmp_path: object) -> None:
    """Two successful channels must exit 0."""
    results = [
        ChannelResult(name="chan-a", success=True, message="ok"),
        ChannelResult(name="chan-b", success=True, message="ok"),
    ]
    with patch(f"{SERVICE_MODULE}.backup_all", return_value=results):
        result = runner.invoke(
            cli, ["collection", "backup", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output + result.stderr


@pytest.mark.ai_generated
def test_backup_partial_failure(tmp_path: object) -> None:
    """One failure among results must produce exit 1."""
    results = [
        ChannelResult(name="chan-a", success=True, message="ok"),
        ChannelResult(name="chan-b", success=False, message="timeout"),
    ]
    with patch(f"{SERVICE_MODULE}.backup_all", return_value=results):
        result = runner.invoke(
            cli, ["collection", "backup", str(tmp_path)],
        )
    assert result.exit_code == 1


@pytest.mark.ai_generated
def test_backup_all_success(tmp_path: object) -> None:
    """All-success results must exit 0."""
    results = [
        ChannelResult(name="a", success=True),
        ChannelResult(name="b", success=True),
        ChannelResult(name="c", success=True),
    ]
    with patch(f"{SERVICE_MODULE}.backup_all", return_value=results):
        result = runner.invoke(
            cli, ["collection", "backup", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output + result.stderr


@pytest.mark.ai_generated
def test_backup_push_requires_save(tmp_path: object) -> None:
    """--push without --save must fail with exit 1 and a clear message."""
    result = runner.invoke(
        cli, ["collection", "backup", str(tmp_path), "--push"],
    )
    assert result.exit_code == 1
    assert "requires --save" in result.stderr


@pytest.mark.ai_generated
def test_backup_with_parallel(tmp_path: object) -> None:
    """--parallel value must be forwarded to backup_all."""
    results = [ChannelResult(name="ch", success=True)]
    with patch(f"{SERVICE_MODULE}.backup_all", return_value=results) as mock_ba:
        result = runner.invoke(
            cli,
            ["collection", "backup", str(tmp_path), "--parallel", "4"],
        )
    assert result.exit_code == 0, result.output + result.stderr
    mock_ba.assert_called_once()
    _, kwargs = mock_ba.call_args
    assert kwargs["parallel"] == 4


@pytest.mark.ai_generated
def test_backup_with_save_and_push(tmp_path: object) -> None:
    """--save --push must both be forwarded to backup_all."""
    results = [ChannelResult(name="ch", success=True)]
    with patch(f"{SERVICE_MODULE}.backup_all", return_value=results) as mock_ba:
        result = runner.invoke(
            cli,
            ["collection", "backup", str(tmp_path), "--save", "--push"],
        )
    assert result.exit_code == 0, result.output + result.stderr
    mock_ba.assert_called_once()
    _, kwargs = mock_ba.call_args
    assert kwargs["save"] is True
    assert kwargs["push"] is True


@pytest.mark.ai_generated
def test_backup_no_channels(tmp_path: object) -> None:
    """Empty channel list must exit 0 (nothing to fail)."""
    with patch(f"{SERVICE_MODULE}.backup_all", return_value=[]):
        result = runner.invoke(
            cli, ["collection", "backup", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output + result.stderr


@pytest.mark.ai_generated
def test_backup_runtime_error(tmp_path: object) -> None:
    """RuntimeError from backup_all must produce exit 1."""
    with patch(
        f"{SERVICE_MODULE}.backup_all",
        side_effect=RuntimeError("discover failed"),
    ):
        result = runner.invoke(
            cli, ["collection", "backup", str(tmp_path)],
        )
    assert result.exit_code == 1
