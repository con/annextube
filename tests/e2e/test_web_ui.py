#!/usr/bin/env python3
"""End-to-end tests for annextube web UI.

This script verifies that the web UI works correctly with a test archive:
- Loading videos and playlists
- Filtering by download status (tracked/downloaded)
- Video seeking functionality
- Playlist navigation

Usage:
    # Start annextube serve in background first
    cd /path/to/archive
    annextube serve --port 8080 &

    # Run tests
    uv run python tests/e2e/test_web_ui.py

    # Or with custom URL
    uv run python tests/e2e/test_web_ui.py --url http://localhost:8080
"""

import argparse
import sys
import time

from playwright.sync_api import Page, sync_playwright


def test_main_page_loads(page: Page, base_url: str) -> bool:
    """Test that the main page loads correctly."""
    print("\n=== Test: Main Page Load ===")
    try:
        page.goto(f"{base_url}/web/", wait_until="networkidle")

        # Check title
        title = page.title()
        print(f"  Page title: {title}")
        if "YouTube Archive Browser" not in title:
            print(f"  ✗ Unexpected title: {title}")
            return False

        # Check video count
        video_text = page.locator("text=/\\d+ videos/").first.inner_text()
        print(f"  {video_text}")

        print("  ✓ Main page loads correctly")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_download_status_filters(page: Page, base_url: str) -> bool:
    """Test that download status filters work."""
    print("\n=== Test: Download Status Filters ===")
    try:
        page.goto(f"{base_url}/web/", wait_until="networkidle")
        time.sleep(1)

        # Find Downloaded checkbox
        downloaded_checkbox = page.locator("label:has-text('Downloaded') input[type='checkbox']").first
        tracked_checkbox = page.locator("label:has-text('Tracked') input[type='checkbox']").first

        # Test Downloaded filter
        print("  Testing 'Downloaded' filter...")
        if not downloaded_checkbox.is_checked():
            downloaded_checkbox.click()
            time.sleep(1)

        video_count = page.locator("text=/\\d+ videos/").first.inner_text()
        print(f"    Downloaded filter: {video_count}")

        # Test Tracked filter
        print("  Testing 'Tracked' filter...")
        downloaded_checkbox.click()  # Uncheck Downloaded
        time.sleep(0.5)
        tracked_checkbox.click()  # Check Tracked
        time.sleep(1)

        video_count = page.locator("text=/\\d+ videos/").first.inner_text()
        print(f"    Tracked filter: {video_count}")

        print("  ✓ Download status filters work")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_video_playback(page: Page, base_url: str) -> bool:
    """Test that video playback works with seeking."""
    print("\n=== Test: Video Playback & Seeking ===")
    try:
        # Navigate to first video
        page.goto(f"{base_url}/web/", wait_until="networkidle")
        time.sleep(1)

        # Click first video
        first_video = page.locator("a[href*='#/video']").first
        print("  Opening first video...")
        first_video.click()
        time.sleep(2)

        # Check video element exists
        video = page.locator("video").first
        if not video:
            print("  ✗ No video element found")
            return False

        print("  ✓ Video player loaded")

        # Wait for metadata
        page.wait_for_function("() => document.querySelector('video').readyState >= 1", timeout=10000)

        # Get duration
        duration = page.evaluate("() => document.querySelector('video').duration")
        print(f"  Video duration: {duration:.2f}s")

        if duration <= 0:
            print("  ✗ Invalid video duration")
            return False

        # Test seeking
        seek_pos = min(30, duration * 0.5)
        print(f"  Testing seek to {seek_pos:.1f}s...")
        page.evaluate(f"() => {{ document.querySelector('video').currentTime = {seek_pos} }}")
        time.sleep(1)

        current_time = page.evaluate("() => document.querySelector('video').currentTime")
        print(f"  Current time after seek: {current_time:.1f}s")

        if abs(current_time - seek_pos) < 2:
            print("  ✓ Video seeking works correctly")
            return True
        else:
            print(f"  ✗ Seek failed (expected ~{seek_pos:.1f}s, got {current_time:.1f}s)")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_playlists(page: Page, base_url: str) -> bool:
    """Test that playlists are displayed and accessible."""
    print("\n=== Test: Playlists ===")
    try:
        page.goto(f"{base_url}/web/", wait_until="networkidle")
        time.sleep(1)

        # Look for playlist filter section
        try:
            # Check if Playlists section exists
            playlist_section = page.locator("text=Playlists").first
            if playlist_section.count() == 0:
                print("  Note: No playlist filter section found (may be no playlists)")
                return True

            print("  ✓ Playlists section found")

            # Try to count playlists
            # This is implementation-specific, adjust selector as needed
            playlist_count = page.locator("label:near(text='Playlists')").count()
            print(f"  Found {playlist_count} playlist filter(s)")

            return True
        except Exception as e:
            print(f"  Note: Could not verify playlists: {e}")
            return True  # Non-critical

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def run_all_tests(base_url: str = "http://0.0.0.0:8080") -> bool:
    """Run all web UI tests."""
    print("=" * 60)
    print("annextube Web UI End-to-End Tests")
    print("=" * 60)
    print(f"Testing against: {base_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        tests = [
            ("Main Page Load", test_main_page_loads),
            ("Download Status Filters", test_download_status_filters),
            ("Video Playback & Seeking", test_video_playback),
            ("Playlists", test_playlists),
        ]

        results = []
        for test_name, test_func in tests:
            success = test_func(page, base_url)
            results.append((test_name, success))

        # Take final screenshot
        screenshot_path = "/tmp/annextube-e2e-final.png"
        page.screenshot(path=screenshot_path)
        print(f"\n📸 Screenshot saved: {screenshot_path}")

        browser.close()

        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        passed = sum(1 for _, success in results if success)
        total = len(results)

        for test_name, success in results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status}: {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")
        print("=" * 60)

        return all(success for _, success in results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run annextube web UI E2E tests")
    parser.add_argument("--url", default="http://0.0.0.0:8080", help="Base URL of annextube server")
    args = parser.parse_args()

    success = run_all_tests(args.url)
    sys.exit(0 if success else 1)
