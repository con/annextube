# Data Model: YouTube Archive System

**Feature**: 001-youtube-backup
**Date**: 2026-01-24
**Purpose**: Define data structures for YouTube archive entities

## Overview

This data model defines the core entities for the YouTube archive system. All data is stored in **file-based formats** (JSON, TSV) with **no database dependencies** (Constitution Principle XI: Storage Simplicity).

**Storage Strategy**:
- **Per-video metadata**: Individual JSON files (one per video)
- **Summary metadata**: Aggregated TSV files (videos.tsv, playlists.tsv) for efficient querying
- **Captions**: VTT files (one per language)
- **Comments**: JSON files (one per video, includes threading)
- **Sync state**: JSON file tracking last sync per source

## Entities

### 1. Channel

Represents a YouTube channel being archived.

**Attributes**:
```typescript
interface Channel {
  channel_id: string;           // YouTube channel ID (unique identifier)
  name: string;                 // Channel name
  description: string;          // Channel description
  custom_url?: string;          // Custom channel URL (e.g., @username)
  subscriber_count: number;     // Subscriber count at last fetch
  video_count: number;          // Total public videos
  avatar_url: string;           // Channel avatar/thumbnail URL
  banner_url?: string;          // Channel banner URL
  country?: string;             // Channel country
  videos: string[];             // List of video IDs in this channel
  playlists: string[];          // List of playlist IDs in this channel
  last_sync: string;            // ISO 8601 timestamp of last sync
  created_at: string;           // Channel creation date (ISO 8601)
  fetched_at: string;           // When this metadata was fetched (ISO 8601)
}
```

**File location**: `channels/{channel_id}/metadata.json`

**Validation**:
- `channel_id`: Required, matches regex `^[A-Za-z0-9_-]+$`
- `name`: Required, non-empty string
- `subscriber_count`, `video_count`: Non-negative integers
- `last_sync`, `created_at`, `fetched_at`: Valid ISO 8601 timestamps

---

### 2. Video

Represents a YouTube video with all associated metadata.

**Attributes**:
```typescript
interface Video {
  video_id: string;              // YouTube video ID (unique identifier)
  title: string;                 // Video title
  description: string;           // Video description
  channel_id: string;            // Parent channel ID
  channel_name: string;          // Channel name (denormalized for convenience)
  published_at: string;          // Publication date (ISO 8601)
  duration: number;              // Duration in seconds
  view_count: number;            // View count at fetch time
  like_count: number;            // Like count at fetch time
  comment_count: number;         // Comment count at fetch time
  thumbnail_url: string;         // Highest resolution thumbnail URL
  license: 'standard' | 'creativeCommon'; // YouTube license type
  privacy_status: 'public' | 'unlisted' | 'private'; // Privacy status
  availability: 'public' | 'private' | 'deleted' | 'unavailable'; // Current availability
  tags: string[];                // Video tags
  categories: string[];          // Video categories
  language?: string;             // Primary language (ISO 639-1)
  captions_available: string[];  // List of caption language codes
  has_auto_captions: boolean;    // Whether auto-generated captions exist
  file_path?: string;            // Path to video file (if downloaded)
  file_size?: number;            // File size in bytes (if downloaded)
  download_status: 'not_downloaded' | 'tracked' | 'downloaded' | 'failed'; // Download status
  source_url: string;            // Original YouTube URL
  fetched_at: string;            // When metadata was fetched (ISO 8601)
  updated_at: string;            // When metadata was last updated (ISO 8601)
}
```

**File locations**:
- Individual metadata: `videos/{path_pattern}/metadata.json` where `{path_pattern}` is configurable (default: `{date}_{video_id}_{sanitized_title}`, e.g., `2026-01-23_FE-hM1kRK4Y_why_laplace_transforms_are_so_useful`)
- Summary TSV: `videos.tsv` (root level)

**Configurable Path Patterns**:
- `{date}`: Publication date in ISO format (YYYY-MM-DD)
- `{video_id}`: YouTube video ID (persistent, unique)
- `{sanitized_title}`: Video title with special characters removed/replaced for filesystem safety
- `{channel_id}`: Channel ID
- `{channel_name}`: Sanitized channel name
- Example pattern: `{date}_{video_id}_{sanitized_title}` → `2026-01-23_FE-hM1kRK4Y_why_laplace_transforms_are_so_useful`

**Validation**:
- `video_id`: Required, matches regex `^[A-Za-z0-9_-]{11}$` (YouTube video ID format)
- `title`: Required, non-empty string
- `channel_id`: Required, valid channel ID
- `published_at`, `fetched_at`, `updated_at`: Valid ISO 8601 timestamps
- `duration`: Non-negative integer (seconds)
- `view_count`, `like_count`, `comment_count`: Non-negative integers
- `captions_available`: Array of ISO 639-1 language codes
- `license`: One of 'standard' or 'creativeCommon'

**State transitions** (download_status):
```
not_downloaded → tracked → downloaded
                       ↓
                    failed → tracked (retry)
```

---

### 3. Playlist

Represents a YouTube playlist with ordered video list.

**Attributes**:
```typescript
interface Playlist {
  playlist_id: string;           // YouTube playlist ID (unique identifier)
  title: string;                 // Playlist title
  description: string;           // Playlist description
  channel_id: string;            // Parent channel ID
  channel_name: string;          // Channel name (denormalized)
  video_ids: string[];           // Ordered list of video IDs
  video_count: number;           // Number of videos in playlist
  total_duration: number;        // Total duration in seconds
  privacy_status: 'public' | 'unlisted' | 'private'; // Privacy status
  created_at: string;            // Playlist creation date (ISO 8601)
  updated_at: string;            // Last modified date (ISO 8601)
  last_sync: string;             // Last sync timestamp (ISO 8601)
  fetched_at: string;            // When metadata was fetched (ISO 8601)
}
```

**File locations**:
- Individual metadata: `playlists/{playlist_id}/metadata.json`
- Summary TSV: `playlists.tsv` (root level)

**Validation**:
- `playlist_id`: Required, matches regex `^[A-Za-z0-9_-]+$`
- `title`: Required, non-empty string
- `video_ids`: Array of valid video IDs (order preserved)
- `video_count`: Non-negative integer, must match length of `video_ids`
- `total_duration`: Non-negative integer (sum of video durations)
- `created_at`, `updated_at`, `last_sync`, `fetched_at`: Valid ISO 8601 timestamps

**Relationships**:
- Videos in playlist may be organized via symlinks: `playlists/{playlist_id}/{video_id}` → `../../videos/{video_id}/`

---

### 4. Caption

Represents closed captions/subtitles for a video.

**Attributes**:
```typescript
interface Caption {
  video_id: string;              // Parent video ID
  language_code: string;         // ISO 639-1 language code (e.g., 'en', 'es')
  language_name: string;         // Human-readable language name (e.g., 'English')
  auto_generated: boolean;       // Whether captions are auto-generated
  format: 'vtt' | 'srt';         // Caption file format
  file_path: string;             // Path to caption file
  fetched_at: string;            // When captions were fetched (ISO 8601)
  updated_at: string;            // When captions were last updated (ISO 8601)
}
```

**File locations**:
- Caption files: `videos/{video_id}/captions/{language_code}.vtt`
- Caption metadata: Included in video metadata.json under `captions` array

**Validation**:
- `video_id`: Required, valid video ID
- `language_code`: Required, ISO 639-1 code (2-letter)
- `format`: One of 'vtt' or 'srt'
- `fetched_at`, `updated_at`: Valid ISO 8601 timestamps

---

### 5. Comment

Represents a comment on a video, including reply threads.

**Attributes**:
```typescript
interface Comment {
  comment_id: string;            // YouTube comment ID (unique identifier)
  video_id: string;              // Parent video ID
  author: string;                // Comment author name
  author_channel_id: string;     // Author's channel ID
  author_thumbnail?: string;     // Author profile picture URL
  text: string;                  // Comment text content
  timestamp: string;             // Comment creation time (ISO 8601)
  like_count: number;            // Like count for this comment
  parent_id?: string;            // Parent comment ID (for replies)
  reply_count: number;           // Number of replies to this comment
  replies?: Comment[];           // Nested reply comments (if fetched)
  fetched_at: string;            // When comment was fetched (ISO 8601)
}
```

**File locations**:
- Comments file: `videos/{video_id}/comments.json` (array of Comment objects)

**Validation**:
- `comment_id`: Required, unique within video
- `video_id`: Required, valid video ID
- `author`: Required, non-empty string
- `text`: Required, non-empty string
- `timestamp`, `fetched_at`: Valid ISO 8601 timestamps
- `like_count`, `reply_count`: Non-negative integers
- `parent_id`: If present, must reference existing comment ID

**Structure**:
- Top-level comments: `parent_id` is null/undefined
- Replies: `parent_id` references top-level comment, nested under `replies` array

**Example threading**:
```json
[
  {
    "comment_id": "comment1",
    "text": "Great video!",
    "reply_count": 2,
    "replies": [
      {
        "comment_id": "comment2",
        "parent_id": "comment1",
        "text": "I agree!"
      },
      {
        "comment_id": "comment3",
        "parent_id": "comment1",
        "text": "Thanks for sharing"
      }
    ]
  }
]
```

---

### 6. SyncState

Tracks synchronization state for incremental updates.

**Attributes**:
```typescript
interface SyncState {
  source_url: string;            // Channel or playlist URL (unique identifier)
  source_type: 'channel' | 'playlist'; // Type of source
  source_id: string;             // Channel ID or playlist ID
  last_sync: string;             // Last successful sync timestamp (ISO 8601)
  last_video_id?: string;        // Last processed video ID (for pagination)
  last_video_published?: string; // Publication date of last video (ISO 8601)
  error_count: number;           // Consecutive error count
  last_error?: string;           // Last error message (if any)
  next_retry?: string;           // Next retry timestamp (ISO 8601, if in error state)
  status: 'active' | 'error' | 'paused'; // Sync status
  videos_tracked: number;        // Total videos tracked from this source
  videos_downloaded: number;     // Total videos downloaded from this source
}
```

**File location**: `.sync/state.json` (array of SyncState objects)

**Validation**:
- `source_url`: Required, valid YouTube URL
- `source_id`: Required, matches channel or playlist ID format
- `last_sync`: Valid ISO 8601 timestamp
- `error_count`: Non-negative integer
- `videos_tracked`, `videos_downloaded`: Non-negative integers

**State transitions**:
```
active → error (on failure, increment error_count)
error → active (on successful retry, reset error_count)
active → paused (user action)
paused → active (user action)
```

---

### 7. FilterConfig

Defines filtering rules for archival scope.

**Attributes**:
```typescript
interface FilterConfig {
  name: string;                  // Filter configuration name
  date_range?: {
    start?: string;              // Start date (ISO 8601)
    end?: string;                // End date (ISO 8601)
  };
  license_types?: ('standard' | 'creativeCommon')[]; // Allowed licenses
  playlists?: {
    include?: string[];          // Playlist IDs to include
    exclude?: string[];          // Playlist IDs to exclude
  };
  metadata_filters?: {
    min_duration?: number;       // Minimum duration in seconds
    max_duration?: number;       // Maximum duration in seconds
    min_views?: number;          // Minimum view count
    tags?: string[];             // Required tags (OR logic)
  };
  components: {                  // What to backup
    videos: boolean;             // Download video files
    metadata: boolean;           // Fetch metadata
    comments: boolean;           // Fetch comments
    captions: boolean;           // Fetch captions
    thumbnails: boolean;         // Download thumbnails
  };
}
```

**File location**: `.config/filters.json` (array of FilterConfig objects)

**Validation**:
- `name`: Required, unique identifier for filter
- `date_range.start`, `date_range.end`: Valid ISO 8601 timestamps (start < end)
- `metadata_filters.min_duration` < `metadata_filters.max_duration` (if both present)
- At least one component must be true (metadata is recommended minimum)

---

## Summary TSV Schema

### videos.tsv

Tab-separated file with summary metadata for all videos (FR-033).

**Columns**:
```
video_id	title	channel_id	channel_name	published_at	duration	view_count	like_count	comment_count	has_captions	license	file_path	download_status	fetched_at
```

**Example**:
```
dQw4w9WgXcQ	Never Gonna Give You Up	UCuAXFkgsw1L7xaCfnd5JJOw	Rick Astley	1987-11-12T00:00:00Z	213	1234567890	12345678	987654	en,es,fr	standard	videos/dQw4w9WgXcQ/video.mp4	downloaded	2026-01-24T12:00:00Z
```

**Usage**:
- Efficient querying without parsing individual JSON files
- Loaded by web UI for fast filtering/search
- Can be analyzed with DuckDB, Visidata, Excel

---

### playlists.tsv

Tab-separated file with summary metadata for all playlists (FR-034).

**Columns**:
```
playlist_id	title	channel_id	channel_name	video_count	total_duration	updated_at	last_sync
```

**Example**:
```
PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf	Python Tutorial	UCCezIgC97PvUuR4_gbFUs5g	Corey Schafer	42	25680	2026-01-20T10:30:00Z	2026-01-24T12:00:00Z
```

**Usage**:
- Browse playlists without loading full metadata
- Aggregate statistics at playlist level
- Filter playlists by channel, video count, etc.

---

## Schema Validation

**JSON Schema location**: `annextube/schema/models.json`

**Frontend type generation**:
- TypeScript types generated from JSON Schema
- Ensures frontend correctly consumes library output (Constitution Principle IX)
- Validation at both library output and frontend input

**Validation tools**:
- Backend: Python `jsonschema` library validates output
- Frontend: Generated TypeScript types ensure compile-time safety
- CI: Schema validation tests in contract test suite

---

## File Organization Example

```
archive-repo/
├── .sync/
│   └── state.json                 # SyncState array
├── .config/
│   └── filters.json               # FilterConfig array
├── channels/
│   └── {channel_id}/
│       └── metadata.json          # Channel
├── videos/
│   ├── {video_id}/
│   │   ├── metadata.json          # Video
│   │   ├── video.mp4              # Video file (git-annex)
│   │   ├── thumbnail.jpg          # Thumbnail (git-annex)
│   │   ├── comments.json          # Comment array
│   │   └── captions/
│   │       ├── en.vtt             # Caption (English)
│   │       └── es.vtt             # Caption (Spanish)
│   └── ...
├── playlists/
│   └── {playlist_id}/
│       ├── metadata.json          # Playlist
│       └── {video_id}/            # Symlink → ../../videos/{video_id}/
├── videos.tsv                     # Video summary (all videos)
└── playlists.tsv                  # Playlist summary (all playlists)
```

---

## Denormalization Strategy

**Denormalized fields** (for query efficiency):
- `Video.channel_name`: Avoids joining to Channel for display
- `Playlist.channel_name`: Same rationale
- Summary TSV files: Pre-aggregated for fast access

**Rationale**:
- File-based storage lacks JOIN operations
- Denormalization enables efficient querying without database
- Aligns with Constitution Principle XI: Resource Efficiency (CPU)

**Trade-off**:
- Storage: Minimal overhead (channel names are small strings)
- Update complexity: When channel name changes, update all videos (rare occurrence)
- Benefit: Fast queries without parsing multiple files

---

## Update Strategy

**Incremental updates** (FR-010 to FR-016):

1. **Load SyncState**: Read `.sync/state.json` to get `last_sync` timestamp
2. **Fetch new videos**: Query YouTube API for videos published after `last_sync`
3. **Detect metadata changes**: Compare fetched metadata with stored `metadata.json`
4. **Update comments**: Fetch comments for videos with `comment_count` increase
5. **Update captions**: Fetch captions for videos with new `captions_available`
6. **Update SyncState**: Write new `last_sync`, `last_video_id`, update TSV files

**Efficiency**:
- Use yt-dlp archive file (tracks processed video IDs)
- Skip videos with matching `updated_at` timestamp
- Batch API requests where possible

---

## Relationships

```
Channel 1───N Video
   │
   └────── 1───N Playlist

Video 1───N Caption
  │
  └────── 1───N Comment (with replies as nested structure)

Playlist N───M Video (many-to-many via symlinks)

SyncState 1───1 Channel (or Playlist)

FilterConfig N───M Video (applied during archival)
```

**Relationship implementation**:
- **One-to-many**: Array of IDs (e.g., `Channel.videos`, `Video.captions_available`)
- **Many-to-many**: Symlinks (playlists reference videos via filesystem symlinks)
- **Foreign keys**: IDs reference other entities (e.g., `Video.channel_id` → `Channel.channel_id`)

---

## Version History

**v1.0.0** (2026-01-24): Initial data model
- Defined 7 core entities (Channel, Video, Playlist, Caption, Comment, SyncState, FilterConfig)
- Established TSV summary files (videos.tsv, playlists.tsv)
- File-based storage strategy aligned with Constitution Principle XI
