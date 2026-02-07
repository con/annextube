# Multi-Channel Collections Design

**Date**: 2026-02-06
**Status**: Draft
**Purpose**: Design composable channel collections that work with existing web UI

## Motivation

Currently annextube creates a flat structure suitable for archiving a single channel or mixed sources. For users archiving multiple distinct channels, we need a composable structure that:

1. Organizes channels into separate directories for clarity
2. Provides per-channel metadata and summaries
3. Supports a top-level overview across all channels
4. Works with the existing web UI (which already supports channel filtering)
5. Remains backward compatible with single-channel archives

**Inspiration**: The [mykrok](file:///home/yoh/proj/mykrok/mykrok-mine) project structure with `athletes.tsv` at root and per-athlete directories.

## Current Structure (Single Archive)

```
archive/
├── .annextube/
│   └── config.toml          # Sources configuration
├── .git/
├── videos/
│   └── {path}/
│       └── metadata.json    # Per-video metadata
├── playlists/
│   └── {playlist_id}/
│       └── playlist.json
├── videos.tsv               # Summary of all videos
└── playlists.tsv            # Summary of all playlists
```

**Current behavior**:
- All sources (channels/playlists) mixed in same `videos/` directory
- Web UI loads `videos.tsv` and filters by `channel_id` field
- Works well for single channel or small mixed collections

## Proposed Structure (Multi-Channel Collections)

### Collection Repository (Aggregation Level)

```
collection/                   # Git repository with submodules
├── .git/
│   └── modules/              # Git submodule metadata
│       ├── ch-apopyk/
│       └── ch-datalad/
├── .gitmodules               # Submodule configuration
├── channels.tsv              # Generated summary (discover from */channel.json)
├── ch-apopyk/                # Git submodule → independent datalad dataset
│   ├── .annextube/
│   │   └── config.toml       # Channel-specific config
│   ├── .git/                 # Independent git repo
│   ├── channel.json          # Channel metadata (used for discovery)
│   ├── videos/
│   │   └── {path}/
│   │       └── metadata.json
│   ├── playlists/
│   ├── videos.tsv            # Channel-specific video summary
│   └── playlists.tsv
├── ch-datalad/               # Git submodule → independent datalad dataset
│   ├── .annextube/
│   │   └── config.toml
│   ├── .git/
│   ├── channel.json
│   ├── videos/
│   ├── videos.tsv
│   └── playlists.tsv
├── org-datalad/              # Optional: nested grouping
│   ├── ch-main/              # Discovered via */*/channel.json
│   │   └── channel.json
│   └── ch-demos/
│       └── channel.json
└── web/                      # Generated web UI
    └── index.html
```

**Key Architecture Points**:

1. **Each channel is an independent datalad dataset (git repository)**
   - Has its own `.annextube/config.toml`
   - Has its own git history
   - Can be used standalone or as part of collection

2. **Collection repo uses git submodules**
   - Channels are added with `git submodule add`
   - No config needed at aggregation level
   - Discovery-based: scan for `*/channel.json` or `*/*/channel.json`

3. **Directory naming is flexible**
   - Pattern doesn't matter - discovery finds `channel.json` files
   - Users can organize however they want (flat, nested, by org, etc.)
   - Example patterns:
     - `ch-apopyk/`, `ch-datalad/` (flat)
     - `org-datalad/ch-main/`, `org-datalad/ch-demos/` (nested)
     - `ukraine/apopyk/`, `research/datalad/` (custom)

### Benefits of This Architecture

| Aspect | Benefit |
|--------|---------|
| **Independence** | Each channel is a complete, standalone archive |
| **Git operations** | Can work on single channel, push/pull independently |
| **Disk navigation** | Clear separation by channel directory |
| **Scalability** | Parallel updates (`git submodule foreach`) |
| **Flexibility** | Users choose directory structure (flat, nested, grouped) |
| **mykrok similarity** | Matches pattern with discovery-based approach |
| **No migration needed** | Existing archives work unchanged, just add to collection |

## Data Model

### channels.tsv (Root Level)

Top-level summary of all channels in the collection (similar to `athletes.tsv` in mykrok).

**Columns**:
```tsv
channel_id	title	custom_url	description	subscriber_count	video_count	playlist_count	total_videos_archived	first_video_date	last_video_date	last_sync	channel_dir
```

**Example**:
```tsv
channel_id	title	custom_url	description	subscriber_count	video_count	playlist_count	total_videos_archived	first_video_date	last_video_date	last_sync	channel_dir
UCZXGJjgg0cB5vqd5aVcJ0pQ	Andriy Popyk	@apopyk	Ukrainian programming tutorials	15234	287	12	287	2018-03-15	2026-01-20	2026-02-06T10:30:00Z	ch-apopyk
UC1234567890ABCDEF	DataLad	@datalad	Data management	8543	156	5	156	2019-06-01	2025-12-15	2026-02-06T10:35:00Z	ch-datalad
```

**Purpose**:
- Quick overview of all channels in collection
- Web UI can display channels grid/list
- Efficient loading without parsing all channel.json files

**Generation Algorithm** (for `aggregate` command):
1. Discover all `channel.json` files up to specified depth
2. For each channel:
   - Parse `channel.json` for metadata
   - Load `{channel_dir}/videos.tsv` to compute archive stats:
     - `total_videos_archived`: Row count
     - `first_video_date`: Min of `published_at` column
     - `last_video_date`: Max of `published_at` column
   - Store relative `channel_dir` path (e.g., `ch-apopyk`, `org-datalad/ch-main`)
3. Sort by channel title
4. Write to `channels.tsv`

### channel.json (Per-Channel)

Detailed metadata for a single channel.

**Location**: `ch-{name}/channel.json`

**Schema**:
```json
{
  "channel_id": "UCZXGJjgg0cB5vqd5aVcJ0pQ",
  "title": "Andriy Popyk",
  "description": "Ukrainian programming tutorials and tech talks",
  "custom_url": "@apopyk",
  "subscriber_count": 15234,
  "video_count": 287,
  "view_count": 1250000,
  "avatar_url": "https://yt3.ggpht.com/...",
  "banner_url": "https://yt3.ggpht.com/...",
  "country": "Ukraine",
  "created_at": "2018-03-15T00:00:00Z",
  "keywords": ["programming", "ukrainian", "tutorials"],
  "playlists": ["PLxxxxxx", "PLyyyyyy"],
  "featured_channels": ["UC1234567890ABCDEF"],
  "social_links": {
    "twitter": "https://twitter.com/apopyk",
    "github": "https://github.com/apopyk"
  },
  "last_sync": "2026-02-06T10:30:00Z",
  "fetched_at": "2026-02-06T10:30:00Z",
  "archive_stats": {
    "total_videos_archived": 287,
    "first_video_date": "2018-03-15",
    "last_video_date": "2026-01-20",
    "total_duration_seconds": 145230,
    "total_size_bytes": 25600000000
  }
}
```

**Notes**:
- Most fields match existing Channel model from data-model.md
- `archive_stats` is computed from local archive (not YouTube API)
- Updated during each backup/export run

## Configuration

### Architecture: Decentralized Configuration

**Collection level**: NO configuration file needed
- Discovery-based: scan for `*/channel.json` (or deeper)
- No `.annextube/` directory at collection root
- Just git with submodules

**Channel level**: Each channel has its own `.annextube/config.toml`
```toml
# ch-apopyk/.annextube/config.toml

[[sources]]
url = "https://www.youtube.com/@apopyk"
type = "channel"
enabled = true

[components]
metadata = true
videos = true
comments_depth = null
captions = true
thumbnails = true

[organization]
video_path_pattern = "{year}/{month}/{date}_{sanitized_title}"
```

### Workflow Examples

**Creating a multi-channel collection**:
```bash
# 1. Create collection repository
mkdir my-collection && cd my-collection
git init

# 2. Add channel archives as submodules
mkdir ch-apopyk && cd ch-apopyk
annextube init https://www.youtube.com/@apopyk
annextube backup
cd ..
git submodule add ./ch-apopyk ch-apopyk

mkdir ch-datalad && cd ch-datalad
annextube init https://www.youtube.com/@datalad
annextube backup
cd ..
git submodule add ./ch-datalad ch-datalad

# 3. Generate collection summary
annextube aggregate .
# Creates channels.tsv from discovered */channel.json

# 4. Generate web UI
annextube generate-web .
```

**Updating a collection**:
```bash
# Update all channels
git submodule foreach 'annextube backup'

# Regenerate collection summary
annextube aggregate .
```

**Adding an existing channel archive**:
```bash
# Add as submodule
git submodule add https://github.com/user/ch-example

# Regenerate summary
annextube aggregate .
```

## Web UI Integration

### Current Web UI Behavior

The existing web UI:
- Loads `videos.tsv` from archive root
- Has channel filtering by `channel_id` field
- Shows video grid with thumbnails, metadata

### Required Web UI Changes

1. **Detection**: Check for `channels.tsv` at root
   ```javascript
   const response = await fetch('channels.tsv');
   const isMultiChannel = response.ok;
   ```

2. **Multi-channel mode**:
   - Load `channels.tsv` for overview page
   - Display channels grid (similar to athletes in mykrok)
   - On channel click: Load `{channel_dir}/videos.tsv`
   - **No aggregated loading** - with ~10 channels, parallel loading is fast:
     ```javascript
     const channelVideos = await Promise.all(
       channels.map(ch => fetch(`${ch.channel_dir}/videos.tsv`))
     );
     ```
   - Breadcrumb: Home > Channel Name > Video

3. **Single-channel mode**:
   - Load `videos.tsv` (existing behavior)
   - No channels overview

**Performance**: For 10 channels with 200 videos each, parallel loading of 10 TSV files (~500KB total) takes <200ms on decent connection. No aggregation needed.

### UX Flow (Multi-Channel)

```
Home Page (Overview)
├── Display channels from channels.tsv
│   ├── Channel card: Avatar, Title, Stats
│   └── Click → Channel Page
│
Channel Page
├── Load ch-{name}/videos.tsv
├── Display videos grid (existing component)
└── Filter/search within channel
│
Video Page (existing)
```

## Implementation Plan

### Phase 1: Discovery & Aggregation (Sufficient for Start)

**Goal**: Support existing channel archives in collection structure with discovery-based aggregation.

#### 1.1: Add `aggregate` Command

```bash
annextube aggregate [DIRECTORY] [OPTIONS]
```

**Options**:
- `--depth N`: Discovery depth for `*/channel.json` (default: 1, max: 3)
- `--output FILE`: Output file path (default: `channels.tsv`)
- `--force`: Overwrite existing `channels.tsv`

**Behavior**:
1. Scan directory for `channel.json` files up to specified depth
2. Parse each `channel.json` for metadata
3. Compute `archive_stats` from each channel's `videos.tsv`
4. Generate `channels.tsv` with summary

**Example**:
```bash
# Flat structure: */channel.json
annextube aggregate . --depth 1

# Nested structure: */*/channel.json
annextube aggregate . --depth 2
```

#### 1.2: Add/Update `channel.json` Schema

Add to data model documentation and generate during `export`:
- Channel metadata fields (existing from data-model.md)
- `archive_stats` computed from local archive

#### 1.3: Modify `export` Command

Add `--channel-json` flag to generate `channel.json`:
```bash
annextube export --channel-json
```

Generates `channel.json` at archive root with:
- Channel metadata from first source in config
- `archive_stats` computed from `videos.tsv`

#### 1.4: Update Web UI

1. Detect multi-channel mode (check `channels.tsv`)
2. Add channels overview page
3. Load per-channel `videos.tsv` on demand

**Outcome**: Users can:
1. Create individual channel archives independently
2. Organize them in collection repository (git submodules)
3. Run `annextube aggregate` to generate overview
4. Web UI displays multi-channel collection properly

### Phase 2: Polish & Automation (Future)

1. Auto-run `aggregate` in `generate-web` if `channels.tsv` missing
2. Add `--aggregate` flag to `backup` command
3. Better error handling for malformed `channel.json`
4. Documentation and examples

### Phase 3: Advanced Features (Optional)

1. Nested grouping visualization in web UI
2. Cross-channel search/filtering
3. Collection-level statistics
4. Automatic submodule discovery and init

## Design Decisions

### 1. Channel Directory Naming
**Decision**: User-defined, discovery doesn't care about folder names
- Users can use any pattern: `ch-apopyk/`, `ukraine/apopyk/`, etc.
- Discovery scans for `*/channel.json` regardless of path
- Folder name stored in `channels.tsv` for web UI navigation

### 2. Collection-Level Configuration
**Decision**: No configuration file at collection level
- Pure discovery-based approach
- Each channel is independent with own `.annextube/config.toml`
- Collection repo is just git with submodules

### 3. Aggregated videos.tsv
**Decision**: Not needed for reasonable collection sizes (<50 channels)
- Parallel loading of `*/videos.tsv` is fast enough
- `channels.tsv` tells web UI which directories to load
- Avoids data duplication and sync issues

### 4. Discovery Depth
**Decision**: Support depth 1-3 with default of 1
- Depth 1: `*/channel.json` (flat structure)
- Depth 2: `*/*/channel.json` (one level of grouping)
- Depth 3: `*/*/*/channel.json` (two levels, e.g., `country/org/channel/`)
- Beyond depth 3 is edge case, can be added later if needed

### 5. Backward Compatibility
**Decision**: Full backward compatibility
- Single-channel archives work unchanged
- Web UI auto-detects: `channels.tsv` exists → multi-channel mode
- No migration needed - just add existing archives to collection

## Complete Workflow Example

### Scenario: Archive 3 Ukrainian Tech Channels

```bash
# 1. Create collection repository
mkdir ukraine-tech-channels
cd ukraine-tech-channels
git init
echo "# Ukrainian Tech Channels Collection" > README.md
git add README.md
git commit -m "Initial commit"

# 2. Create first channel archive
mkdir ch-apopyk
cd ch-apopyk
annextube init https://www.youtube.com/@apopyk
annextube backup
annextube export --channel-json  # Generate channel.json
cd ..

# 3. Add as git submodule
git submodule add ./ch-apopyk ch-apopyk
git commit -m "Add Andriy Popyk channel"

# 4. Create second channel archive
mkdir ch-dou
cd ch-dou
annextube init https://www.youtube.com/@DOU_UKRAINE
annextube backup
annextube export --channel-json
cd ..
git submodule add ./ch-dou ch-dou
git commit -m "Add DOU channel"

# 5. Create third channel archive
mkdir ch-cursor
cd ch-cursor
annextube init https://www.youtube.com/@CursorEdu
annextube backup
annextube export --channel-json
cd ..
git submodule add ./ch-cursor ch-cursor
git commit -m "Add Cursor Education channel"

# 6. Generate collection summary
annextube aggregate .
# Creates channels.tsv with 3 channels

# 7. Generate web UI
annextube generate-web .
# Web UI detects channels.tsv and creates multi-channel interface

# 8. Open in browser
firefox web/index.html
# Shows: Overview page with 3 channels → Click channel → Videos grid
```

### Result Structure

```
ukraine-tech-channels/
├── .git/
├── .gitmodules
├── README.md
├── channels.tsv              # Generated by aggregate
├── ch-apopyk/                # Submodule
│   ├── .annextube/
│   ├── .git/
│   ├── channel.json          # Generated by export --channel-json
│   ├── videos/
│   ├── videos.tsv
│   └── playlists.tsv
├── ch-dou/                   # Submodule
│   ├── .annextube/
│   ├── .git/
│   ├── channel.json
│   └── ...
├── ch-cursor/                # Submodule
│   └── ...
└── web/                      # Generated web UI
    ├── index.html            # Entry point with channel overview
    └── assets/
```

### Updating Collection

```bash
# Update all channels (parallel)
git submodule foreach 'annextube backup'

# Regenerate summaries
git submodule foreach 'annextube export --channel-json'
annextube aggregate .

# Commit updates
git add .
git commit -m "Update all channels $(date +%Y-%m-%d)"
```

### Adding Existing Archive

```bash
# Someone shared their archive on GitHub
git submodule add https://github.com/user/ch-example
annextube aggregate .  # Rediscover and regenerate channels.tsv
```

## Comparison with mykrok Structure

**mykrok pattern**:
```
mykrok-mine/
├── athletes.tsv                    # Summary (all athletes)
├── athl=yhalchenko/
│   ├── athlete.json                # Athlete metadata
│   ├── avatar.jpg
│   ├── gear.json
│   └── ses=20230613T113607/        # Session directories
│       ├── activity.json
│       └── ...
└── web/
```

**annextube pattern** (proposed):
```
archive/
├── channels.tsv                    # Summary (all channels) ← matches athletes.tsv
├── ch-apopyk/                      # ← matches athl= pattern
│   ├── channel.json                # ← matches athlete.json
│   ├── videos/                     # ← analogous to sessions
│   │   └── 2024/01/...
│   └── videos.tsv
└── web/
```

**Key similarities**:
- Top-level TSV for overview
- Per-entity directories with metadata JSON
- Hierarchical organization
- Static web UI in `web/`

**Differences**:
- Channels have nested `videos/` directory (flatter than nested sessions)
- Additional `playlists/` concept
- Per-channel TSV summaries

## References

- [mykrok structure](file:///home/yoh/proj/mykrok/mykrok-mine)
- [annextube data-model.md](file:///home/yoh/proj/annextube/specs/001-youtube-backup/data-model.md)
- [Constitution Principle XI: Storage Simplicity](file:///home/yoh/proj/annextube/.specify/memory/constitution.md)
