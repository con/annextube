# Test Channel Setup Plan

**Purpose**: Create a controlled YouTube test channel with videos under different licenses, playlists, and metadata for reliable annextube testing.

**Status**: Planning
**Created**: 2026-02-04

## Goals

1. **Eliminate dependency on external channels** - No risk of videos being deleted or privacy settings changed
2. **Test all license types** - Both standard YouTube and Creative Commons videos
3. **Fast testing** - Very short videos (1-5 seconds) for quick downloads
4. **Comprehensive metadata** - Videos with various metadata combinations for thorough testing
5. **Playlist coverage** - Multiple playlists including edge cases

## Test Channel Structure

### Channel Name
`annextube-test-channel` or `AnnexTube Testing`

### Video Collection (12 videos minimum)

#### License Coverage (6 videos)
1. **Standard License Videos** (3 videos)
   - `test-video-standard-01.mp4` - "Standard License Test 1" (1 sec, solid red)
   - `test-video-standard-02.mp4` - "Standard License Test 2" (2 sec, solid green)
   - `test-video-standard-03.mp4` - "Standard License Test 3" (3 sec, solid blue)

2. **Creative Commons Videos** (3 videos)
   - `test-video-cc-01.mp4` - "CC License Test 1" (1 sec, solid yellow)
   - `test-video-cc-02.mp4` - "CC License Test 2" (2 sec, solid magenta)
   - `test-video-cc-03.mp4` - "CC License Test 3" (3 sec, solid cyan)

#### Metadata Variety (6 additional videos)
3. **With Captions** (2 videos)
   - `test-video-captions-en.mp4` - English captions
   - `test-video-captions-multi.mp4` - Multiple language captions (en, es, de)

4. **With Location Metadata** (2 videos)
   - `test-video-location-nyc.mp4` - Recorded in NYC (40.7128° N, 74.0060° W)
   - `test-video-location-london.mp4` - Recorded in London (51.5074° N, 0.1278° W)

5. **With Comments** (2 videos)
   - `test-video-with-comments-01.mp4` - 5+ comments with replies
   - `test-video-with-comments-02.mp4` - 10+ comments with threading

#### Special Cases (optional, for advanced testing)
6. **Edge Cases**
   - `test-video-no-description.mp4` - Empty description
   - `test-video-long-description.mp4` - Very long description (>5000 chars)
   - `test-video-many-tags.mp4` - Maximum tags (500 chars)
   - `test-video-hd.mp4` - HD quality (1920x1080, 1 sec)
   - `test-video-4k.mp4` - 4K quality (3840x2160, 1 sec) if supported

### Playlist Collection (5 playlists)

1. **"All Standard License"** - Contains all 3 standard license videos
2. **"All Creative Commons"** - Contains all 3 CC videos
3. **"Mixed Licenses"** - Contains both standard and CC videos
4. **"Videos with Captions"** - All videos that have captions
5. **"Videos with Location"** - All videos with GPS metadata

### Privacy Settings
- **Public**: 10 videos (for general testing)
- **Unlisted**: 2 videos (for privacy testing)
- **Private**: 0 videos (can't be archived by annextube)

## Implementation Steps

### Phase 1: Preparation (Manual)

**1. Create YouTube Channel**
- Create new Google account: `annextube.test@gmail.com` (or similar)
- Create YouTube channel: "AnnexTube Testing"
- Enable channel for uploads
- Note channel ID

**2. Generate Test Videos**
- Use ffmpeg to create very short videos (see script below)
- Create solid color videos (smallest file size)
- Generate caption files (VTT format)
- Total storage needed: ~5-10 MB for all videos

**3. Get API Credentials**
- Enable YouTube Data API v3 in Google Cloud Console
- Create OAuth 2.0 credentials for desktop app
- Download `client_secrets.json`

### Phase 2: Automated Upload (Script)

**Script: `setup_test_channel.py`**

Functions:
1. `generate_test_videos()` - Create MP4 files with ffmpeg
2. `generate_caption_files()` - Create VTT caption files
3. `upload_video()` - Upload video with metadata
4. `set_video_license()` - Set license to standard or CC
5. `create_playlist()` - Create playlist
6. `add_to_playlist()` - Add videos to playlists
7. `add_location_metadata()` - Set recording location
8. `post_test_comments()` - Add comments to videos

### Phase 3: Verification

**Checklist:**
- [ ] All videos uploaded successfully
- [ ] 3 standard license + 3 CC license videos confirmed
- [ ] All playlists created and populated
- [ ] Captions uploaded and visible
- [ ] Location metadata set
- [ ] Comments posted
- [ ] Channel public and accessible

### Phase 4: Integration with annextube Tests

**Update test files:**
```python
# tests/conftest.py
TEST_CHANNEL_URL = "https://www.youtube.com/@annextube-test-channel"
TEST_CHANNEL_ID = "UC..."  # Actual channel ID

# Test data
TEST_VIDEOS = {
    "standard_license": ["video_id_1", "video_id_2", "video_id_3"],
    "cc_license": ["video_id_4", "video_id_5", "video_id_6"],
    "with_captions": ["video_id_7", "video_id_8"],
    "with_location": ["video_id_9", "video_id_10"],
}

TEST_PLAYLISTS = {
    "all_standard": "playlist_id_1",
    "all_cc": "playlist_id_2",
    "mixed": "playlist_id_3",
}
```

**Update integration tests:**
```python
# tests/integration/test_comprehensive_backup.py
def test_comprehensive_backup_with_all_features(tmp_git_annex_repo: Path) -> None:
    """Test backup with playlists, captions, comments, and thumbnails enabled."""
    config = Config(
        components=ComponentsConfig(
            videos=False,
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

    # Use controlled test channel instead of Khan Academy
    result = archiver.backup_channel(TEST_CHANNEL_URL)

    # Now we can reliably assert exact counts
    assert result["videos_processed"] == 12
    # ... rest of assertions
```

## Video Generation Commands

### Using ffmpeg to create test videos

```bash
# Solid color videos (very small file size)
# Red (1 second)
ffmpeg -f lavfi -i color=c=red:s=1280x720:d=1 -c:v libx264 -preset ultrafast -crf 28 test-video-standard-01.mp4

# Green (2 seconds)
ffmpeg -f lavfi -i color=c=green:s=1280x720:d=2 -c:v libx264 -preset ultrafast -crf 28 test-video-standard-02.mp4

# Blue (3 seconds)
ffmpeg -f lavfi -i color=c=blue:s=1280x720:d=3 -c:v libx264 -preset ultrafast -crf 28 test-video-standard-03.mp4

# Yellow (CC license, 1 second)
ffmpeg -f lavfi -i color=c=yellow:s=1280x720:d=1 -c:v libx264 -preset ultrafast -crf 28 test-video-cc-01.mp4

# Magenta (CC license, 2 seconds)
ffmpeg -f lavfi -i color=c=magenta:s=1280x720:d=2 -c:v libx264 -preset ultrafast -crf 28 test-video-cc-02.mp4

# Cyan (CC license, 3 seconds)
ffmpeg -f lavfi -i color=c=cyan:s=1280x720:d=3 -c:v libx264 -preset ultrafast -crf 28 test-video-cc-03.mp4

# With text overlay (for caption testing)
ffmpeg -f lavfi -i color=c=white:s=1280x720:d=5 \
  -vf "drawtext=text='Test Video with Captions':fontsize=48:fontcolor=black:x=(w-text_w)/2:y=(h-text_h)/2" \
  -c:v libx264 -preset ultrafast -crf 28 test-video-captions-en.mp4

# HD version (1 second, 1920x1080)
ffmpeg -f lavfi -i color=c=orange:s=1920x1080:d=1 -c:v libx264 -preset ultrafast -crf 28 test-video-hd.mp4
```

### Caption File Example (VTT format)

```vtt
WEBVTT

00:00:00.000 --> 00:00:02.000
This is a test video

00:00:02.000 --> 00:00:05.000
With English captions for testing
```

## Quota Usage Estimate

**Upload operations:**
- Upload video: 1600 units per video × 12 videos = **19,200 units**
- Set video metadata: 50 units per video × 12 videos = **600 units**
- Create playlist: 50 units × 5 playlists = **250 units**
- Add to playlist: 50 units × 20 additions = **1,000 units**
- **Total: ~21,000 units** (2.1 days of free tier or $21 USD)

**One-time cost**: This is a one-time setup, so the quota cost is acceptable.

## Maintenance

**Annual refresh:**
- Re-upload videos if any get deleted
- Refresh comments if they get removed
- Update captions if needed
- Verify all playlists still exist

**Backup the test channel:**
- Keep local copies of all generated videos
- Keep OAuth credentials secure
- Document video IDs and playlist IDs
- Store in git repo (videos excluded, IDs included)

## Security Considerations

1. **API Key Security**
   - Store OAuth credentials in `.gitignore`
   - Use environment variables for sensitive data
   - Limit API scope to minimum required

2. **Channel Security**
   - Use strong password for Google account
   - Enable 2FA on test account
   - Don't use for any other purpose

3. **Content Moderation**
   - Keep all videos appropriate (solid colors, test text only)
   - Monitor for spam comments
   - Make channel clearly identified as "test/development"

## Alternative: Use Existing Free Test Videos

**Option**: Instead of creating our own channel, use existing CC-licensed test videos:

Pros:
- No quota cost
- No maintenance
- Videos already exist

Cons:
- Can't control metadata
- Can't guarantee availability
- Can't test all edge cases
- Can't add custom comments

**Recommendation**: Create our own test channel for maximum control and reliability.

## Next Steps

1. [ ] Create Google account for test channel
2. [ ] Enable YouTube Data API v3
3. [ ] Generate OAuth credentials
4. [ ] Run video generation script (ffmpeg)
5. [ ] Run upload script (`setup_test_channel.py`)
6. [ ] Verify all uploads successful
7. [ ] Update annextube tests to use test channel
8. [ ] Document video IDs and playlist IDs in `tests/conftest.py`
9. [ ] Run full test suite to verify
10. [ ] Commit test channel metadata to git

## Resources

- YouTube Data API v3 Upload: https://developers.google.com/youtube/v3/guides/uploading_a_video
- OAuth 2.0 Setup: https://developers.google.com/youtube/v3/guides/auth/installed-apps
- Quota Costs: https://developers.google.com/youtube/v3/determine_quota_cost
- ffmpeg Documentation: https://ffmpeg.org/documentation.html
