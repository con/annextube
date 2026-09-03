"""Stale-bundle detection for ``generate-web`` in a development checkout.

``web/`` is git-ignored and built by ``hatch_build.py`` at install time, so a
checkout that changes ``frontend/src/`` without rebuilding deploys the *old*
UI.  ``_warn_if_bundle_stale()`` makes that visible instead of silent.
"""

import os

import pytest

from annextube.cli import generate_web


def _make_tree(tmp_path, bundle_mtime: float, source_mtime: float):
    """Build a fake checkout with a bundle and one frontend source file."""
    assets = tmp_path / "web" / "assets"
    assets.mkdir(parents=True)
    bundle = assets / "index.js"
    bundle.write_text("// built bundle")
    os.utime(bundle, (bundle_mtime, bundle_mtime))

    src = tmp_path / "frontend" / "src" / "services"
    src.mkdir(parents=True)
    source = src / "data-loader.ts"
    source.write_text("// source")
    os.utime(source, (source_mtime, source_mtime))

    return tmp_path / "web", tmp_path / "frontend" / "src"


@pytest.mark.ai_generated
def test_warns_when_sources_are_newer_than_bundle(tmp_path, monkeypatch, capsys):
    """A source edited after the last build must produce a warning."""
    web, src = _make_tree(tmp_path, bundle_mtime=1000, source_mtime=2000)
    monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", web)
    monkeypatch.setattr(generate_web, "FRONTEND_SRC_DIR", src)

    generate_web._warn_if_bundle_stale()

    err = capsys.readouterr().err
    assert "older than 1 frontend source file(s)" in err
    assert "data-loader.ts" in err
    assert "npm run build" in err


@pytest.mark.ai_generated
def test_silent_when_bundle_is_current(tmp_path, monkeypatch, capsys):
    """A bundle built after the last source edit says nothing."""
    web, src = _make_tree(tmp_path, bundle_mtime=2000, source_mtime=1000)
    monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", web)
    monkeypatch.setattr(generate_web, "FRONTEND_SRC_DIR", src)

    generate_web._warn_if_bundle_stale()

    assert capsys.readouterr().err == ""


@pytest.mark.ai_generated
def test_silent_without_frontend_sources(tmp_path, monkeypatch, capsys):
    """An installed wheel has no frontend/src/ to compare against."""
    web, src = _make_tree(tmp_path, bundle_mtime=1000, source_mtime=2000)
    monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", web)
    monkeypatch.setattr(generate_web, "FRONTEND_SRC_DIR", tmp_path / "absent")

    generate_web._warn_if_bundle_stale()

    assert capsys.readouterr().err == ""


@pytest.mark.ai_generated
def test_silent_without_a_built_bundle(tmp_path, monkeypatch, capsys):
    """No assets/*.js means there is no build time to compare against.

    deploy_frontend() reports a missing build separately; this check must
    not add noise on top of it.
    """
    web, src = _make_tree(tmp_path, bundle_mtime=1000, source_mtime=2000)
    (web / "assets" / "index.js").unlink()
    monkeypatch.setattr(generate_web, "FRONTEND_BUILD_DIR", web)
    monkeypatch.setattr(generate_web, "FRONTEND_SRC_DIR", src)

    generate_web._warn_if_bundle_stale()

    assert capsys.readouterr().err == ""
