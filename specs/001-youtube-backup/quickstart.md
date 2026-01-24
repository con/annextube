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

Initialize a new YouTube archive repository:

```bash
annextube create-dataset ~/my-youtube-archive
```

**What this does**:
- Creates a new directory at `~/my-youtube-archive`
- Initializes git repository
- Initializes git-annex with URL backend (for video URLs)
- Configures file tracking (.gitattributes):
  - Metadata files (*.json, *.tsv, *.md, *.vtt) → git
  - Media files (*.mp4, *.webm, *.jpg, *.png) → git-annex

**Output**:
```
Initialized YouTube archive repository at: /home/user/my-youtube-archive
Git-annex backend: URL (for video URLs)
Tracking configuration:
  - *.json, *.tsv, *.md, *.vtt → git
  - *.mp4, *.webm, *.jpg, *.png → git-annex
```

---

## Step 3: Backup Your First Channel

Let's backup a YouTube channel (metadata only, no video downloads):

```bash
annextube backup \
  --output-dir ~/my-youtube-archive \
  https://www.youtube.com/@RickAstleyYT
```

**What this does**:
- Fetches channel metadata (name, description, subscriber count)
- Lists all public videos in the channel
- Downloads video metadata (title, description, views, likes, etc.)
- Downloads comments for each video
- Downloads captions in all available languages
- Downloads thumbnails
- Tracks video URLs (but doesn't download video files)

**Progress output**:
```
Backing up channel: Rick Astley (UCuAXFkgsw1L7xaCfnd5JJOw)
  Videos found: 42
  Playlists found: 5

Progress: [████████████████████] 42/42 videos (100%)

Summary:
  Videos tracked: 42
  Videos downloaded: 0 (metadata only)
  Comments fetched: 1,234
  Captions downloaded: 84 (2 languages avg)
  Duration: 2m 34s

Repository updated: /home/user/my-youtube-archive
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
annextube export --output-dir ~/my-youtube-archive
```

**Output**:
```
Exporting metadata...
  Videos: 42 entries → videos.tsv
  Playlists: 5 entries → playlists.tsv

Export complete.
```

**What this does**:
- Creates `videos.tsv` (summary of all videos)
- Creates `playlists.tsv` (summary of all playlists)
- Both files can be opened in Excel, Visidata, DuckDB, etc.

**Example: View with Visidata** (if installed):
```bash
cd ~/my-youtube-archive
visidata videos.tsv
```

---

## Step 5: Browse Your Archive

Generate a web interface to browse videos offline:

```bash
annextube generate-web --output-dir ~/my-youtube-archive
```

**Output**:
```
Generating web interface...
  Loading metadata: 42 videos, 5 playlists
  Building index...
  Generating pages...
  Copying assets...

Web interface generated: /home/user/my-youtube-archive/web/
  Open: file:///home/user/my-youtube-archive/web/index.html
```

**Open in browser**:
```bash
# Linux
xdg-open ~/my-youtube-archive/web/index.html

# macOS
open ~/my-youtube-archive/web/index.html

# Windows (WSL)
explorer.exe $(wslpath -w ~/my-youtube-archive/web/index.html)
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
annextube update --output-dir ~/my-youtube-archive
```

**What this does**:
- Checks all tracked channels/playlists for new videos
- Fetches new comments on existing videos
- Fetches updated captions
- Only downloads what's new (efficient)

### Automatic updates (cron)

Add to your crontab (`crontab -e`):
```bash
# Update archive daily at 2 AM
0 2 * * * /usr/bin/annextube update --output-dir ~/my-youtube-archive
```

### Automatic updates (GitHub Actions)

See [CI/CD workflow guide](../how-to/setup-ci-workflow.md) for automated updates via GitHub Actions.

---

## Next Steps

### Download Video Files

By default, annextube only tracks video URLs (metadata-only mode). To download videos:

```bash
annextube backup \
  --output-dir ~/my-youtube-archive \
  --download-videos \
  https://www.youtube.com/@RickAstleyYT
```

**Note**: Video files are large! A channel with 100 videos can easily be 50GB+.

### Apply Filters

Backup only videos matching specific criteria:

**Creative Commons only**:
```bash
annextube backup \
  --output-dir ~/my-youtube-archive \
  --license creativeCommon \
  https://www.youtube.com/@SomeChannel
```

**Date range** (2024 videos only):
```bash
annextube backup \
  --output-dir ~/my-youtube-archive \
  --date-start 2024-01-01 \
  --date-end 2024-12-31 \
  https://www.youtube.com/@SomeChannel
```

**Skip components** (metadata + thumbnails only, no comments/captions):
```bash
annextube backup \
  --output-dir ~/my-youtube-archive \
  --no-comments \
  --no-captions \
  https://www.youtube.com/@SomeChannel
```

### Backup Playlists

Backup a specific playlist:

```bash
annextube backup \
  --output-dir ~/my-youtube-archive \
  https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf
```

### Configure git-annex Remotes

Store video files on S3, WebDAV, or other remotes:

```bash
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
annextube backup --log-level debug --output-dir ~/my-youtube-archive <URL>
```

### Force re-fetch metadata (if something changed)
```bash
annextube update --force --output-dir ~/my-youtube-archive
```

### Export for analysis (JSON format)
```bash
annextube export --json --output-dir ~/my-youtube-archive > export.json
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
