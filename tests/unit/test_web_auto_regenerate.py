"""Auto-regeneration of a stale web/ bundle (FR: auto-regenerate on version upgrade).

``check_and_regenerate_web()`` lets ``annextube backup`` keep an archive's
``web/`` UI in sync with the installed annextube version without a manual
``annextube generate-web --force`` after every upgrade.
"""

from unittest.mock import patch

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
        mock_deploy.assert_called_once_with(web_dir)
        out = capsys.readouterr().out
        assert "0.13.0" in out
        assert "0.14.0" in out
