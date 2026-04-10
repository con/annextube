"""Integration tests for multi-channel collection pipeline.

Tests the aggregate → generate-web pipeline using real file I/O with
synthetic channel fixtures.  Network-dependent operations (YouTube backup,
DataLad) are out of scope — those are covered by E2E network tests.

The pipeline under test:
  1. Create collection structure with channel.json + videos.tsv per channel
  2. Run aggregate to produce channels.tsv
  3. Verify channels.tsv contents
  4. Verify discover_subdatasets finds the right directories
"""

import csv
import json
from pathlib import Path

import pytest

from annextube.cli.aggregate import aggregate, compute_archive_stats, discover_channels
from annextube.services.collection import discover_subdatasets


def _make_channel_fixture(
    collection_dir: Path,
    name: str,
    channel_id: str,
    custom_url: str,
    videos: list[dict],
) -> Path:
    """Create a minimal channel archive fixture.

    Creates the directory structure expected by aggregate:
      {name}/channel.json
      {name}/videos/videos.tsv
      {name}/.annextube/config.toml  (for discover_subdatasets)
    """
    ch_dir = collection_dir / name
    ch_dir.mkdir()

    # channel.json
    channel_json = {
        "channel_id": channel_id,
        "name": name.replace("ch-", "").title(),
        "custom_url": custom_url,
        "description": f"Test channel {name}",
        "subscriber_count": 1000,
        "video_count": len(videos),
        "playlist_count": 0,
    }
    (ch_dir / "channel.json").write_text(json.dumps(channel_json, indent=2))

    # videos/videos.tsv
    videos_dir = ch_dir / "videos"
    videos_dir.mkdir()
    if videos:
        fieldnames = [
            "video_id", "title", "channel_id", "channel_name",
            "published_at", "duration", "view_count", "like_count",
            "comment_count", "thumbnail_url", "download_status",
            "source_url", "path",
        ]
        with open(videos_dir / "videos.tsv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            for v in videos:
                writer.writerow(v)

    # .annextube/config.toml (for discover_subdatasets)
    config_dir = ch_dir / ".annextube"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        f'[[sources]]\nurl = "https://www.youtube.com/{custom_url}"\ntype = "channel"\n'
    )

    return ch_dir


def _make_video(video_id: str, title: str, channel_id: str, channel_name: str,
                published_at: str, duration: int = 300) -> dict:
    """Create a minimal video row dict for videos.tsv."""
    return {
        "video_id": video_id,
        "title": title,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "published_at": published_at,
        "duration": str(duration),
        "view_count": "100",
        "like_count": "10",
        "comment_count": "5",
        "thumbnail_url": f"https://example.com/{video_id}.jpg",
        "download_status": "tracked",
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
        "path": video_id.lower(),
    }


@pytest.fixture
def collection_dir(tmp_path):
    """Create a multi-channel collection fixture with 2 channels."""
    root = tmp_path / "my-collection"
    root.mkdir()

    _make_channel_fixture(
        root, "ch-alpha", "UC001", "@AlphaChannel",
        videos=[
            _make_video("V001", "Alpha Vid 1", "UC001", "Alpha", "2023-01-15"),
            _make_video("V002", "Alpha Vid 2", "UC001", "Alpha", "2023-06-20", 600),
            _make_video("V003", "Alpha Vid 3", "UC001", "Alpha", "2024-01-10", 120),
        ],
    )

    _make_channel_fixture(
        root, "ch-beta", "UC002", "@BetaChannel",
        videos=[
            _make_video("V010", "Beta Vid 1", "UC002", "Beta", "2022-05-01", 900),
            _make_video("V011", "Beta Vid 2", "UC002", "Beta", "2024-03-01", 450),
        ],
    )

    return root


class TestCollectionPipeline:
    """Integration tests for the collection pipeline: aggregate + discover."""

    @pytest.mark.ai_generated
    def test_discover_channels_finds_both(self, collection_dir) -> None:
        """discover_channels finds channel.json in both subdirectories."""
        channels = discover_channels(collection_dir, depth=1)
        assert len(channels) == 2
        dirs = [str(rel) for rel, _ in channels]
        assert "ch-alpha" in dirs
        assert "ch-beta" in dirs

    @pytest.mark.ai_generated
    def test_compute_archive_stats(self, collection_dir) -> None:
        """compute_archive_stats reads videos.tsv and produces correct counts."""
        stats = compute_archive_stats(collection_dir / "ch-alpha")
        assert stats["total_videos_archived"] == 3
        assert stats["first_video_date"] == "2023-01-15"
        assert stats["last_video_date"] == "2024-01-10"
        assert stats["total_duration_seconds"] == 300 + 600 + 120

    @pytest.mark.ai_generated
    def test_compute_archive_stats_no_videos_tsv(self, collection_dir) -> None:
        """compute_archive_stats handles missing videos.tsv gracefully."""
        # Create a channel without videos.tsv
        empty_dir = collection_dir / "ch-empty"
        empty_dir.mkdir()
        (empty_dir / "channel.json").write_text('{"channel_id": "UC999"}')

        stats = compute_archive_stats(empty_dir)
        assert stats["total_videos_archived"] == 0
        assert stats["first_video_date"] is None
        assert stats["last_video_date"] is None

    @pytest.mark.ai_generated
    def test_discover_subdatasets_finds_configured(self, collection_dir) -> None:
        """discover_subdatasets finds directories with .annextube/config.toml."""
        subdatasets = discover_subdatasets(collection_dir)
        assert len(subdatasets) == 2
        names = [p.name for p in subdatasets]
        assert names == ["ch-alpha", "ch-beta"]  # sorted

    @pytest.mark.ai_generated
    def test_discover_subdatasets_skips_unconfigured(self, collection_dir) -> None:
        """Directories without .annextube/config.toml are not discovered."""
        # Create a directory without config
        (collection_dir / "random-dir").mkdir()
        subdatasets = discover_subdatasets(collection_dir)
        names = [p.name for p in subdatasets]
        assert "random-dir" not in names

    @pytest.mark.ai_generated
    def test_aggregate_produces_channels_tsv(self, collection_dir) -> None:
        """Running aggregate creates a valid channels.tsv with both channels."""
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(aggregate, [str(collection_dir), "--force"])
        assert result.exit_code == 0, result.output

        channels_tsv = collection_dir / "channels.tsv"
        assert channels_tsv.exists()

        with open(channels_tsv) as f:
            reader = csv.DictReader(f, delimiter="\t")
            rows = list(reader)

        assert len(rows) == 2

        # Rows are sorted by title (case-insensitive)
        # "Alpha" (from ch-alpha) and "Beta" (from ch-beta)
        alpha_row = next(r for r in rows if r["channel_id"] == "UC001")
        beta_row = next(r for r in rows if r["channel_id"] == "UC002")

        assert alpha_row["custom_url"] == "@AlphaChannel"
        assert alpha_row["total_videos_archived"] == "3"
        assert alpha_row["first_video_date"] == "2023-01-15"
        assert alpha_row["last_video_date"] == "2024-01-10"
        assert alpha_row["channel_dir"] == "ch-alpha"

        assert beta_row["total_videos_archived"] == "2"
        assert beta_row["channel_dir"] == "ch-beta"

    @pytest.mark.ai_generated
    def test_aggregate_idempotent_with_force(self, collection_dir) -> None:
        """Running aggregate twice with --force produces same result."""
        from click.testing import CliRunner

        runner = CliRunner()
        runner.invoke(aggregate, [str(collection_dir), "--force"])
        runner.invoke(aggregate, [str(collection_dir), "--force"])

        channels_tsv = collection_dir / "channels.tsv"
        with open(channels_tsv) as f:
            reader = csv.DictReader(f, delimiter="\t")
            rows = list(reader)

        assert len(rows) == 2

    @pytest.mark.ai_generated
    def test_aggregate_without_force_fails_on_existing(self, collection_dir) -> None:
        """aggregate without --force refuses to overwrite existing channels.tsv."""
        from click.testing import CliRunner

        runner = CliRunner()
        # First run creates the file
        runner.invoke(aggregate, [str(collection_dir), "--force"])

        # Second run without --force should fail
        result = runner.invoke(aggregate, [str(collection_dir)])
        assert result.exit_code == 1

    @pytest.mark.ai_generated
    def test_aggregate_handles_cloned_archives(self, collection_dir) -> None:
        """Cloned archives (with channel.json but without local backup history) are aggregated."""
        # Simulate a cloned archive: has channel.json and videos.tsv
        # but may lack .annextube/config.toml (aggregate uses channel.json, not config)
        cloned_dir = collection_dir / "ch-cloned"
        cloned_dir.mkdir()
        (cloned_dir / "channel.json").write_text(json.dumps({
            "channel_id": "UC_CLONED",
            "name": "Cloned Channel",
            "custom_url": "@ClonedChannel",
            "description": "An externally cloned archive",
            "subscriber_count": 500,
            "video_count": 10,
            "playlist_count": 0,
        }))
        # Has videos.tsv with some data
        videos_dir = cloned_dir / "videos"
        videos_dir.mkdir()
        with open(videos_dir / "videos.tsv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "video_id", "title", "channel_id", "channel_name",
                "published_at", "duration", "view_count", "like_count",
                "comment_count", "thumbnail_url", "download_status",
                "source_url", "path",
            ], delimiter="\t")
            writer.writeheader()
            writer.writerow(_make_video(
                "VC01", "Cloned Vid", "UC_CLONED", "Cloned", "2024-02-15",
            ))

        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(aggregate, [str(collection_dir), "--force"])
        assert result.exit_code == 0, result.output

        with open(collection_dir / "channels.tsv") as f:
            reader = csv.DictReader(f, delimiter="\t")
            rows = list(reader)

        # Should now have 3 channels: alpha, beta, and the cloned one
        assert len(rows) == 3
        cloned_row = next(r for r in rows if r["channel_id"] == "UC_CLONED")
        assert cloned_row["total_videos_archived"] == "1"
        assert cloned_row["channel_dir"] == "ch-cloned"

    @pytest.mark.ai_generated
    def test_channel_usable_standalone(self, collection_dir) -> None:
        """FR-029: Channel archive works independently outside collection."""
        ch_dir = collection_dir / "ch-alpha"
        assert (ch_dir / "channel.json").exists()
        assert (ch_dir / "videos" / "videos.tsv").exists()
        assert (ch_dir / ".annextube" / "config.toml").exists()

        # aggregate on a single channel dir finds no sub-channels
        channels = discover_channels(ch_dir, depth=1)
        assert len(channels) == 0

        # but its own archive stats are computable
        stats = compute_archive_stats(ch_dir)
        assert stats["total_videos_archived"] == 3

    @pytest.mark.ai_generated
    def test_empty_collection(self, tmp_path) -> None:
        """Aggregate on empty dir exits 0 with no channels.tsv created."""
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(aggregate, [str(tmp_path)])
        assert result.exit_code == 0
        assert not (tmp_path / "channels.tsv").exists()
