# AnnexTube Tools

Development and testing utilities for annextube.

## YouTube API Credentials

**Two types of credentials are used:**

1. **API Key** (in `.git/secrets`)
   - **Purpose**: Read-only access to fetch video metadata
   - **Used by**: `test_api_metadata.py`, integration tests
   - **Setup**: Already configured in `.git/secrets` as `YOUTUBE_API_KEY`
   - **Access**: `source ../.git/secrets` to load into environment

2. **OAuth 2.0** (for `setup_test_channel.py`)
   - **Purpose**: Write access to upload videos, create playlists, post comments
   - **Used by**: `setup_test_channel.py` only
   - **Setup**: Requires Google Cloud project (see below)
   - **Access**: Browser-based authentication flow

## test_api_metadata.py

**Purpose**: Test YouTube API metadata enhancement with real videos using the existing API key.

**Usage**:
```bash
# Load API key from .git/secrets
source ../.git/secrets

# Test with known videos (default)
python test_api_metadata.py

# Test with specific video IDs
python test_api_metadata.py --video-ids "YE7VzlLtp-4,dQw4w9WgXcQ"

# Save results to file
python test_api_metadata.py --video-ids "..." --output results.json
```

This script tests the same metadata enhancement that integration tests use, but with real YouTube videos to verify license detection, recording location, and other enhanced fields.

## setup_test_channel.py

**Purpose**: Create a controlled YouTube test channel with videos under different licenses, playlists, and metadata for reliable testing.

**Why**: External channels (like Khan Academy) can have videos deleted or privacy settings changed, causing test failures. A dedicated test channel gives us full control.

### Features

- **12 test videos** (1-5 seconds each, ~2-5 KB per video)
- **License variety**: 3 standard YouTube license + 3 Creative Commons videos
- **Metadata coverage**: Videos with captions, GPS locations, comments
- **5 playlists**: Standard license, CC license, mixed, with captions, with location
- **Fast downloads**: Very short videos minimize test execution time

### Setup

**1. Prerequisites**

```bash
# Install required packages
pip install google-api-python-client google-auth-oauthlib

# Install ffmpeg (for video generation)
# Ubuntu/Debian:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg
```

**2. Google Cloud Setup**

**Note**: You already have an API key in `.git/secrets` for **read-only** access (metadata fetching). However, uploading videos requires **OAuth 2.0** credentials with write permissions.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "annextube-test-channel"
3. Enable **YouTube Data API v3**
4. Create **OAuth 2.0 Client ID** (Application type: Desktop app)
5. Download credentials as `client_secrets.json`
6. Place `client_secrets.json` in `tools/` directory

**3. Create YouTube Channel**

1. Create new Google account (or use existing test account)
2. Create YouTube channel: "AnnexTube Testing" or similar
3. Make channel public

### Usage

**Generate test videos locally:**

```bash
cd tools/
python setup_test_channel.py --generate-videos
```

This creates 12 test videos in `test_videos/` directory (~30 KB total).

**Upload everything to YouTube:**

```bash
python setup_test_channel.py --upload-all
```

This will:
1. Authenticate with YouTube (browser window opens)
2. Upload all 12 videos
3. Set licenses (standard vs CC)
4. Upload captions
5. Create 5 playlists
6. Add videos to playlists
7. Save video IDs and playlist IDs to `test_videos/test_channel_metadata.json`

**Just create playlists** (videos already uploaded):

```bash
python setup_test_channel.py --create-playlists
```

**Add test comments:**

```bash
python setup_test_channel.py --add-comments
```

### Quota Cost

**One-time setup:**
- Upload 12 videos: 12 × 1,600 = 19,200 units
- Update metadata: 12 × 50 = 600 units
- Create 5 playlists: 5 × 50 = 250 units
- Add videos to playlists: ~20 × 50 = 1,000 units
- **Total: ~21,000 units** (~$21 USD or ~2 days of free tier)

This is a **one-time cost**. Once the channel is set up, tests can use it indefinitely.

### Integration with Tests

After running `--upload-all`, the script outputs video IDs and playlist IDs.

**Add to `tests/conftest.py`:**

```python
# Test channel metadata (created by tools/setup_test_channel.py)
TEST_CHANNEL_URL = "https://www.youtube.com/@annextube-test-channel"

TEST_CHANNEL_VIDEOS = {
    "test-video-standard-01.mp4": "VIDEO_ID_1",
    "test-video-standard-02.mp4": "VIDEO_ID_2",
    "test-video-standard-03.mp4": "VIDEO_ID_3",
    "test-video-cc-01.mp4": "VIDEO_ID_4",
    "test-video-cc-02.mp4": "VIDEO_ID_5",
    "test-video-cc-03.mp4": "VIDEO_ID_6",
    # ... etc
}

TEST_CHANNEL_PLAYLISTS = {
    "All Standard License Videos": "PLAYLIST_ID_1",
    "All Creative Commons Videos": "PLAYLIST_ID_2",
    # ... etc
}
```

**Update integration tests:**

```python
# tests/integration/test_comprehensive_backup.py

def test_comprehensive_backup_with_all_features(tmp_git_annex_repo: Path) -> None:
    """Test backup with playlists, captions, comments, and thumbnails enabled."""
    config = Config(
        components=ComponentsConfig(
            videos=False,  # Still skip video downloads
            metadata=True,
            captions=True,
            thumbnails=True,
            comments_depth=10000,
        ),
        filters=FiltersConfig(
            limit=12,  # Get all test videos
        ),
    )

    archiver = Archiver(tmp_git_annex_repo, config)

    # Use controlled test channel instead of external channel
    result = archiver.backup_channel(TEST_CHANNEL_URL)

    # Now we can reliably assert exact counts
    assert result["videos_processed"] == 12
    # ... rest of assertions
```

### Maintenance

**Annual refresh** (if needed):
```bash
# Re-upload any deleted videos
python setup_test_channel.py --upload-all

# Refresh comments
python setup_test_channel.py --add-comments
```

**Backup test channel:**
Keep the generated videos in git:
```bash
# Add test_videos/ to git (videos are tiny)
git add tools/test_videos/*.mp4
git add tools/test_videos/*.vtt
git add tools/test_videos/test_channel_metadata.json
```

### Security

**IMPORTANT**: Do not commit sensitive files:
- `client_secrets.json` - OAuth credentials (add to .gitignore)
- `token.json` - Access token (add to .gitignore)

**Recommended `.gitignore` entries:**
```gitignore
# YouTube API credentials
tools/client_secrets.json
tools/token.json

# But DO commit test video files (they're tiny and useful)
# !tools/test_videos/*.mp4
# !tools/test_videos/*.vtt
```

### Troubleshooting

**"ffmpeg not found"**
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg      # macOS
```

**"client_secrets.json not found"**
- Download OAuth 2.0 credentials from Google Cloud Console
- Save as `tools/client_secrets.json`

**"Quota exceeded"**
- Wait 24 hours for quota to reset (resets at midnight Pacific Time)
- Or request quota increase from Google Cloud Console
- Or purchase additional quota ($0.10 per 100 units)

**Upload fails with 403 error**
- Check OAuth scopes are correct
- Re-authenticate: delete `token.json` and run script again
- Verify YouTube Data API v3 is enabled in Google Cloud Console

### Example Output

```
=== Generating Test Videos ===

  Generating test-video-standard-01.mp4 (1s, red)...
  ✓ Generated test_videos/test-video-standard-01.mp4 (3 KB)
  Generating test-video-standard-02.mp4 (2s, green)...
  ✓ Generated test_videos/test-video-standard-02.mp4 (4 KB)
  ...

✓ Generated 12 test videos

=== Uploading Videos to YouTube ===

✓ Authenticated with YouTube API
  Uploading test-video-standard-01.mp4...
  ✓ Uploaded: dQw4w9WgXcQ (License: youtube)
  Uploading test-video-cc-01.mp4...
  ✓ Uploaded: aBc123XyZ (License: creativeCommon)
  ...

✓ Uploaded 12 videos

=== Creating Playlists ===

  Creating playlist: All Standard License Videos...
  ✓ Created playlist: PLxxxxxx
    Added Test Video - Standard License 1
    Added Test Video - Standard License 2
    Added Test Video - Standard License 3
  ...

✓ Created 5 playlists

✓ Metadata saved to test_videos/test_channel_metadata.json

Add this to tests/conftest.py:
```python
TEST_CHANNEL_VIDEOS = {
    "test-video-standard-01.mp4": "dQw4w9WgXcQ",
    "test-video-standard-02.mp4": "aBc123XyZ",
    ...
}
...
```

✓ Test channel setup complete!
```

## Other Tools (Future)

- `migrate_metadata.py` - Migrate old metadata format to new schema
- `validate_archive.py` - Verify archive integrity
- `benchmark_performance.py` - Performance benchmarking
