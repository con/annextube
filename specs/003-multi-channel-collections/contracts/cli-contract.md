# CLI Contract: Multi-Channel Collections

**Version**: 1.0.0
**Date**: 2026-03-21
**Purpose**: Define command-line interface contract for multi-channel collection commands

## Overview

These commands extend the annextube CLI (see [001 CLI contract](../../001-youtube-backup/contracts/cli-contract.md)) with collection management capabilities. All commands follow the same conventions: Unix philosophy, meaningful exit codes, structured logging, idempotent operations.

## Commands

### 1. aggregate (IMPLEMENTED)

Discover channel archives and generate a collection-level summary.

**Implementation**: `annextube/cli/aggregate.py`

**Usage**:
```bash
annextube aggregate [DIRECTORY] [OPTIONS]
```

**Arguments**:
```
DIRECTORY     Root directory to scan (default: current directory)
```

**Options**:
```
--depth N     Discovery depth for channel.json scanning (1-3, default: 1)
--output FILE Output file path (default: DIRECTORY/channels.tsv)
--force       Overwrite existing channels.tsv
```

**Behavior**:
1. Scan `DIRECTORY` for `channel.json` files using glob patterns up to `--depth` levels
2. For each discovered channel:
   - Parse `channel.json` for metadata (channel_id, name, custom_url, etc.)
   - Compute archive statistics from `videos/videos.tsv` (video count, date range)
3. Sort channels by title (case-insensitive)
4. Write `channels.tsv` with one row per channel

**Output** (stdout):
```
Generated channels.tsv with 3 channel(s)

Channels discovered:
  - Andriy Popyk (ch-apopyk): 287 videos
  - DataLad (ch-datalad): 156 videos
  - ReproNim (ch-repronim): 42 videos
```

**Exit Codes**:
- `0`: Success (channels found and TSV generated)
- `0`: No channels found (informational message, no file created)
- `1`: Error (file exists without --force, I/O error)

**Edge Cases**:
- No `channel.json` files found: prints message, exits 0, does not create empty file
- `channel.json` exists but is malformed: logs warning, skips channel, continues
- `videos/videos.tsv` missing for a channel: logs warning, archive_stats will be empty (zeros)
- Output file exists without `--force`: prints error to stderr, aborts

---

### 2. export --channel-json (IMPLEMENTED)

Generate `channel.json` metadata file for a single-channel archive.

**Implementation**: `annextube/cli/export.py` (flag on existing `export` command)

**Usage**:
```bash
annextube export --channel-json [--output-dir DIR]
```

**Behavior**:
1. Read channel metadata from the archive's config and cached YouTube data
2. Compute `archive_stats` from local `videos/videos.tsv`
3. Write `channel.json` at the archive root

**Output** (stdout):
```
[ok] Generated channel.json
```

**Exit Codes**:
- `0`: Success
- `1`: Not a single-channel archive, or no source configured

**Notes**:
- Only works within a single-channel archive (not at collection level)
- Generates the file that `aggregate` later discovers

---

### 3. collection add (NEW -- Phase 2)

Add a new YouTube channel to an existing collection.

**Usage**:
```bash
annextube collection add <URL> [OPTIONS]
```

**Arguments**:
```
URL           YouTube channel URL (e.g., https://www.youtube.com/@ChannelName)
```

**Options**:
```
--name NAME        Override the subdataset directory name (default: derived from @handle)
--no-backup        Skip the initial backup (init only)
--output-dir DIR   Collection directory (default: current directory)
```

**Behavior**:
1. Extract channel handle from URL (e.g., `@ChannelName` -> `ChannelName`)
2. Check that target directory does not already exist; fail if it does
3. Read `[collection]` defaults from collection's `.annextube/config.toml` (if present)
4. Create DataLad subdataset: `datalad create -d . <name>`
5. Initialize channel archive: `annextube init <url>` with collection defaults
6. If `common_config` configured: embed common config into channel
7. Unless `--no-backup`:
   - Run initial backup: `annextube backup`
   - Generate channel.json: `annextube export --channel-json`
8. Save at collection level: `datalad save -m "Add @handle channel"`

**Output** (stdout):
```
Creating channel archive: ChannelName/
  [ok] DataLad subdataset created
  [ok] annextube initialized with collection defaults
  [ok] Common config embedded
  [ok] Initial backup complete (42 videos)
  [ok] channel.json generated
  [ok] Saved at collection level

Channel @ChannelName added to collection.
Run 'annextube aggregate --force' to update channels.tsv.
```

**Exit Codes**:
- `0`: Success (channel created and backed up)
- `1`: Directory already exists
- `3`: Network error during backup
- `6`: Collection config error

**Edge Cases**:
- Directory name conflict: fails with clear error, suggests `--name` override
- No `[collection]` config section: proceeds with annextube defaults (no collection-specific defaults applied)
- `--no-backup`: creates and initializes only, no `channel.json` generated (user must run backup and export separately)
- URL without @handle: requires `--name` flag

---

### 4. collection backup (NEW -- Phase 2)

Batch update all channels in a collection.

**Usage**:
```bash
annextube collection backup [DIRECTORY] [OPTIONS]
```

**Arguments**:
```
DIRECTORY     Collection directory (default: current directory)
```

**Options**:
```
--parallel N   Update up to N channels concurrently (default: 1, sequential)
--save         Save changes at collection level after all updates
--push         Push to configured remote after updates (requires --save)
```

**Behavior**:
1. Discover all channel subdatasets containing `.annextube/config.toml`
2. For each channel (sequentially by default, or up to N in parallel):
   a. If channel has uncommitted changes: `datalad save -m "Pre-backup state"`
   b. Run backup: `annextube backup`
   c. Run export: `annextube export --channel-json`
   d. Record result (success/failure with reason)
   e. On failure: log error, continue to next channel
3. If `--save`: run `annextube aggregate --force` then `datalad save -d . -m "Batch update"`
4. If `--push`: `datalad push -r` to configured remote

**Output** (stdout):
```
Backing up 3 channels in /path/to/collection...

  [1/3] @apopyk... ok (3 new videos)
  [2/3] @datalad... ok (1 new video)
  [3/3] @broken... FAILED: Network timeout

Backup complete: 2/3 channels updated successfully

  [ok] @apopyk (3 new videos)
  [ok] @datalad (1 new video)
  [FAIL] @broken - Network timeout after 3 retries

[ok] Collection saved
[ok] Pushed to remote: datalad-public
```

**Exit Codes**:
- `0`: All channels updated successfully
- `1`: One or more channels failed (but all were attempted)

**Edge Cases**:
- All channels fail: exits 1, reports all failures
- `--push` without `--save`: error (must save before pushing)
- `--parallel N` with N > channel count: runs all channels, no issue
- No channels found: prints message, exits 0
- Interrupted (Ctrl+C): current channel may be partially updated; next run resumes cleanly

---

## Command Group Structure

The `collection` commands are grouped under a Click command group:

```
annextube
├── aggregate           # Standalone command (already exists)
├── backup              # Single-channel backup (already exists)
├── export              # Single-channel export with --channel-json (already exists)
├── collection          # Command group (new)
│   ├── add             # Add channel to collection
│   └── backup          # Batch backup collection
└── ...                 # Other existing commands
```

## Configuration

The `collection` commands read the `[collection]` section from `.annextube/config.toml` at the collection root. See [data-model.md](../data-model.md) for the full schema.

Commands that operate on individual channels (e.g., `annextube backup`, `annextube export`) are unchanged and continue to read only the per-channel config.
