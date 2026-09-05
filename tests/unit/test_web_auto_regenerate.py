"""Auto-regeneration of a stale web/ bundle (FR: auto-regenerate on version upgrade).

``check_and_regenerate_web()`` lets ``annextube backup`` keep an archive's
``web/`` UI in sync with the installed annextube version without a manual
``annextube generate-web --force`` after every upgrade.
"""

from unittest.mock import patch

import click
import pytest

from annextube.cli import generate_web


def _make_bundle(tmp_path, version: str | None):
    """Build a fake web/ with one built JS asset, optionally version-stamped."""
    assets = tmp_path / "web" / "assets"
    assets.mkdir(parents=True)
    content = f'console.log("app");const v="{version}";' if version else "console.log('app');"
    (assets / "index.js").write_text(content)
    return tmp_path / "web"


@pytest.mark.ai_generated
class TestExtractVersionFromBundle:
    def test_finds_bare_version_string(self, tmp_path):
        web_dir = _make_bundle(tmp_path, "0.13.0")
        assert generate_web._extract_version_from_bundle(web_dir) == "0.13.0"

    def test_strips_leading_v_prefix(self, tmp_path):
        web_dir = _make_bundle(tmp_path, "v0.13.0")
        assert generate_web._extract_version_from_bundle(web_dir) == "0.13.0"

    def test_none_when_no_assets_dir(self, tmp_path):
        web_dir = tmp_path / "web"
        web_dir.mkdir()
        assert generate_web._extract_version_from_bundle(web_dir) is None

    def test_none_when_no_version_like_string_present(self, tmp_path):
        assets = tmp_path / "web" / "assets"
        assets.mkdir(parents=True)
        (assets / "index.js").write_text("console.log('no version here');")
        assert generate_web._extract_version_from_bundle(tmp_path / "web") is None


@pytest.mark.ai_generated
class TestCheckAndRegenerateWeb:
    def test_false_when_web_dir_missing(self, tmp_path):
        assert generate_web.check_and_regenerate_web(tmp_path) is False

    def test_false_when_version_matches(self, tmp_path, monkeypatch):
        monkeypatch.setattr(generate_web, "__version__", "0.14.0")
        _make_bundle(tmp_path, "0.14.0")

        with patch.object(generate_web, "deploy_frontend") as mock_deploy:
            result = generate_web.check_and_regenerate_web(tmp_path)

        assert result is False
        mock_deploy.assert_not_called()

    def test_false_when_bundle_version_unknown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(generate_web, "__version__", "0.14.0")
        _make_bundle(tmp_path, None)

        with patch.object(generate_web, "deploy_frontend") as mock_deploy:
            result = generate_web.check_and_regenerate_web(tmp_path)

        assert result is False
        mock_deploy.assert_not_called()

    def test_regenerates_when_version_differs(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(generate_web, "__version__", "0.14.0")
        web_dir = _make_bundle(tmp_path, "0.13.0")

        with patch.object(generate_web, "deploy_frontend") as mock_deploy:
            result = generate_web.check_and_regenerate_web(tmp_path)

        assert result is True
        mock_deploy.assert_called_once_with(web_dir, quiet=False)
        out = capsys.readouterr().out
        assert "0.13.0" in out
        assert "0.14.0" in out

    def test_quiet_suppresses_stdout_and_forwards_to_deploy(self, tmp_path, monkeypatch, capsys):
        """quiet=True must not print to stdout (e.g. for `backup --json`)."""
        monkeypatch.setattr(generate_web, "__version__", "0.14.0")
        web_dir = _make_bundle(tmp_path, "0.13.0")

        with patch.object(generate_web, "deploy_frontend") as mock_deploy:
            result = generate_web.check_and_regenerate_web(tmp_path, quiet=True)

        assert result is True
        mock_deploy.assert_called_once_with(web_dir, quiet=True)
        assert capsys.readouterr().out == ""


@pytest.mark.ai_generated
class TestDeployFrontendQuiet:
    """``quiet=True`` must not write to stdout (e.g. for ``backup --json``)."""

    def _make_build(self, tmp_path):
        assets = tmp_path / "build" / "assets"
        assets.mkdir(parents=True)
        (assets / "index.js").write_text(
            f'const v="{generate_web.FRONTEND_VERSION_PLACEHOLDER}";'
        )
        return tmp_path / "build"

    def test_quiet_suppresses_success_message(self, tmp_path, monkeypatch, capsys):
        build_dir = self._make_build(tmp_path)
        monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", build_dir)
        monkeypatch.setattr(generate_web, "FRONTEND_SRC_DIR", tmp_path / "absent")
        web_dir = tmp_path / "web"

        generate_web.deploy_frontend(web_dir, quiet=True)

        assert capsys.readouterr().out == ""
        assert (web_dir / "assets" / "index.js").exists()

    def test_missing_build_error_is_quiet_on_stdout(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", tmp_path / "no-build")
        web_dir = tmp_path / "web"

        with pytest.raises(click.exceptions.Abort):
            generate_web.deploy_frontend(web_dir, quiet=True)

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Frontend build not found" in captured.err
