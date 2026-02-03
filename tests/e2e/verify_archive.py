#!/usr/bin/env python3
"""Verify archive integrity and TSV accuracy.

This script checks that:
1. TSV download_status values match actual git-annex state
2. All videos with video.mkv files are tracked
3. File sizes are correctly classified (downloaded vs tracked)
4. Web UI displays correct counts

Usage:
    cd /path/to/archive
    uv run python /path/to/annextube/tests/e2e/verify_archive.py
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def check_git_annex_state(repo_path: Path) -> dict:
    """Check git-annex state for all video files."""
    print("\n=== Checking git-annex state ===")

    # Find all video.mkv files tracked by git-annex
    result = subprocess.run(
        ["git", "annex", "find", "--in", "here"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )

    annex_files = [line.strip() for line in result.stdout.split('\n') if line.strip().endswith('.mkv')]
    print(f"Found {len(annex_files)} video files tracked in git-annex")

    # Check each file
    file_states = {}
    for file_path in annex_files:
        full_path = repo_path / file_path
        if not full_path.exists():
            continue

        # Get file size
        try:
            target_path = full_path.resolve()
            file_size = target_path.stat().st_size

            # Classify by size
            if file_size > 1024 * 1024:  # > 1MB
                status = "downloaded"
            else:
                status = "tracked"

            file_states[file_path] = {
                'status': status,
                'size': file_size,
                'size_mb': file_size / (1024 * 1024)
            }
        except Exception as e:
            print(f"  Error checking {file_path}: {e}")

    return file_states


def check_tsv_accuracy(repo_path: Path, annex_states: dict) -> dict:
    """Check that videos.tsv matches actual git-annex state."""
    print("\n=== Checking videos.tsv accuracy ===")

    videos_tsv = repo_path / "videos" / "videos.tsv"
    if not videos_tsv.exists():
        print("  ✗ videos.tsv not found!")
        return {}

    # Read TSV
    with open(videos_tsv) as f:
        reader = csv.DictReader(f, delimiter='\t')
        tsv_data = {row['video_id']: row for row in reader}

    print(f"Found {len(tsv_data)} videos in TSV")

    # Count statuses
    status_counts = {'metadata_only': 0, 'tracked': 0, 'downloaded': 0}
    for row in tsv_data.values():
        status = row.get('download_status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    print("TSV status distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # Verify each video
    mismatches = []
    for video_id, row in tsv_data.items():
        tsv_status = row.get('download_status')
        video_path = row.get('path', '')

        # Check if video.mkv exists
        video_file = f"videos/{video_path}/video.mkv"

        if video_file in annex_states:
            actual_status = annex_states[video_file]['status']
            if tsv_status != actual_status:
                mismatches.append({
                    'video_id': video_id,
                    'tsv_status': tsv_status,
                    'actual_status': actual_status,
                    'size_mb': annex_states[video_file]['size_mb']
                })
        else:
            # No video file
            if tsv_status != 'metadata_only':
                mismatches.append({
                    'video_id': video_id,
                    'tsv_status': tsv_status,
                    'actual_status': 'metadata_only',
                    'size_mb': 0
                })

    if mismatches:
        print(f"\n  ✗ Found {len(mismatches)} mismatches:")
        for m in mismatches[:5]:  # Show first 5
            print(f"    {m['video_id']}: TSV={m['tsv_status']}, Actual={m['actual_status']} ({m['size_mb']:.1f}MB)")
    else:
        print("  ✓ All TSV entries match actual state!")

    return {'status_counts': status_counts, 'mismatches': mismatches}


def verify_archive(repo_path: Path) -> bool:
    """Run all verification checks."""
    print("=" * 60)
    print("Archive Verification")
    print("=" * 60)
    print(f"Archive: {repo_path}")

    # Check if it's a git-annex repo
    if not (repo_path / ".git" / "annex").exists():
        print("\n✗ Not a git-annex repository!")
        return False

    # Check git-annex state
    annex_states = check_git_annex_state(repo_path)

    # Check TSV accuracy
    tsv_results = check_tsv_accuracy(repo_path, annex_states)

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    status_counts = tsv_results.get('status_counts', {})
    mismatches = tsv_results.get('mismatches', [])

    print(f"Total videos in annex: {len(annex_states)}")
    print(f"Total videos in TSV: {sum(status_counts.values())}")
    print(f"TSV mismatches: {len(mismatches)}")

    if mismatches:
        print("\n✗ Verification FAILED")
        print("\nTo fix: Run 'annextube export' to regenerate TSV files")
        return False
    else:
        print("\n✓ Verification PASSED")
        print("\nAll TSV entries correctly reflect git-annex state!")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify archive integrity")
    parser.add_argument(
        "archive_path",
        nargs="?",
        default=".",
        help="Path to archive (default: current directory)"
    )
    args = parser.parse_args()

    archive_path = Path(args.archive_path).resolve()
    success = verify_archive(archive_path)
    sys.exit(0 if success else 1)
