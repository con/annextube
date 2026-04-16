"""Unit tests for shell completion command (T141, FR-057i)."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from annextube.cli.__main__ import cli
from annextube.cli.completion import _detect_shell

runner = CliRunner()


@pytest.mark.ai_generated
def test_completion_bash_outputs_script() -> None:
    """annextube completion bash outputs a bash completion script."""
    result = runner.invoke(cli, ["completion", "bash"])
    assert result.exit_code == 0, result.output
    assert "_annextube_completion" in result.output
    assert "COMP_WORDS" in result.output


@pytest.mark.ai_generated
def test_completion_zsh_outputs_script() -> None:
    """annextube completion zsh outputs a zsh completion script."""
    result = runner.invoke(cli, ["completion", "zsh"])
    assert result.exit_code == 0, result.output
    assert "_annextube_completion" in result.output


@pytest.mark.ai_generated
def test_completion_fish_outputs_script() -> None:
    """annextube completion fish outputs a fish completion script."""
    result = runner.invoke(cli, ["completion", "fish"])
    assert result.exit_code == 0, result.output
    assert "annextube" in result.output
    assert "complete" in result.output


@pytest.mark.ai_generated
def test_completion_autodetect_bash() -> None:
    """Without argument, detects shell from $SHELL."""
    with patch.dict("os.environ", {"SHELL": "/bin/bash"}):
        result = runner.invoke(cli, ["completion"])
    assert result.exit_code == 0, result.output
    assert "_annextube_completion" in result.output
    assert "COMP_WORDS" in result.output


@pytest.mark.ai_generated
def test_completion_autodetect_zsh() -> None:
    """Without argument, detects zsh from $SHELL."""
    with patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"}):
        result = runner.invoke(cli, ["completion"])
    assert result.exit_code == 0, result.output
    assert "_annextube_completion" in result.output


@pytest.mark.ai_generated
def test_completion_autodetect_unknown_shell() -> None:
    """Unknown $SHELL produces an error."""
    with patch.dict("os.environ", {"SHELL": "/bin/csh"}):
        result = runner.invoke(cli, ["completion"])
    assert result.exit_code != 0
    assert "Could not detect shell" in result.output


@pytest.mark.ai_generated
def test_completion_invalid_shell_argument() -> None:
    """Invalid shell name is rejected by Click's Choice."""
    result = runner.invoke(cli, ["completion", "powershell"])
    assert result.exit_code != 0


@pytest.mark.ai_generated
def test_detect_shell_bash() -> None:
    """_detect_shell returns 'bash' for /bin/bash."""
    with patch.dict("os.environ", {"SHELL": "/bin/bash"}):
        assert _detect_shell() == "bash"


@pytest.mark.ai_generated
def test_detect_shell_zsh() -> None:
    """_detect_shell returns 'zsh' for /usr/bin/zsh."""
    with patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"}):
        assert _detect_shell() == "zsh"


@pytest.mark.ai_generated
def test_detect_shell_fish() -> None:
    """_detect_shell returns 'fish' for /usr/bin/fish."""
    with patch.dict("os.environ", {"SHELL": "/usr/bin/fish"}):
        assert _detect_shell() == "fish"


@pytest.mark.ai_generated
def test_detect_shell_none() -> None:
    """_detect_shell returns None when $SHELL is unset."""
    with patch.dict("os.environ", {}, clear=True):
        assert _detect_shell() is None
