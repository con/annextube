"""Tests for error reporting utilities."""

import subprocess

import pytest

from annextube.lib.error_utils import format_subprocess_error


@pytest.mark.ai_generated
class TestFormatSubprocessError:
    """Tests for format_subprocess_error."""

    def test_regular_exception(self):
        """Regular exceptions return str(e)."""
        e = ValueError("something went wrong")
        assert format_subprocess_error(e) == "something went wrong"

    def test_called_process_error_no_output(self):
        """CalledProcessError without stdout/stderr."""
        e = subprocess.CalledProcessError(1, ["git", "commit"])
        result = format_subprocess_error(e)
        assert "git" in result
        assert "exit status 1" in result

    def test_called_process_error_with_stderr_str(self):
        """CalledProcessError with string stderr."""
        e = subprocess.CalledProcessError(
            128, ["git", "commit", "-m", "test"],
            output=None,
            stderr="fatal: not a git repository",
        )
        result = format_subprocess_error(e)
        assert "fatal: not a git repository" in result
        assert "stderr:" in result

    def test_called_process_error_with_stderr_bytes(self):
        """CalledProcessError with bytes stderr."""
        e = subprocess.CalledProcessError(
            128, ["git", "commit"],
            output=None,
            stderr=b"fatal: not a git repository\n",
        )
        result = format_subprocess_error(e)
        assert "fatal: not a git repository" in result
        assert "stderr:" in result

    def test_called_process_error_with_stdout_and_stderr(self):
        """CalledProcessError with both stdout and stderr."""
        e = subprocess.CalledProcessError(
            1, ["git", "add", "."],
            output="some stdout output",
            stderr="warning: something bad",
        )
        result = format_subprocess_error(e)
        assert "stdout: some stdout output" in result
        assert "stderr: warning: something bad" in result

    def test_called_process_error_empty_stderr(self):
        """CalledProcessError with empty stderr is omitted."""
        e = subprocess.CalledProcessError(
            1, ["git", "status"],
            output=None,
            stderr="",
        )
        result = format_subprocess_error(e)
        assert "stderr" not in result

    def test_called_process_error_whitespace_stderr(self):
        """CalledProcessError with whitespace-only stderr is omitted."""
        e = subprocess.CalledProcessError(
            1, ["git", "status"],
            output=None,
            stderr="   \n  ",
        )
        result = format_subprocess_error(e)
        assert "stderr" not in result

    def test_called_process_error_bytes_with_invalid_utf8(self):
        """CalledProcessError with invalid UTF-8 bytes uses replacement chars."""
        e = subprocess.CalledProcessError(
            1, ["git", "status"],
            output=None,
            stderr=b"error: \xff\xfe bad encoding",
        )
        result = format_subprocess_error(e)
        assert "stderr:" in result
        # Should not raise, replacement chars are used
        assert "bad encoding" in result
