#!/usr/bin/env python3
"""Test YouTube API metadata enhancement with real data.

This script uses the YOUTUBE_API_KEY from environment (sourced from .git/secrets)
to test metadata fetching from real videos, including the user's Liked Videos.

Usage:
    # Source API key
    source ../.git/secrets

    # Test with Liked Videos playlist
    python test_api_metadata.py --liked-videos

    # Test with specific channel
    python test_api_metadata.py --channel "@ChannelName"

    # Test with specific video IDs
    python test_api_metadata.py --video-ids "dQw4w9WgXcQ,YE7VzlLtp-4"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path to import annextube
sys.path.insert(0, str(Path(__file__).parent.parent))

from annextube.services.youtube_api import YouTubeAPIMetadataClient, QuotaEstimator


def test_liked_videos(api_key: str, max_results: int = 50) -> None:
    """Test fetching metadata from user's Liked Videos playlist.

    Note: This requires OAuth authentication, not just an API key.
    The liked videos playlist ID is channel-specific.
    """
    print("=" * 80)
    print("Testing Liked Videos Playlist")
    print("=" * 80)
    print()
    print("⚠️  WARNING: Fetching liked videos requires OAuth authentication.")
    print("    An API key alone cannot access private playlists.")
    print()
    print("To test liked videos:")
    print("  1. Use annextube CLI with --youtube-api-key and authentication cookies")
    print("  2. Or manually get video IDs and use --video-ids option")
    print()


def test_channel_videos(api_key: str, channel_url: str, max_results: int = 20) -> dict[str, Any]:
    """Test fetching metadata from a public channel's videos."""
    print("=" * 80)
    print(f"Testing Channel: {channel_url}")
    print("=" * 80)
    print()

    # For now, just test with known video IDs
    # Full channel fetching requires yt-dlp integration
    print("⚠️  Note: Full channel fetching requires yt-dlp integration.")
    print("    Use --video-ids to test specific videos from the channel.")
    print()

    return {}


def test_video_metadata(api_key: str, video_ids: list[str]) -> dict[str, Any]:
    """Test fetching enhanced metadata for specific video IDs."""
    print("=" * 80)
    print(f"Testing {len(video_ids)} Video(s)")
    print("=" * 80)
    print()

    client = YouTubeAPIMetadataClient(api_key=api_key)

    # Estimate quota cost
    estimated_cost = QuotaEstimator.estimate_video_metadata_cost(len(video_ids))
    print(f"📊 Estimated quota cost: {estimated_cost:,} units")
    print()

    # Fetch metadata
    print("Fetching video details from YouTube API...")
    try:
        videos_data = client.get_video_details(video_ids)
    except Exception as e:
        print(f"❌ Error fetching video details: {e}")
        return {}

    print(f"✓ Fetched data for {len(videos_data)} video(s)")
    print()

    # Process each video
    results = {}
    for video_id, video_data in videos_data.items():
        print("-" * 80)
        print(f"Video ID: {video_id}")
        print("-" * 80)

        # Extract enhanced metadata
        metadata = client.extract_enhanced_metadata(video_data)
        results[video_id] = metadata

        # Display key metadata
        snippet = video_data.get("snippet", {})
        print(f"Title: {snippet.get('title', 'N/A')}")
        print(f"Channel: {snippet.get('channelTitle', 'N/A')}")
        print()

        print("📋 License Information:")
        print(f"  License: {metadata.get('license', 'N/A')}")
        print(f"  Licensed Content: {metadata.get('licensed_content', 'N/A')}")
        print(f"  Embeddable: {metadata.get('embeddable', 'N/A')}")
        print()

        if metadata.get("recording_date") or metadata.get("recording_location"):
            print("📍 Recording Details:")
            if metadata.get("recording_date"):
                print(f"  Date: {metadata['recording_date']}")
            if metadata.get("recording_location"):
                loc = metadata["recording_location"]
                print(f"  Location: {loc.get('latitude', 'N/A')}, {loc.get('longitude', 'N/A')}")
                if metadata.get("location_description"):
                    print(f"  Description: {metadata['location_description']}")
            print()

        if metadata.get("region_restriction"):
            print("🌍 Region Restrictions:")
            restriction = metadata["region_restriction"]
            if restriction.get("allowed"):
                print(f"  Allowed: {', '.join(restriction['allowed'][:5])}...")
            if restriction.get("blocked"):
                print(f"  Blocked: {', '.join(restriction['blocked'][:5])}...")
            print()

        print("🎥 Technical Details:")
        print(f"  Definition: {metadata.get('definition', 'N/A')}")
        print(f"  Dimension: {metadata.get('dimension', 'N/A')}")
        print(f"  Projection: {metadata.get('projection', 'N/A')}")
        print()

        if metadata.get("topic_categories"):
            print("🏷️  Topic Categories:")
            for topic in metadata["topic_categories"]:
                # Extract topic name from URL
                topic_name = topic.split("/")[-1].replace("_", " ")
                print(f"  - {topic_name}")
            print()

    return results


def save_results(results: dict[str, Any], output_file: Path) -> None:
    """Save test results to JSON file."""
    output_file.write_text(json.dumps(results, indent=2))
    print(f"✓ Results saved to: {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test YouTube API metadata enhancement")
    parser.add_argument(
        "--liked-videos",
        action="store_true",
        help="Test with user's Liked Videos playlist (requires OAuth)"
    )
    parser.add_argument(
        "--channel",
        help="Test with videos from a specific channel (URL or handle)"
    )
    parser.add_argument(
        "--video-ids",
        help="Comma-separated list of video IDs to test"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum number of videos to fetch (default: 20)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file"
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY environment variable not set")
        print()
        print("Set it via:")
        print("  source ../.git/secrets")
        print("  OR")
        print("  export YOUTUBE_API_KEY='your-key-here'")
        sys.exit(1)

    print(f"✓ API key loaded: {api_key[:20]}...{api_key[-4:]}")
    print()

    # Run appropriate test
    results = {}

    if args.liked_videos:
        test_liked_videos(api_key, args.max_results)
    elif args.channel:
        results = test_channel_videos(api_key, args.channel, args.max_results)
    elif args.video_ids:
        video_ids = [vid.strip() for vid in args.video_ids.split(",")]
        results = test_video_metadata(api_key, video_ids)
    else:
        # Default: test with known videos of different licenses
        print("No specific test specified. Testing with known videos...")
        print()

        known_videos = [
            "YE7VzlLtp-4",  # Big Buck Bunny (Creative Commons)
            "dQw4w9WgXcQ",  # Rick Astley (Standard License)
        ]
        results = test_video_metadata(api_key, known_videos)

    # Save results if requested
    if args.output and results:
        save_results(results, args.output)
        print()

    print("=" * 80)
    print("✓ Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
