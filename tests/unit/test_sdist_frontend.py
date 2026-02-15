"""Verify the built Svelte frontend is included in the installed package.

When annextube is installed from the sdist (which is what tox does), the
hatch_build.py hook compiles the Svelte frontend and the resulting web/
directory must be included in the wheel.  These tests catch regressions in
the build configuration that would silently drop the frontend.
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.ai_generated
def test_frontend_build_dir_exists():
    """FRONTEND_BUILD_DIR must point to an existing directory."""
    from annextube.cli.generate_web import FRONTEND_BUILD_DIR

    assert FRONTEND_BUILD_DIR.exists(), (
        f"Frontend build not found at {FRONTEND_BUILD_DIR}. "
        "This means the sdist/wheel does not include the built web/ directory. "
        "Check pyproject.toml [tool.hatch.build] artifacts and force-include settings."
    )


@pytest.mark.ai_generated
def test_frontend_build_has_index_html():
    """web/index.html must exist."""
    from annextube.cli.generate_web import FRONTEND_BUILD_DIR

    index = FRONTEND_BUILD_DIR / "index.html"
    assert index.exists(), f"Missing {index}"


@pytest.mark.ai_generated
def test_frontend_build_has_js_bundle():
    """web/assets/ must contain at least one .js file (the Svelte bundle)."""
    from annextube.cli.generate_web import FRONTEND_BUILD_DIR

    assets = FRONTEND_BUILD_DIR / "assets"
    assert assets.exists(), f"Missing {assets}"
    js_files = list(assets.glob("*.js"))
    assert js_files, f"No .js files in {assets}"


@pytest.mark.ai_generated
def test_frontend_build_has_css():
    """web/assets/ must contain at least one .css file."""
    from annextube.cli.generate_web import FRONTEND_BUILD_DIR

    assets = FRONTEND_BUILD_DIR / "assets"
    css_files = list(assets.glob("*.css"))
    assert css_files, f"No .css files in {assets}"


@pytest.mark.ai_generated
def test_generate_web_on_minimal_archive(tmp_path):
    """generate-web must succeed on a minimal multi-channel collection.

    Creates the bare minimum archive structure (channels.tsv) and runs
    generate-web to verify the frontend can be deployed from the installed
    package.  Uses multi-channel mode which only needs channels.tsv — no
    git-annex or export service required.
    """
    archive = tmp_path / "archive"
    archive.mkdir()

    # channels.tsv triggers multi-channel mode (no git-annex needed)
    (archive / "channels.tsv").write_text(
        "channel_id\tchannel_name\tchannel_url\tpath\n"
        "UC123\tTest\thttps://www.youtube.com/@test\tch-test\n"
    )

    # Run from archive dir so the project-root annextube/ package doesn't
    # shadow the installed one (python -m adds cwd to sys.path).
    result = subprocess.run(
        [sys.executable, "-m", "annextube", "generate-web",
         "--output-dir", str(archive)],
        capture_output=True,
        text=True,
        cwd=str(archive),
    )

    assert result.returncode == 0, (
        f"generate-web failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    web_dir = archive / "web"
    assert web_dir.exists(), "generate-web did not create web/ directory"
    assert (web_dir / "index.html").exists(), "Missing web/index.html"
    assert list((web_dir / "assets").glob("*.js")), "Missing JS bundle in web/assets/"
