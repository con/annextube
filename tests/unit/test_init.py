"""Unit tests for init command -- curation, search, and enable-all flags."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from annextube.lib.config import generate_config_template


# ── Config template generation tests ──────────────────────────────────────


@pytest.mark.ai_generated
class TestGenerateConfigTemplateCurationSearch:
    """Test that enable_curation / enable_search toggle [curation] and [search] sections."""

    def test_default_curation_disabled(self) -> None:
        """By default, curation is commented out."""
        template = generate_config_template()
        assert "# enabled = true              # Auto-curate" in template

    def test_default_search_disabled(self) -> None:
        """By default, search is commented out."""
        template = generate_config_template()
        assert "# enabled = true  # Uncomment to auto-build" in template

    def test_curation_enabled(self) -> None:
        """enable_curation=True uncomments the curation enabled line."""
        template = generate_config_template(enable_curation=True)
        assert "enabled = true              # Auto-curate captions during backup" in template
        # Should NOT have the commented-out version
        assert "# enabled = true              # Auto-curate" not in template

    def test_search_enabled(self) -> None:
        """enable_search=True uncomments the search enabled line."""
        template = generate_config_template(enable_search=True)
        assert "enabled = true  # Auto-build search index after backup" in template
        assert "# enabled = true  # Uncomment to auto-build" not in template

    def test_both_enabled(self) -> None:
        """Both can be enabled simultaneously."""
        template = generate_config_template(enable_curation=True, enable_search=True)
        assert "enabled = true              # Auto-curate captions during backup" in template
        assert "enabled = true  # Auto-build search index after backup" in template

    def test_curation_enabled_search_disabled(self) -> None:
        """Enabling one doesn't affect the other."""
        template = generate_config_template(enable_curation=True, enable_search=False)
        assert "enabled = true              # Auto-curate captions during backup" in template
        assert "# enabled = true  # Uncomment to auto-build" in template


# ── CLI init flag wiring tests ────────────────────────────────────────────


@pytest.mark.ai_generated
class TestInitCLIFlags:
    """Test that --curation, --search, and --enable-all CLI flags produce correct config."""

    @staticmethod
    def _run_init(tmp_path: Path, *extra_args: str) -> Path:
        """Run annextube init and return the archive path."""
        repo_path = tmp_path / "archive"
        result = subprocess.run(
            [
                sys.executable, "-m", "annextube", "init",
                str(repo_path),
                "--no-videos", "--comments-depth", "0",
                "--no-captions", "--no-thumbnails",
                *extra_args,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Init failed: {result.stderr}"
        return repo_path

    def test_default_no_curation_no_search(self, tmp_path: Path) -> None:
        """Default init leaves curation and search commented out."""
        repo_path = self._run_init(tmp_path)
        config = (repo_path / ".annextube" / "config.toml").read_text()
        assert "# enabled = true              # Auto-curate" in config
        assert "# enabled = true  # Uncomment to auto-build" in config

    def test_curation_flag(self, tmp_path: Path) -> None:
        """--curation enables curation in generated config."""
        repo_path = self._run_init(tmp_path, "--curation")
        config = (repo_path / ".annextube" / "config.toml").read_text()
        assert "enabled = true              # Auto-curate captions during backup" in config
        # search should still be disabled
        assert "# enabled = true  # Uncomment to auto-build" in config

    def test_search_flag(self, tmp_path: Path) -> None:
        """--search enables search in generated config."""
        repo_path = self._run_init(tmp_path, "--search")
        config = (repo_path / ".annextube" / "config.toml").read_text()
        assert "enabled = true  # Auto-build search index after backup" in config
        # curation should still be disabled
        assert "# enabled = true              # Auto-curate" in config

    def test_enable_all_flag(self, tmp_path: Path) -> None:
        """--enable-all enables both curation and search."""
        repo_path = self._run_init(tmp_path, "--enable-all")
        config = (repo_path / ".annextube" / "config.toml").read_text()
        assert "enabled = true              # Auto-curate captions during backup" in config
        assert "enabled = true  # Auto-build search index after backup" in config

    def test_enable_all_output_mentions_features(self, tmp_path: Path) -> None:
        """--enable-all shows enabled features in CLI output."""
        repo_path = tmp_path / "archive"
        result = subprocess.run(
            [
                sys.executable, "-m", "annextube", "init",
                str(repo_path),
                "--no-videos", "--comments-depth", "0",
                "--no-captions", "--no-thumbnails",
                "--enable-all",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Init failed: {result.stderr}"
        assert "Curation: enabled" in result.stdout
        assert "Search index: enabled" in result.stdout

    def test_no_curation_flag(self, tmp_path: Path) -> None:
        """--no-curation explicitly disables curation (same as default)."""
        repo_path = self._run_init(tmp_path, "--no-curation")
        config = (repo_path / ".annextube" / "config.toml").read_text()
        assert "# enabled = true              # Auto-curate" in config
