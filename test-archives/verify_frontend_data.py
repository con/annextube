#!/usr/bin/env python3
"""
Verify frontend data loads correctly.

This script checks that TSV files can be parsed and contain expected data.
"""

import sys
from pathlib import Path

def parse_tsv(tsv_path):
    """Parse TSV file into list of dicts."""
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    if len(lines) < 2:
        return []

    headers = lines[0].split('\t')
    rows = []
    for line in lines[1:]:
        values = line.split('\t')
        row = dict(zip(headers, values))
        rows.append(row)

    return rows

def verify_archive(archive_path):
    """Verify an archive's frontend data."""
    archive_path = Path(archive_path)
    print(f"\nVerifying: {archive_path.name}")
    print("=" * 60)

    # Check videos.tsv
    videos_tsv = archive_path / "videos" / "videos.tsv"
    if not videos_tsv.exists():
        print(f"❌ Missing: {videos_tsv}")
        return False

    videos = parse_tsv(videos_tsv)
    print(f"✓ videos.tsv: {len(videos)} videos")

    # Verify required columns
    required_video_cols = [
        'video_id', 'title', 'channel_id', 'channel_name', 'published_at',
        'duration', 'view_count', 'like_count', 'comment_count',
        'thumbnail_url', 'download_status', 'source_url', 'path'
    ]

    if videos:
        first_video = videos[0]
        missing_cols = [col for col in required_video_cols if col not in first_video]
        if missing_cols:
            print(f"❌ Missing columns in videos.tsv: {missing_cols}")
            return False

        print(f"  ✓ All required columns present")
        print(f"  ✓ Sample video: {first_video['title'][:50]}...")
        print(f"  ✓ Path field: {first_video['path']}")

    # Check playlists.tsv
    playlists_tsv = archive_path / "playlists" / "playlists.tsv"
    if playlists_tsv.exists():
        playlists = parse_tsv(playlists_tsv)
        print(f"✓ playlists.tsv: {len(playlists)} playlists")

        required_playlist_cols = [
            'playlist_id', 'title', 'channel_id', 'channel_name',
            'video_count', 'total_duration', 'privacy_status',
            'created_at', 'last_sync'
        ]

        if playlists:
            first_playlist = playlists[0]
            missing_cols = [col for col in required_playlist_cols if col not in first_playlist]
            if missing_cols:
                print(f"❌ Missing columns in playlists.tsv: {missing_cols}")
                return False

            print(f"  ✓ All required columns present")
            print(f"  ✓ Sample playlist: {first_playlist['title']}")
            print(f"  ✓ Video count: {first_playlist['video_count']}")

    # Check that web directory exists
    web_dir = archive_path / "web"
    if not web_dir.exists():
        print(f"❌ Missing web directory")
        return False

    print(f"✓ web directory exists")

    # Check index.html
    index_html = web_dir / "index.html"
    if not index_html.exists():
        print(f"❌ Missing index.html")
        return False

    print(f"✓ index.html exists")

    print("\n✅ Archive verification passed!")
    return True

def main():
    """Main entry point."""
    test_archives_dir = Path(__file__).parent

    # Test both archives
    apopyk = test_archives_dir / "apopyk"
    datalad = test_archives_dir / "datalad"

    success = True

    if apopyk.exists():
        if not verify_archive(apopyk):
            success = False
    else:
        print(f"⚠ Archive not found: {apopyk}")

    if datalad.exists():
        if not verify_archive(datalad):
            success = False
    else:
        print(f"⚠ Archive not found: {datalad}")

    if success:
        print("\n" + "=" * 60)
        print("🎉 All archives verified successfully!")
        print("\nYou can now open the archives in a browser:")
        if apopyk.exists():
            print(f"  file://{apopyk}/web/index.html")
        if datalad.exists():
            print(f"  file://{datalad}/web/index.html")
        return 0
    else:
        print("\n❌ Verification failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
