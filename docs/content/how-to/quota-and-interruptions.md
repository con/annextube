---
title: "Handling Quota Limits and Interruptions"
description: "Guide to YouTube API quota management and backup recovery"
weight: 30
---

# Handling Quota Limits and Interruptions

This guide explains how annextube handles YouTube API quota limits and backup interruptions, ensuring your data is safe and backups can resume seamlessly.

## YouTube API Quota Management

### Understanding YouTube API Quotas

YouTube Data API v3 has a daily quota limit:
- **Default quota**: 10,000 units per day (free tier)
- **Enhanced metadata**: 10 units per video
- **Comments**: 1 unit per 100 comment threads
- **Quota reset**: Midnight Pacific Time (PST/PDT)

**Example capacity**:
- ~1,000 videos/day (metadata only)
- ~500 videos/day (metadata + 100 comments each)

### Automatic Quota Handling

**annextube automatically handles quota exceeded errors** with intelligent retry logic:

#### How It Works

1. **Detection**: Recognizes `quotaExceeded` HTTP 403 errors from YouTube API
2. **Calculation**: Computes time until midnight Pacific Time (handles PST/PDT transitions)
3. **Sleep**: Waits with progress updates every 30 minutes
4. **Retry**: Automatically resumes operation when quota resets
5. **Cancellation**: Supports Ctrl+C to abort wait

#### Example Workflow

```bash
$ annextube backup --output-dir my-archive

# Processing videos...
Processing video 847/2000: Example Video Title

# Quota exceeded!
WARNING - YouTube API quota exceeded: quotaExceeded
WARNING - Quota resets at: 2026-02-08 00:00:00 PST
INFO - Sleeping until quota reset (9h 33m from now). Press Ctrl+C to cancel.

# Progress updates every 30 minutes
INFO - Quota resets in 9h 3m
INFO - Quota resets in 8h 33m
INFO - Quota resets in 8h 3m
...

# Quota resets at midnight PT
INFO - Quota reset time reached. Resuming operations.
Processing video 848/2000: Next Video Title
...
```

### Configuration

Default settings work for most users, but you can customize behavior:

**Python API** (for custom scripts):
```python
from annextube.lib.quota_manager import QuotaManager

# Default: enabled, 48h max wait, 30min check interval
quota_manager = QuotaManager()

# Custom: 24h max wait, 15min check interval
quota_manager = QuotaManager(
    enabled=True,
    max_wait_hours=24,
    check_interval_seconds=900
)

# Disable auto-wait (abort immediately on quota exceeded)
quota_manager = QuotaManager(enabled=False)

# Pass to YouTube API clients
from annextube.services.youtube_api import YouTubeAPIMetadataClient
client = YouTubeAPIMetadataClient(api_key="...", quota_manager=quota_manager)
```

**Future**: Configuration file support planned for `.annextube/config.toml`:
```toml
[api]
quota_auto_wait = true       # Enable auto-wait (default: true)
quota_max_wait_hours = 48    # Max hours to wait (default: 48)
quota_check_interval_min = 30 # Check every N minutes (default: 30)
```

### Strategies for Large Backups

If you're backing up a large channel (>1000 videos):

#### Strategy 1: Incremental Backups Over Multiple Days

```bash
# Day 1: Initial backup (hits quota at ~1000 videos)
annextube backup --output-dir my-archive --limit 1000

# Day 2: Continue backup (next 1000 videos)
annextube backup --output-dir my-archive --limit 2000

# Day 3: Final batch
annextube backup --output-dir my-archive
```

Incremental mode automatically skips existing videos.

#### Strategy 2: Use yt-dlp Only (No API)

```bash
# Don't set YOUTUBE_API_KEY
unset YOUTUBE_API_KEY

# Backup with yt-dlp only (no quota limits)
annextube backup --output-dir my-archive
```

**Trade-off**: No enhanced metadata (license, recording location, etc.), but no quota limits.

#### Strategy 3: Request Quota Increase

For production use, request increased quota:

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)
2. Select your project
3. Request quota increase for "Queries per day"
4. Can request up to 1,000,000 units/day (paid tier)

**Cost estimate** (at 1M units/day):
- Enables ~100,000 videos/day
- Google may charge for quota above free tier

#### Strategy 4: Split into Components

Process metadata and comments separately to optimize quota usage:

```bash
# Day 1: Metadata only (10 units/video = 1000 videos)
annextube backup --output-dir my-archive --comments 0

# Day 2: Add comments for recent videos (1 unit/100 threads)
annextube backup --output-dir my-archive --update-mode comments --date-start 2026-01-01
```

---

## Backup Interruption Recovery

### Understanding Interruptions

Backups can be interrupted by:
- **Ctrl+C** (user cancellation)
- **System crash** (power loss, kernel panic)
- **Quota exceeded** (API limits)
- **Network errors** (transient failures)

annextube is designed to handle interruptions gracefully with **zero data loss**.

### What's Safe on Interruption

#### ✅ Always Safe on Disk

These are written immediately during processing:

- **`metadata.json`** files for each video
- **Git-annex URL links** (staged in git)
- **Downloaded content** (if `--videos` enabled):
  - Video files (`.mkv`)
  - Captions (`.vtt`)
  - Thumbnails (`.jpg`)
- **TSV files** (if checkpoint commits enabled)

#### ❌ Lost in Memory

Only summary statistics are lost:
- `videos_processed` counter
- `captions_downloaded` counter
- Other stats for final summary log

**Impact**: Just informational logging, no actual data loss.

### Automatic Recovery with Checkpoints

**Default behavior**: annextube creates checkpoint commits every 50 videos.

#### Checkpoint Example

```bash
$ annextube backup --output-dir my-archive

Processing video 1/300...
Processing video 50/300...
INFO - Checkpoint: 50/300 videos processed
INFO - Generating TSV metadata files
[Commit: "Checkpoint: @channel (50/300 videos)"]

Processing video 100/300...
INFO - Checkpoint: 100/300 videos processed
[Commit: "Checkpoint: @channel (100/300 videos)"]

Processing video 150/300...
^C  # User presses Ctrl+C

WARNING - Backup interrupted by user (Ctrl+C)
INFO - Auto-committing partial progress (173 videos processed)...
INFO - Generating TSV metadata files
[Commit: "Partial backup (interrupted): @channel (173 videos)"]
INFO - Partial progress committed successfully
```

#### Git History

```bash
$ git log --oneline

a1b2c3d Partial backup (interrupted): @channel (173 videos)
e4f5g6h Checkpoint: @channel (150/300 videos)
i7j8k9l Checkpoint: @channel (100/300 videos)
m0n1o2p Checkpoint: @channel (50/300 videos)
...
```

#### Resume Backup

```bash
$ annextube backup --output-dir my-archive

# Incremental mode automatically detects existing videos
INFO - Incremental mode: filtering 173 existing videos
INFO - Found 127 new videos to process (174-300)

Processing video 174/300...
...
```

**Result**: Continues exactly where it left off, no duplicate work.

### Configuration

Customize checkpoint behavior in `.annextube/config.toml`:

```toml
[backup]
# Checkpoint interval (0 = disabled)
checkpoint_interval = 50

# Enable/disable checkpoint commits
checkpoint_enabled = true

# Auto-commit on Ctrl+C (highly recommended)
auto_commit_on_interrupt = true
```

#### Disable Checkpoints

```toml
[backup]
checkpoint_enabled = false
```

**Trade-off**:
- ✅ Cleaner git history (single commit at end)
- ❌ Ctrl+C loses uncommitted work (requires manual recovery)

#### Custom Checkpoint Interval

```toml
[backup]
checkpoint_interval = 100  # Commit every 100 videos
```

**Guidelines**:
- **Small channels** (<500 videos): `checkpoint_interval = 100`
- **Medium channels** (500-2000 videos): `checkpoint_interval = 50` (default)
- **Large channels** (>2000 videos): `checkpoint_interval = 25`

### Manual Recovery

If you disabled `auto_commit_on_interrupt`, you'll have uncommitted changes after Ctrl+C.

#### Check Status

```bash
cd my-archive
git status
```

Output:
```
On branch master
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        new file:   videos/2026/02/07_example-video/metadata.json
        new file:   videos/2026/02/08_another-video/metadata.json
        ...
```

#### Option 1: Commit Partial Work (Recommended)

```bash
# Regenerate TSVs from existing metadata.json files
annextube export --output-dir .

# Stage all changes
git add .

# Commit with descriptive message
git commit -m "Partial backup: interrupted at 173 videos"

# Resume backup (incremental mode skips existing)
annextube backup --output-dir .
```

#### Option 2: Discard Uncommitted Work

**⚠️ WARNING: This deletes all processed videos!**

```bash
# Reset to last commit (DESTRUCTIVE)
git reset --hard HEAD

# Start backup from scratch
annextube backup --output-dir .
```

Only use this if you want to completely start over.

### Best Practices

1. **Enable checkpoints** (default): Safest option for large backups
2. **Enable auto-commit on interrupt** (default): Ctrl+C is safe
3. **Use incremental mode** (default): Automatic resume capability
4. **Monitor disk space**: Checkpoints create more commits (minimal overhead)
5. **Test recovery**: Interrupt a test backup and verify resume works

### FAQ

**Q: How do checkpoints affect repository size?**

A: Minimal impact. Git commits are small (just metadata), and content is deduplicated. Each checkpoint adds ~1KB to git history.

**Q: Can I push checkpoints to a remote git repository?**

A: Yes! Checkpoints are regular git commits. Push with `git push` to backup your progress remotely.

**Q: What if my system crashes mid-checkpoint?**

A: Files on disk are safe. The checkpoint commit might be incomplete, but you can manually commit or let the next checkpoint handle it.

**Q: Do checkpoints work with playlists?**

A: Yes! Playlist backups also support checkpoints with the same configuration.

**Q: How long does a checkpoint take?**

A: Typically 1-3 seconds (TSV regeneration + git commit). Negligible overhead for large backups.

---

## Advanced Scenarios

### Recovering from System Crash

If your system crashed during a backup:

1. **Boot system** and navigate to archive directory
2. **Check git status**: `git status`
3. **Commit if safe**:
   ```bash
   annextube export --output-dir .
   git add .
   git commit -m "Recovery: commit work before crash"
   ```
4. **Resume backup**: `annextube backup --output-dir .`

### Parallel Backups (Multiple Channels)

If running multiple backups in parallel:

```bash
# Terminal 1: Backup channel A
annextube backup --output-dir archive-A

# Terminal 2: Backup channel B (different directory!)
annextube backup --output-dir archive-B
```

**⚠️ Never run parallel backups in the same directory** - git conflicts will occur!

For multi-channel collections, use sequential backups or separate machines.

### Quota Exceeded + Ctrl+C

If you press Ctrl+C during quota wait:

```
INFO - Sleeping until quota reset (5h 23m from now). Press Ctrl+C to cancel.
^C
WARNING - Sleep interrupted by user (Ctrl+C)
WARNING - Backup interrupted by user (Ctrl+C)
INFO - Auto-committing partial progress (847 videos processed)...
[Commit created]
```

**Resume later**: When quota resets, run `annextube backup` again. It will:
1. Skip the 847 already-processed videos
2. Continue from video 848 onwards
3. Use remaining quota for new videos

---

## Monitoring and Logging

### Check Quota Usage

annextube logs quota usage estimates:

```
INFO - Estimated quota cost: 10,000 units (1,000 videos × 10 units)
INFO - Fetching enhanced metadata for 50 videos (500 quota units)
```

**Monitor your quota**:
- [Google Cloud Console > Quotas](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)
- View daily usage and remaining quota

### Checkpoint Logging

When checkpoints occur:

```
INFO - Processing video 50/300: Example Video Title
INFO - Checkpoint: 50/300 videos processed
INFO - Generating TSV metadata files
INFO - Successfully committed: Checkpoint: @channel (50/300 videos)
```

### Interruption Logging

When Ctrl+C is pressed:

```
^C
WARNING - Backup interrupted by user (Ctrl+C)
INFO - Auto-committing partial progress (173 videos processed)...
INFO - Generating TSV metadata files
INFO - Successfully committed: Partial backup (interrupted): @channel (173 videos)
INFO - Partial progress committed successfully
```

---

## Summary

### Key Points

1. **Quota exceeded**: Automatically waits until midnight PT and retries
2. **Interruptions**: Zero data loss - all processed videos committed
3. **Checkpoints**: Auto-save every 50 videos (configurable)
4. **Resume**: Incremental mode automatically skips existing videos
5. **Ctrl+C is safe**: Auto-commits partial work before exiting

### Default Configuration (Recommended)

```toml
[backup]
checkpoint_interval = 50
checkpoint_enabled = true
auto_commit_on_interrupt = true

[api]
quota_auto_wait = true
quota_max_wait_hours = 48
```

### Getting Help

If you encounter issues:

1. Check logs for detailed error messages
2. Run `git status` to see uncommitted work
3. Use `annextube export` to regenerate TSVs
4. Consult [Troubleshooting Guide](../troubleshooting)
5. Report bugs at [GitHub Issues](https://github.com/datalad/annextube/issues)
