---
title: "Troubleshooting"
description: "Common issues and solutions for annextube"
weight: 100
---

# Troubleshooting

This guide covers common issues you might encounter when using annextube and how to resolve them.

## yt-dlp Challenge Solver Version Errors

### Symptom

When running `annextube backup`, you see errors like:

```
yt_dlp: [youtube] [jsc:deno] Challenge solver lib script version 0.3.2 is not supported
(source: python package, variant: ScriptVariant.MINIFIED, supported version: 0.4.0)
```

### Cause

This error occurs when yt-dlp's JavaScript challenge solver dependencies are outdated. The challenge solver is used to bypass YouTube's bot detection mechanisms.

### Solution

Upgrade yt-dlp with all its default dependencies:

```bash
python3 -m pip install -U "yt-dlp[default]"
```

Or if using uv:

```bash
uv pip install -U "yt-dlp[default]"
```

**Note:** The `[default]` extra is important - it includes dependencies like the Deno JavaScript runtime needed for the challenge solver.

### Prevention

If you're installing annextube in a fresh environment, ensure you're using a recent version:

```bash
pip install -U "annextube[devel]"  # Includes recent yt-dlp>=2026.2.0
```

The project's `pyproject.toml` specifies `yt-dlp>=2026.2.0`, which includes the required challenge solver version, but existing installations may have outdated dependencies that need manual updating.

---

## YouTube API Quota Exceeded

### Symptom

When running `annextube backup`, you see errors like:

```
WARNING - YouTube API quota exceeded: quotaExceeded
WARNING - Quota resets at: 2026-02-08 00:00:00 PST
INFO - Sleeping until quota reset (9h 33m from now). Press Ctrl+C to cancel.
```

### Cause

YouTube Data API has a daily quota limit (default: 10,000 units per day). Each video's enhanced metadata costs 10 units, so you can fetch metadata for ~1,000 videos per day before hitting the quota. Comments cost additional quota (1 unit per 100 comment threads).

The quota resets at **midnight Pacific Time** (either PST UTC-8 or PDT UTC-7 depending on daylight saving time).

### Solution (Automatic)

**By default**, annextube automatically handles quota exceeded errors:

1. **Detects quota exceeded** in YouTube API responses
2. **Calculates next quota reset** (midnight Pacific Time)
3. **Sleeps with progress updates** every 30 minutes
4. **Automatically retries** when quota resets
5. **Supports Ctrl+C** to abort the wait

Example output:
```
2026-02-07 14:26:59 - WARNING - YouTube API quota exceeded
2026-02-07 14:26:59 - WARNING - Quota resets at: 2026-02-08 00:00:00 PST
2026-02-07 14:26:59 - INFO - Sleeping until quota reset (9h 33m from now). Press Ctrl+C to cancel.
2026-02-07 14:56:59 - INFO - Quota resets in 9h 3m
2026-02-07 15:26:59 - INFO - Quota resets in 8h 33m
...
2026-02-08 00:00:00 - INFO - Quota reset time reached. Resuming operations.
```

### Configuration

You can configure quota handling behavior in `.annextube/config.toml`:

```toml
[backup]
# Auto-wait for quota reset (default: true)
auto_commit_on_interrupt = true

# Maximum hours to wait before giving up (default: 48)
# Set lower to abort if quota reset is too far away
max_wait_hours = 24
```

**To disable auto-wait** (abort immediately on quota exceeded):
```python
# In Python code:
from annextube.lib.quota_manager import QuotaManager

quota_manager = QuotaManager(enabled=False)
```

### Workarounds

**Option 1: Use yt-dlp only** (no API key)
- Don't set `YOUTUBE_API_KEY` environment variable
- annextube will fall back to yt-dlp for all metadata
- Slower, no enhanced metadata (license, recording location, etc.)
- No quota limits

**Option 2: Request quota increase**
- Go to [Google Cloud Console](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)
- Request quota increase for YouTube Data API v3
- Can request up to 1,000,000 units/day (paid tier)

**Option 3: Split into multiple days**
- Use `--limit` to process fewer videos per day
- Example: `annextube backup --limit 800` (leaves 200 units buffer)

---

## Backup Interrupted (Ctrl+C, Crash, or Quota)

### Symptom

You interrupted a backup operation (Ctrl+C, system crash, quota exceeded, etc.) and want to know:
- What data was lost?
- How to resume?
- Should you commit or reset changes?

### What Happens on Interruption

**✅ Safe on disk** (immediately written during processing):
- `metadata.json` files for all processed videos
- Git-annex URL links (staged in git, ready to commit)
- Downloaded content (videos, captions, thumbnails)
- TSV files (if checkpoint commits were enabled)

**❌ Lost in memory** (not critical):
- Summary statistics counters (only affects logging)

**Key insight**: All actual work is preserved on disk, just not yet committed to git history.

### Automatic Recovery (Default Behavior)

**By default**, annextube auto-commits partial progress when you press Ctrl+C:

```
^C
WARNING - Backup interrupted by user (Ctrl+C)
INFO - Auto-committing partial progress (127 videos processed)...
INFO - Generating TSV metadata files
INFO - Partial progress committed successfully
```

This creates a commit like:
```
Partial backup (interrupted): https://youtube.com/@channel (127 videos)
```

**To resume**, just run the backup command again:
```bash
annextube backup --output-dir /path/to/archive
```

The incremental mode automatically skips already-processed videos (checks `videos.tsv`).

### Manual Recovery (If Auto-Commit Disabled)

If you disabled `auto_commit_on_interrupt = false`, you'll have uncommitted changes:

**Check status:**
```bash
cd /path/to/archive
git status
```

**Option 1: Commit partial work** (recommended)
```bash
# Regenerate TSVs from existing metadata.json files
annextube export --output-dir .

# Commit everything
git add .
git commit -m "Partial backup: interrupted at 127 videos"

# Resume backup (incremental mode skips existing)
annextube backup --output-dir .
```

**Option 2: Discard uncommitted work** (only if you want to start over)
```bash
# WARNING: This deletes all staged files!
git reset --hard HEAD

# Start backup from scratch
annextube backup --output-dir .
```

### Checkpoint Commits (Periodic Auto-Save)

**By default**, annextube creates checkpoint commits every 50 videos:

```
Commit history:
a1b2c3d Checkpoint: @channel (50/300 videos)
e4f5g6h Checkpoint: @channel (100/300 videos)
i7j8k9l Checkpoint: @channel (150/300 videos)
[User presses Ctrl+C]
m0n1o2p Partial backup (interrupted): @channel (173 videos)
```

**Benefits:**
- No data loss on interruption
- Progress visible in git history
- TSVs updated incrementally (web UI works immediately)
- Resume capability via incremental mode

**Configure checkpoint interval:**
```toml
# .annextube/config.toml
[backup]
checkpoint_interval = 50        # Commit every N videos (default: 50)
checkpoint_enabled = true       # Enable checkpoints (default: true)
auto_commit_on_interrupt = true # Auto-commit on Ctrl+C (default: true)
```

**Disable checkpoints** (single commit at end):
```toml
[backup]
checkpoint_enabled = false
```

### FAQ

**Q: If I interrupt at video 200/300, how many videos do I need to reprocess?**

A: None! The incremental mode checks `videos.tsv` and skips all existing videos. You'll only process new videos (201-300).

**Q: Why are my staged files not showing in the web UI?**

A: The web UI reads from `videos.tsv`, which is only generated when you:
1. Run `annextube export` (regenerates from metadata.json files)
2. Let a checkpoint commit complete (auto-generates TSVs)
3. Complete the backup (final TSV generation)

**Q: Can I commit manually without regenerating TSVs?**

A: Yes, but the web UI won't work until you run `annextube export`. The next backup will regenerate TSVs automatically.

---

## More Troubleshooting Topics

(To be added as issues are encountered and documented)
