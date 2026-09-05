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
    """Build a fake web/ stamped with the given deployed version.

    Mirrors what ``deploy_frontend()`` actually leaves behind: a JS asset
    (content irrelevant to version detection -- the version comes from the
    ``_VERSION_MARKER_FILENAME`` sidecar file, not from parsing the bundle)
    plus that marker file, unless ``version`` is None (simulating a web/
    deployed by an annextube version that predates the marker file).
    """
    assets = tmp_path / "web" / "assets"
    assets.mkdir(parents=True)
    (assets / "index.js").write_text("console.log('app');")
    if version is not None:
        (tmp_path / "web" / generate_web._VERSION_MARKER_FILENAME).write_text(version + "\n")
    return tmp_path / "web"


@pytest.mark.ai_generated
class TestReadDeployedVersion:
    @pytest.mark.parametrize(
        "version",
        [
            "0.13.0",
            # hatch-vcs PEP 440 local versions, e.g. tagged...
            "0.2.0.post1+gc6bd677.d20260905",
            # ...and its untagged-checkout fallback shape (shorter base).
            "0.0.post101+gdcfbbeec1.d20260905",
        ],
    )
    def test_finds_stamped_version(self, tmp_path, version):
        web_dir = _make_bundle(tmp_path, version)
        assert generate_web._read_deployed_version(web_dir) == version

    def test_ignores_unrelated_version_looking_strings_in_the_bundle(self, tmp_path):
        """A bundled dependency's own quoted version string (e.g. from a
        third-party JS library) must not be mistaken for annextube's --
        only the marker file deploy_frontend() stamps is authoritative.
        """
        web_dir = _make_bundle(tmp_path, "0.14.0")
        (web_dir / "assets" / "index.js").write_text('const libVersion="7.1.0";')
        assert generate_web._read_deployed_version(web_dir) == "0.14.0"

    def test_none_when_no_marker_file(self, tmp_path):
        """A web/ deployed by an annextube version older than the marker file."""
        web_dir = _make_bundle(tmp_path, None)
        assert generate_web._read_deployed_version(web_dir) is None


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

    def test_regenerates_once_when_marker_missing(self, tmp_path, monkeypatch, capsys):
        """A web/ deployed before this feature existed has no marker at all.

        It must regenerate once (which then stamps the marker) rather than
        never auto-upgrading -- otherwise every archive that already had a
        web/ before upgrading annextube would never benefit from this
        feature until someone ran `generate-web --force` by hand.
        """
        monkeypatch.setattr(generate_web, "__version__", "0.14.0")
        web_dir = _make_bundle(tmp_path, None)

        with patch.object(generate_web, "deploy_frontend") as mock_deploy:
            result = generate_web.check_and_regenerate_web(tmp_path)

        assert result is True
        mock_deploy.assert_called_once_with(web_dir, quiet=False)
        assert "0.14.0" in capsys.readouterr().out

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

    def test_stamps_version_marker(self, tmp_path, monkeypatch):
        """deploy_frontend() must stamp the marker _read_deployed_version()
        later reads back -- otherwise check_and_regenerate_web() can never
        detect that this bundle is up to date.
        """
        build_dir = self._make_build(tmp_path)
        monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", build_dir)
        monkeypatch.setattr(generate_web, "FRONTEND_SRC_DIR", tmp_path / "absent")
        monkeypatch.setattr(generate_web, "__version__", "0.14.0")
        web_dir = tmp_path / "web"

        generate_web.deploy_frontend(web_dir, quiet=True)

        assert generate_web._read_deployed_version(web_dir) == "0.14.0"

    def test_no_marker_when_placeholder_injection_fails(self, tmp_path, monkeypatch):
        """If the placeholder isn't found (e.g. a future build drift), the
        bundle doesn't actually show __version__ -- so the marker must NOT
        be stamped, or check_and_regenerate_web() would wrongly consider
        this deploy up to date forever instead of retrying next time.
        """
        assets = tmp_path / "build" / "assets"
        assets.mkdir(parents=True)
        (assets / "index.js").write_text("console.log('no placeholder here');")
        monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", tmp_path / "build")
        monkeypatch.setattr(generate_web, "FRONTEND_SRC_DIR", tmp_path / "absent")
        web_dir = tmp_path / "web"

        generate_web.deploy_frontend(web_dir, quiet=True)

        assert generate_web._read_deployed_version(web_dir) is None

    def test_missing_build_error_is_quiet_on_stdout(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", tmp_path / "no-build")
        web_dir = tmp_path / "web"

        with pytest.raises(click.exceptions.Abort):
            generate_web.deploy_frontend(web_dir, quiet=True)

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Frontend build not found" in captured.err
