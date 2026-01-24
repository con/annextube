# Quick Start Guide: annextube

**Goal**: Get your first YouTube channel archived in 15 minutes

This guide walks you through creating your first YouTube archive, from installation to browsing videos offline.

## Prerequisites

- **Git** (2.20+)
- **git-annex** (8.0+)
- **Python** (3.10+)
- **pip** or **uv** (Python package manager)

**Installation check**:
```bash
git --version
git-annex version
python3 --version
```

## Step 1: Install annextube

### Using pip
```bash
pip install annextube
```

### Using uv (faster)
```bash
uv pip install annextube
```

### From source (development)
```bash
git clone https://github.com/yourusername/annextube.git
cd annextube
uv pip install -e .
```

**Verify installation**:
```bash
annextube --version
```

Expected output: `annextube version 1.0.0`

---

## Step 2: Create Your First Archive

Create a directory and initialize the archive:

```bash
mkdir ~/my-youtube-archive
cd ~/my-youtube-archive
annextube init
```

**What this does**:
- Initializes git repository in current directory
- Initializes git-annex with URL backend (for video URLs)
- Creates `.annextube/config.toml` template with common settings
- Configures file tracking (.gitattributes):
  - Metadata files (*.json, *.tsv, *.md, *.vtt) → git
  - Media files (*.mp4, *.webm, *.jpg, *.png) → git-annex

**Output**:
```
Initialized YouTube archive repository in current directory
Git-annex backend: URL (for video URLs)
Tracking configuration:
  - *.json, *.tsv, *.md, *.vtt → git
  - *.mp4, *.webm, *.jpg, *.png → git-annex

Template configuration created: .annextube/config.toml
Edit this file to configure channels, playlists, and filters.

Next steps:
  1. Edit .annextube/config.toml to add channels/playlists
  2. Run: annextube backup
```

**Directory structure created**:
```
my-youtube-archive/
├── .git/               # Git repository
├── .git-annex/         # Git-annex metadata
├── .annextube/         # annextube config
│   └── config.toml     # Configuration file (EDIT THIS!)
├── .gitattributes      # File tracking rules
├── videos/             # Video content (created on first backup)
├── playlists/          # Playlist content
└── channels/           # Channel metadata
```

---

## Step 2.5: Configure Sources

Edit `.annextube/config.toml` to add channels/playlists you want to archive:

```bash
vim .annextube/config.toml  # or nano, or your favorite editor
```

**Add your channels** (example config):

```toml
# YouTube Data API v3 key (REQUIRED)
# Get from: https://console.cloud.google.com/apis/credentials
api_key = "YOUR_API_KEY_HERE"

# Quick test configuration (~10 videos)
[[sources]]
url = "https://www.youtube.com/@RickAstleyYT"
type = "channel"
enabled = true

# HIGH PRIORITY: Liked Videos playlist test case
# [[sources]]
# url = "https://www.youtube.com/playlist?list=LL"  # LL = Liked Videos
# type = "playlist"
# enabled = true

# Add more sources as needed
# [[sources]]
# url = "https://youtube.com/c/datalad"
# type = "channel"
# enabled = true

[components]
videos = false       # Track URLs only (no video downloads)
metadata = true
comments = true
captions = true
thumbnails = true

[filters]
limit = 10  # For quick testing: 10 most recent videos by upload date (newest first)
# date_start = "2024-01-01"  # Uncomment to filter by date
```

**Save the file** and you're ready to backup!

---

## Step 3: Backup Configured Channels

Now run the backup command (it will use sources from your config):

```bash
annextube backup
```

**What this does**:
- Reads `.annextube/config.toml` for sources and settings
- Fetches channel metadata (name, description, subscriber count)
- Lists videos (limited to 10 if you set `filters.limit = 10`)
- Downloads video metadata (title, description, views, likes, etc.)
- Downloads comments for each video
- Downloads captions in all available languages
- Downloads thumbnails
- Tracks video URLs with git-annex (--relaxed mode: URL-only, no video file download)

**Progress output** (with config: limit = 10):
```
Loading config: .annextube/config.toml
Found 1 enabled source

Backing up [1/1]: https://www.youtube.com/@RickAstleyYT
  Channel: Rick Astley (UCuAXFkgsw1L7xaCfnd5JJOw)
  Videos found: 42 (limiting to 10 via config.filters.limit)

  Progress: [████████████████████] 10/10 videos (100%)

  Summary:
    Videos tracked: 10 (URL-only via git-annex --relaxed)
    Comments fetched: 234
    Captions downloaded: 20 (2 languages avg)

Total summary:
  Sources processed: 1
  Videos tracked: 10
  Comments fetched: 234
  Captions downloaded: 20
  Duration: 45s
```

**What you have now**:
- Full metadata for all videos (even if videos get deleted from YouTube later)
- All comments (preserved even if comments are disabled later)
- Captions in all languages
- Thumbnails
- Video URLs tracked (can download videos later if needed)

---

## Step 4: Export Metadata

Generate TSV (tab-separated values) files for efficient browsing:

```bash
annextube export
```

**Output**:
```
Exporting metadata...
  Videos: 10 entries → videos.tsv
  Playlists: 0 entries → playlists.tsv

Export complete.
```

**What this does**:
- Creates `videos.tsv` (summary of all videos) in current directory
- Creates `playlists.tsv` (summary of all playlists)
- Both files can be opened in Excel, Visidata, DuckDB, etc.

**Example: View with Visidata** (if installed):
```bash
visidata videos.tsv
```

---

## Step 5: Browse Your Archive

Generate a web interface to browse videos offline:

```bash
annextube generate-web
```

**Output**:
```
Generating web interface...
  Loading metadata: 10 videos, 0 playlists
  Building index...
  Generating pages...
  Copying assets...

Web interface generated: web/
  Open: file:///home/user/my-youtube-archive/web/index.html
```

**Open in browser**:
```bash
# Linux
xdg-open web/index.html

# macOS
open web/index.html

# Windows (WSL)
explorer.exe $(wslpath -w web/index.html)
```

**Web interface features**:
- Browse all videos with thumbnails
- Search by title, description, tags
- Filter by date range, channel, playlist
- Watch videos (if downloaded) or click through to YouTube
- View comments and captions
- Works entirely offline (no server needed)

---

## Step 6: Set Up Incremental Updates

Run daily updates to catch new videos and comments:

### Manual update
```bash
cd ~/my-youtube-archive
annextube update
```

**What this does**:
- Reads sources from `.annextube/config.toml`
- Checks all configured channels/playlists for new videos
- Fetches new comments on existing videos
- Fetches updated captions
- Only downloads what's new (efficient)

### Automatic updates (cron)

Add to your crontab (`crontab -e`):
```bash
# Update archive daily at 2 AM
0 2 * * * cd ~/my-youtube-archive && /usr/bin/annextube update
```

### Automatic updates (GitHub Actions)

See [CI/CD workflow guide](../how-to/setup-ci-workflow.md) for automated updates via GitHub Actions.

---

## Next Steps

### Download Video Files

By default, annextube only tracks video URLs (metadata-only mode via git-annex --relaxed). To actually download video content, edit your config:

```toml
# In .annextube/config.toml
[components]
videos = true  # Change to true to download video files

[filters]
limit = 5  # Limit for testing (videos are large!)
```

Then run:
```bash
annextube backup
```

**Note**: Video files are large! A channel with 100 videos can easily be 50GB+. Use `limit` for testing.

### Recommended Test Channels

For development and testing, configure these channels in `.annextube/config.toml`:

**Example config with test channels**:

```toml
# Quick testing (~10 videos)
[[sources]]
url = "https://www.youtube.com/@RickAstleyYT"
type = "channel"
enabled = true

# Playlist testing (DataLad has many playlists)
[[sources]]
url = "https://youtube.com/c/datalad"
type = "channel"
enabled = true

# ReproNim
[[sources]]
url = "https://www.youtube.com/@repronim"
type = "channel"
enabled = true

# Andriy Popyk (see /home/yoh/proj/TrueTube/Andriy_Popyk for prototype reference)
[[sources]]
url = "https://www.youtube.com/@apopyk"
type = "channel"
enabled = true

# Center for Open Neuroscience
[[sources]]
url = "https://www.youtube.com/@centeropenneuro"
type = "channel"
enabled = true

[components]
videos = false  # Track URLs only (no downloads)
metadata = true
comments = true
captions = true
thumbnails = true

[filters]
limit = 10  # Limit each source to 10 most recent videos (by upload date) for testing
```

Then backup all:
```bash
annextube backup
```

### Apply Filters

Configure filters in `.annextube/config.toml`:

**Creative Commons only**:
```toml
[filters]
license = "creativeCommon"
```

**Date range** (2024 videos only):
```toml
[filters]
date_start = "2024-01-01"
date_end = "2024-12-31"
```

**Skip components** (metadata + thumbnails only, no comments/captions):
```toml
[components]
videos = false
metadata = true
comments = false  # Skip comments
captions = false  # Skip captions
thumbnails = true
```

Then backup:
```bash
annextube backup
```

**Override config with CLI flags** (for one-time use):
```bash
annextube backup --license creativeCommon --limit 5
```

### Backup Playlists

Add playlist to config:

```toml
[[sources]]
url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
type = "playlist"
enabled = true
```

Then backup:
```bash
annextube backup
```

Or backup ad-hoc without config:
```bash
annextube backup https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf
```

### Configure git-annex Remotes

Store video files on S3, WebDAV, or other remotes:

```bash
# Navigate to archive
cd ~/my-youtube-archive

# Example: S3 remote
git annex initremote s3backup \
  type=S3 \
  bucket=my-youtube-backup \
  encryption=none

# Copy video files to remote
git annex copy --to=s3backup videos/
```

See [git-annex special remotes guide](../how-to/configure-special-remotes.md) for details.

---

## Common Tasks

### Check archive status
```bash
cd ~/my-youtube-archive
git status
git annex info
```

### View logs (if errors occur)
```bash
annextube backup --log-level debug
```

### Force re-fetch metadata (if something changed)
```bash
annextube update --force
```

### Export config for reference
```bash
cat .annextube/config.toml
```

---

## Troubleshooting

### "git-annex not found"

Install git-annex:
```bash
# Debian/Ubuntu
sudo apt install git-annex

# macOS (Homebrew)
brew install git-annex

# Conda/Mamba
conda install -c conda-forge git-annex
```

### "YouTube API quota exceeded"

yt-dlp uses web scraping (no API key needed), but YouTube may rate-limit. Solutions:
- Wait a few hours and retry
- Use `--sleep-interval 5` to slow down requests (not implemented in v1)
- Archive smaller chunks (per playlist instead of entire channel)

### "Network timeout"

Check your internet connection. If YouTube is unreachable, wait and retry. The system will resume from where it left off.

### "Disk full"

Video files are large. Either:
- Use `--no-download-videos` (metadata only)
- Configure git-annex special remote to store videos elsewhere
- Free up disk space

---

## Summary

You've learned how to:
- ✅ Install annextube
- ✅ Create a YouTube archive repository
- ✅ Backup a channel (metadata, comments, captions)
- ✅ Export metadata to TSV files
- ✅ Browse your archive offline with the web interface
- ✅ Set up incremental updates

**What you have now**:
- Complete archive of a YouTube channel
- Metadata preserved even if videos are deleted
- Comments preserved even if disabled
- Offline-browsable web interface
- Efficient incremental update capability

**Recommended next steps**:
1. Set up automated daily updates (cron or GitHub Actions)
2. Configure git-annex special remote for video storage
3. Explore filtering options for targeted archival
4. Read the full documentation for advanced features

---

## Resources

- **Full Documentation**: [https://annextube.readthedocs.io/](https://annextube.readthedocs.io/) (placeholder)
- **GitHub Repository**: [https://github.com/yourusername/annextube](https://github.com/yourusername/annextube) (placeholder)
- **CLI Reference**: [contracts/cli-contract.md](./contracts/cli-contract.md)
- **Data Model**: [data-model.md](./data-model.md)
- **Issue Tracker**: [https://github.com/yourusername/annextube/issues](https://github.com/yourusername/annextube/issues) (placeholder)

---

**Estimated time to complete this guide**: 15 minutes (Success Criterion SC-015 ✅)
