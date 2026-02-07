"""E2E test for multi-channel collections.

Tests the complete workflow:
1. Create two channel archives (limited videos)
2. Export channel.json for each
3. Aggregate into channels.tsv
4. Generate web UI
5. Verify outputs
"""

import csv
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.network
@pytest.mark.ai_generated
def test_multi_channel_collection_workflow():
    """Test complete multi-channel collection workflow.

    Creates a collection with two channels (AnnexTubeTesting and limited apopyk),
    aggregates metadata, and verifies web UI generation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = Path(tmpdir) / "collection"
        collection_dir.mkdir()

        # Channel 1: AnnexTubeTesting (limit 3 videos)
        ch1_dir = collection_dir / "ch-annextubetesting"
        ch1_dir.mkdir()

        print("\n=== Creating channel 1: AnnexTubeTesting ===")
        result = subprocess.run(
            [
                "annextube",
                "init",
                str(ch1_dir),
                "https://www.youtube.com/@AnnexTubeTesting",
                "--limit",
                "3",
                "--comments",
                "0",
                "--no-captions",
                "--no-thumbnails",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Backup channel 1
        print("\n=== Backing up channel 1 ===")
        result = subprocess.run(
            ["annextube", "backup", "--output-dir", str(ch1_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Export channel.json for channel 1
        print("\n=== Exporting channel.json for channel 1 ===")
        result = subprocess.run(
            [
                "annextube",
                "export",
                "--output-dir",
                str(ch1_dir),
                "--channel-json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Channel 2: Andriy Popyk (limit 2 videos)
        ch2_dir = collection_dir / "ch-apopyk"
        ch2_dir.mkdir()

        print("\n=== Creating channel 2: Andriy Popyk ===")
        result = subprocess.run(
            [
                "annextube",
                "init",
                str(ch2_dir),
                "https://www.youtube.com/@apopyk",
                "--limit",
                "2",
                "--comments",
                "0",
                "--no-captions",
                "--no-thumbnails",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Backup channel 2
        print("\n=== Backing up channel 2 ===")
        result = subprocess.run(
            ["annextube", "backup", "--output-dir", str(ch2_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Export channel.json for channel 2
        print("\n=== Exporting channel.json for channel 2 ===")
        result = subprocess.run(
            [
                "annextube",
                "export",
                "--output-dir",
                str(ch2_dir),
                "--channel-json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Verify channel.json files exist
        ch1_json = ch1_dir / "channel.json"
        ch2_json = ch2_dir / "channel.json"

        assert ch1_json.exists(), "channel.json not found for channel 1"
        assert ch2_json.exists(), "channel.json not found for channel 2"

        # Verify channel.json content
        with open(ch1_json) as f:
            ch1_data = json.load(f)
            assert "channel_id" in ch1_data
            assert "name" in ch1_data
            assert "archive_stats" in ch1_data
            assert ch1_data["archive_stats"]["total_videos_archived"] > 0
            print(f"\nChannel 1: {ch1_data['name']} - {ch1_data['archive_stats']['total_videos_archived']} videos")

        with open(ch2_json) as f:
            ch2_data = json.load(f)
            assert "channel_id" in ch2_data
            assert "name" in ch2_data
            assert "archive_stats" in ch2_data
            assert ch2_data["archive_stats"]["total_videos_archived"] > 0
            print(f"Channel 2: {ch2_data['name']} - {ch2_data['archive_stats']['total_videos_archived']} videos")

        # Aggregate channels
        print("\n=== Aggregating channels ===")
        result = subprocess.run(
            ["annextube", "aggregate", str(collection_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Verify channels.tsv
        channels_tsv = collection_dir / "channels.tsv"
        assert channels_tsv.exists(), "channels.tsv not found"

        with open(channels_tsv) as f:
            reader = csv.DictReader(f, delimiter="\t")
            channels = list(reader)

            assert len(channels) == 2, f"Expected 2 channels, got {len(channels)}"

            # Verify TSV columns
            expected_columns = [
                "channel_id",
                "title",
                "custom_url",
                "description",
                "subscriber_count",
                "video_count",
                "playlist_count",
                "total_videos_archived",
                "first_video_date",
                "last_video_date",
                "last_sync",
                "channel_dir",
            ]
            assert list(channels[0].keys()) == expected_columns

            # Verify channel data
            for channel in channels:
                print(f"\n  - {channel['title']} ({channel['channel_dir']}): {channel['total_videos_archived']} videos")
                assert channel["channel_id"] != ""
                assert channel["title"] != ""
                assert int(channel["total_videos_archived"]) > 0
                assert channel["channel_dir"] in ["ch-annextubetesting", "ch-apopyk"]

        # Generate web UI
        print("\n=== Generating web UI ===")
        result = subprocess.run(
            ["annextube", "generate-web", "--output-dir", str(collection_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        # Verify web UI
        web_dir = collection_dir / "web"
        assert web_dir.exists(), "web/ directory not found"
        assert (web_dir / "index.html").exists(), "index.html not found"

        # Verify channels.tsv is accessible by web UI
        # (Web UI expects it at ../channels.tsv relative to web/index.html)
        assert channels_tsv.exists()

        # Verify per-channel videos.tsv files exist
        ch1_videos_tsv = ch1_dir / "videos" / "videos.tsv"
        ch2_videos_tsv = ch2_dir / "videos" / "videos.tsv"
        assert ch1_videos_tsv.exists(), "videos.tsv not found for channel 1"
        assert ch2_videos_tsv.exists(), "videos.tsv not found for channel 2"

        print("\n✅ Multi-channel collection workflow successful!")
        print(f"Collection directory: {collection_dir}")
        print("Structure:")
        print(f"  - channels.tsv (2 channels)")
        print(f"  - ch-annextubetesting/ ({ch1_data['archive_stats']['total_videos_archived']} videos)")
        print(f"  - ch-apopyk/ ({ch2_data['archive_stats']['total_videos_archived']} videos)")
        print(f"  - web/index.html")


@pytest.mark.network
@pytest.mark.ai_generated
def test_aggregate_with_depth():
    """Test aggregate command with different depth levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = Path(tmpdir) / "collection"
        collection_dir.mkdir()

        # Create nested structure: org/channel/
        org_dir = collection_dir / "ukraine"
        org_dir.mkdir()
        ch_dir = org_dir / "ch-annextubetesting"
        ch_dir.mkdir()

        print("\n=== Creating nested channel ===")
        result = subprocess.run(
            [
                "annextube",
                "init",
                str(ch_dir),
                "https://www.youtube.com/@AnnexTubeTesting",
                "--limit",
                "2",
                "--comments",
                "0",
                "--no-captions",
                "--no-thumbnails",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        result = subprocess.run(
            ["annextube", "backup", "--output-dir", str(ch_dir)],
            capture_output=True,
            text=True,
            check=True,
        )

        result = subprocess.run(
            [
                "annextube",
                "export",
                "--output-dir",
                str(ch_dir),
                "--channel-json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Aggregate with depth 1 (should find nothing)
        print("\n=== Aggregating with depth 1 (should find nothing) ===")
        result = subprocess.run(
            ["annextube", "aggregate", str(collection_dir), "--depth", "1"],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        assert "No channels found" in result.stdout

        # Aggregate with depth 2 (should find the channel)
        print("\n=== Aggregating with depth 2 (should find channel) ===")
        result = subprocess.run(
            ["annextube", "aggregate", str(collection_dir), "--depth", "2", "--force"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        channels_tsv = collection_dir / "channels.tsv"
        assert channels_tsv.exists()

        with open(channels_tsv) as f:
            reader = csv.DictReader(f, delimiter="\t")
            channels = list(reader)
            assert len(channels) == 1
            assert channels[0]["channel_dir"] == "ukraine/ch-annextubetesting"

        print("\n✅ Depth-based discovery successful!")
