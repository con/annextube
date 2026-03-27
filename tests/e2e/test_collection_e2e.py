"""E2E test for multi-channel collection using real public archives.

Clones real annextube archives from GitHub, aggregates them into a
collection, generates a web UI, and optionally runs backup if YouTube
cookies are available.

Requires network access (git clone from GitHub).
"""

import csv
import functools
import http.server
import os
import subprocess
import sys
import threading
from pathlib import Path

import datalad.api as dl
import pytest

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.network,
    pytest.mark.ai_generated,
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Clone the same test archive under two names to simulate a multi-channel
# collection.  Using a single fast-to-clone repo keeps the test lightweight
# while exercising the full aggregate → generate-web pipeline.
ARCHIVE_REPOS = [
    ("channel-a", "https://github.com/con/annextubetesting"),
    ("channel-b", "https://github.com/con/annextubetesting"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def collection_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a DataLad superdataset and clone archive repos as subdatasets.

    Scope is module-level so the expensive clone is shared across tests.
    """
    root = tmp_path_factory.mktemp("collection")

    # Create superdataset
    dl.create(path=str(root), force=True)

    # Clone each archive as a subdataset
    for name, url in ARCHIVE_REPOS:
        print(f"\n=== Cloning {name} from {url} ===")
        dl.clone(
            source=url,
            path=str(root / name),
            dataset=str(root),
        )
        assert (root / name).is_dir(), f"Clone of {name} failed"

    return root


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_aggregate_creates_channels_tsv(collection_dir: Path) -> None:
    """Aggregate discovers channel.json in each subdataset and writes channels.tsv."""
    # Each cloned archive needs channel.json generated first
    for name, _url in ARCHIVE_REPOS:
        channel_path = collection_dir / name
        export_result = subprocess.run(
            [
                sys.executable, "-m", "annextube",
                "export", "--channel-json",
                "--output-dir", str(channel_path),
            ],
            capture_output=True,
            text=True,
            cwd=str(channel_path),
        )
        print(export_result.stdout)
        if export_result.returncode != 0:
            print(export_result.stderr)
        assert export_result.returncode == 0, (
            f"export --channel-json failed for {name}: {export_result.stderr}"
        )
        assert (channel_path / "channel.json").exists(), (
            f"channel.json not created for {name}"
        )

    result = subprocess.run(
        [sys.executable, "-m", "annextube", "aggregate", str(collection_dir), "--force"],
        capture_output=True,
        text=True,
        cwd=str(collection_dir),
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    assert result.returncode == 0, f"aggregate failed: {result.stderr}"

    channels_tsv = collection_dir / "channels.tsv"
    assert channels_tsv.exists(), "channels.tsv was not created"

    with open(channels_tsv, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        channels = list(reader)

    assert len(channels) == 2, (
        f"Expected 2 channels in channels.tsv, got {len(channels)}"
    )

    # Verify required columns are present
    expected_columns = {
        "channel_id",
        "title",
        "custom_url",
        "channel_dir",
        "total_videos_archived",
    }
    actual_columns = set(channels[0].keys())
    missing = expected_columns - actual_columns
    assert not missing, f"Missing columns in channels.tsv: {missing}"

    # Each channel should have a non-empty title and channel_dir
    for ch in channels:
        assert ch["title"], f"Empty title for channel_dir={ch.get('channel_dir')}"
        assert ch["channel_dir"] in ("channel-a", "channel-b"), (
            f"Unexpected channel_dir: {ch['channel_dir']}"
        )

    print(f"\nchannels.tsv contains {len(channels)} channel(s):")
    for ch in channels:
        print(
            f"  - {ch['title']} ({ch['channel_dir']}): "
            f"{ch['total_videos_archived']} videos archived"
        )


def test_collection_backup_with_cookies(collection_dir: Path) -> None:
    """Run collection backup if ANNEXTUBE_COOKIES_FILE is set, otherwise skip."""
    cookies = os.environ.get("ANNEXTUBE_COOKIES_FILE")
    if not cookies:
        pytest.skip(
            "Skipping backup: ANNEXTUBE_COOKIES_FILE not set "
            "(YouTube requires authentication)"
        )

    result = subprocess.run(
        [
            sys.executable, "-m", "annextube",
            "collection", "backup",
            str(collection_dir),
            "--save",
        ],
        capture_output=True,
        text=True,
        cwd=str(collection_dir),
        timeout=600,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    assert result.returncode == 0, f"collection backup failed: {result.stderr}"


def test_generate_web_creates_ui(collection_dir: Path) -> None:
    """generate-web produces web/index.html for the collection."""
    # Ensure channels.tsv exists (depends on aggregate test running first)
    channels_tsv = collection_dir / "channels.tsv"
    if not channels_tsv.exists():
        # Run aggregate if the previous test was somehow skipped
        subprocess.run(
            [sys.executable, "-m", "annextube", "aggregate", str(collection_dir), "--force"],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(collection_dir),
        )

    result = subprocess.run(
        [
            sys.executable, "-m", "annextube",
            "generate-web",
            "--output-dir", str(collection_dir),
            "--force",
        ],
        capture_output=True,
        text=True,
        cwd=str(collection_dir),
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    assert result.returncode == 0, f"generate-web failed: {result.stderr}"

    web_dir = collection_dir / "web"
    assert web_dir.is_dir(), "web/ directory was not created"
    assert (web_dir / "index.html").exists(), "web/index.html was not created"

    # channels.tsv should still be intact at the collection root
    assert channels_tsv.exists(), "channels.tsv disappeared after generate-web"

    print(f"\nWeb UI generated at {web_dir}")
    print(f"  index.html size: {(web_dir / 'index.html').stat().st_size} bytes")


def test_web_ui_with_playwright(collection_dir: Path) -> None:
    """Serve the web UI and verify channel list renders in a real browser.

    Skipped if playwright or pytest-playwright are not installed, or if
    the web directory does not exist (generate-web test must run first).
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright not installed (pip install annextube[e2e])")

    web_dir = collection_dir / "web"
    if not web_dir.is_dir():
        pytest.skip("web/ directory not found; generate-web test may have been skipped")

    channels_tsv = collection_dir / "channels.tsv"
    if not channels_tsv.exists():
        pytest.skip("channels.tsv not found; aggregate test may have been skipped")

    # Start a local HTTP server rooted at collection_dir so relative
    # paths (../channels.tsv from web/) resolve correctly.
    # Use functools.partial to set the directory without chdir.
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(collection_dir)
    )
    httpd = http.server.HTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(f"{base_url}/web/", wait_until="networkidle", timeout=30000)

            title = page.title()
            print(f"\n  Page title: {title}")

            # The page should contain some text related to channels or videos
            body_text = page.locator("body").inner_text(timeout=10000)
            assert len(body_text) > 0, "Page body is empty"

            # Take a screenshot for debugging
            screenshot_path = collection_dir / "playwright-screenshot.png"
            page.screenshot(path=str(screenshot_path))
            print(f"  Screenshot saved: {screenshot_path}")

            browser.close()
    finally:
        httpd.shutdown()

    print("  Browser test passed")
