# Feature Specification: YouTube Archive System

**Feature Branch**: `001-youtube-backup`
**Created**: 2026-01-24
**Status**: Draft
**Input**: User description: "We would like to backup and keep updating such a backup (with new videos, closed captures, and comments) a collection of videos from YouTube. It might be an entire channel (with some filters on what to include or exclude) with all or selected set of playlists, or a specific playlist, like e.g. liked videos. What to backup (just videos or may be comments etc) should be configurable, and backup solution should be efficient in its detection on what has changed in a given source to fetch updates etc. Filters could also be dates based, or other metadata based (e.g. backup only content under specific licenses like creative commons etc). Underlying backup would be a datalad repository with git-annex, and git-annex would need to have files added via its support of downloads from youtube, so later videos could be re-fetched using yt-dlp (relaxed URL annex backend to be used for them). File tree hierarchy would be configurable to allow for customization, generally would allow to separate out all videos from playlists. Likely to have a folder per youtube video in most of the cases, to keep nearby all relevant to that video data, like closed captions in various languages, metadata dump, comments. git-annex will also have metadata for the video associated with the original file. Also potentially have a top level videos/ folder where to collect all folders per posted video, and then playlists/ folder where per playlist just assemble symlinks to the folders under videos/ so we could scale for the cases where the same video is present in multiple playlists. Specific attention to be payed to updates since comments and closed captions would be updating. Ideally we should plan also for workflows to update automatically generated closed captions for upload back into youtube having them fixed up, so it would not only be a backup but curation platform. Similarly to mykrok project, we would like to establish top level aggregates of summary metadata across videos and playlists which would have most important metadata propagated and summarized at the top level for efficient navigation of the collection. For the web frontend we want a purely client-based software like we did in mykrok with interfaces for filtering based on time range on when videos were released or updated, tags, authors or people associated with them. CLI and library interfaces should allow for logging control to troubleshoot, forcing updates for older dates/videos. Web frontend should provide convenient means to navigate the collection, search, see comments, and potentially integrate with external services to edit closed captions or pass them to LLMs for tune ups. Detailed documentation following the principle https://diataxis.fr/ and having demo served through gh-pages."

## Clarifications

### Session 2026-01-24

- Q: What should be the core dependency for git/git-annex operations? → A: Use datasalad (https://hub.datalad.org/datalad/datasalad) as the core library for efficient git/git-annex command execution, prioritizing its interfaces for external command execution where possible
- Q: What documentation system should be used? → A: Hugo static site generator with congo theme (https://github.com/jpanther/congo)
- Q: How should git vs git-annex configuration be managed? → A: Initial configuration specified via create-dataset command options, with persistent rules stored in .gitattributes file
- Q: How should subdataset structure be supported? → A: Support subdataset creation when path specification contains '//' separator (similar to CON/tinuous pattern, e.g., 'videos/{year}//{month}' creates year-based subdatasets)
- Q: What CI/CD platforms should be supported? → A: GitHub Actions, Codeberg Actions, and Forgejo instances (e.g., https://codeberg.org/forgejo-aneksajo/forgejo-aneksajo/), with two modes: index-only updates (fetch metadata/comments) and full backup (push content to git-annex remotes)
- Q: How should git-annex storage be handled in CI? → A: Support configuration of git-annex special remotes (S3, WebDAV, directory, etc.) for automated content storage, allowing content to be pushed to pre-configured remotes while updating index on git hosting

## User Scenarios & Testing

### User Story 1 - Initial Channel Archive (Priority: P1)

A researcher wants to create a complete archive of a YouTube channel for preservation and offline access, capturing all videos with their metadata, thumbnails, and captions.

**Why this priority**: This is the core value proposition - being able to preserve YouTube content that might be deleted or become unavailable. Without this functionality, the entire system has no purpose.

**Independent Test**: Can be fully tested by running a single command to backup a channel and verifying all videos are tracked (even if not downloaded) with their metadata accessible offline.

**Acceptance Scenarios**:

1. **Given** a YouTube channel URL, **When** user initiates backup with default settings, **Then** system creates repository structure, tracks all public videos from the channel (ordered by upload date, newest first), and stores metadata for each video
2. **Given** a channel with multiple playlists, **When** backup completes, **Then** system organizes videos logically and creates both playlist and video-centric views
3. **Given** limited disk space, **When** backup is initiated, **Then** system tracks video URLs without downloading content (via git-annex addurl --relaxed --fast), allowing selective download later
4. **Given** a video with multiple caption languages, **When** backup runs, **Then** system downloads all available captions as separate VTT files per language (using yt-dlp --write-subs)
5. **Given** a "Liked Videos" playlist, **When** user initiates backup with proper API credentials, **Then** system archives all liked videos with full metadata (HIGH PRIORITY test case)

---

### User Story 2 - Incremental Updates (Priority: P1)

A content curator runs daily updates to capture new videos, new comments, and updated captions from channels they archive, efficiently detecting and fetching only what changed.

**Why this priority**: Static backups become stale quickly. The ability to incrementally update is essential for maintaining a current archive and is a core efficiency feature that distinguishes this from one-time downloads.

**Independent Test**: Can be tested by creating an archive, simulating passage of time (or using test data), running update, and verifying only new/changed content is fetched.

**Acceptance Scenarios**:

1. **Given** an existing archive from yesterday, **When** user runs update command, **Then** system identifies and fetches only new videos published since last sync
2. **Given** videos with new comments, **When** update runs, **Then** system fetches updated comment data without re-downloading video files
3. **Given** updated auto-generated captions, **When** update runs, **Then** system detects caption changes and fetches new versions
4. **Given** a channel with 1000 videos but only 2 new ones, **When** update runs, **Then** system completes in under 5 minutes (not re-checking all 1000 videos inefficiently)

---

### User Story 3 - Selective Filtering and Scope Control (Priority: P2)

An archivist wants to backup only specific content from a channel based on criteria like date range, playlist membership, license type, or video metadata to manage storage and focus on relevant content.

**Why this priority**: Not all users want complete archives. Filtering enables targeted preservation and makes the tool practical for users with storage constraints or specific research needs.

**Independent Test**: Can be tested by configuring filters (e.g., "only Creative Commons licensed videos from 2024"), running backup, and verifying only matching videos are included in the archive.

**Acceptance Scenarios**:

1. **Given** a channel with videos under different licenses, **When** user filters for Creative Commons only, **Then** system archives only CC-licensed videos
2. **Given** a date range filter for 2024-01-01 to 2024-12-31, **When** backup runs, **Then** system includes only videos published in that range
3. **Given** a channel with 50 playlists, **When** user specifies 3 playlists to backup, **Then** system archives only videos from those playlists
4. **Given** metadata filters like "videos longer than 10 minutes", **When** applied, **Then** system excludes shorter videos from archive

---

### User Story 4 - Browse and Search Archive via Web Interface (Priority: P2)

A user wants to browse their offline YouTube archive through a web interface that works without a server, allowing them to search, filter by date/tags/author, watch videos, read comments, and view captions.

**Why this priority**: An archive is only useful if users can access the content. A client-side web interface provides excellent usability without infrastructure requirements, making archives portable and easy to share.

**Independent Test**: Can be tested by generating the web interface, opening it in a browser (file:// protocol), and verifying search, filtering, video playback, and comment display all work without a backend server.

**Acceptance Scenarios**:

1. **Given** an archive with web interface generated, **When** user opens index.html in browser, **Then** interface displays all videos with thumbnails, titles, and metadata
2. **Given** web interface is open, **When** user applies date range filter, **Then** only videos from that date range are displayed
3. **Given** a video in the interface, **When** user clicks to view, **Then** video plays with available captions selectable
4. **Given** a video with comments, **When** user views video details, **Then** comments are displayed in chronological or ranked order
5. **Given** web interface on file:// protocol, **When** user performs search for keyword, **Then** results appear instantly without requiring network access

---

### User Story 5 - Configurable Organization Structure (Priority: P3)

A power user wants to customize how videos are organized on disk (e.g., by year, by playlist, flat vs nested), including support for videos appearing in multiple playlists without duplication.

**Why this priority**: Different use cases (long-running channels, multi-topic channels, research collections) benefit from different organizational schemes. This adds flexibility but isn't essential for basic archival.

**Independent Test**: Can be tested by configuring custom hierarchy templates, running backup, and verifying files are organized according to the specified structure.

**Acceptance Scenarios**:

1. **Given** configuration for "videos/ + playlists/ with symlinks", **When** backup runs, **Then** videos are stored once under videos/ and playlists contain symlinks
2. **Given** a date-based hierarchy template "videos/{year}/{video_id}/", **When** backup runs, **Then** videos are organized into year folders
3. **Given** a video in multiple playlists, **When** organized with symlink strategy, **Then** video content exists once with symlinks from each playlist folder
4. **Given** custom file naming template, **When** backup runs, **Then** files follow specified naming convention

---

### User Story 6 - Export Summary Metadata (Priority: P3)

A data analyst wants to export high-level metadata about all videos and playlists in tab-separated format for analysis with tools like Excel, DuckDB, or Visidata.

**Why this priority**: Enables integration with data analysis workflows and provides lightweight access to archive metadata without parsing individual video files. Useful but not critical for basic archival.

**Independent Test**: Can be tested by running metadata export command and verifying TSV files are created with correct columns and can be opened in spreadsheet software or queried with DuckDB.

**Acceptance Scenarios**:

1. **Given** an archive with 100 videos, **When** user runs metadata export, **Then** videos.tsv is created with one row per video containing key fields
2. **Given** an archive with playlists, **When** export runs, **Then** playlists.tsv is created with playlist-level aggregates
3. **Given** TSV files exist, **When** user opens in Visidata, **Then** data is properly formatted and filterable
4. **Given** exported TSV, **When** user queries with SQL tool, **Then** metadata is accessible for analysis

---

### User Story 7 - Caption Curation Workflow (Priority: P4)

A content creator wants to download auto-generated captions, edit them for accuracy, and have a workflow to upload corrected versions back to YouTube, using the archive as a curation platform.

**Why this priority**: Transforms the tool from read-only backup to a content improvement workflow. Valuable for creators but not essential for preservation use cases.

**Independent Test**: Can be tested by exporting captions, modifying them, and verifying the system can prepare them for upload (actual upload would require YouTube API credentials).

**Acceptance Scenarios**:

1. **Given** a video with auto-generated captions, **When** user exports for editing, **Then** captions are provided in editable VTT format
2. **Given** edited captions, **When** user marks for upload, **Then** system validates format and prepares upload command
3. **Given** integration with external editor service, **When** user sends captions to LLM, **Then** interface provides corrected captions ready for upload
4. **Given** batch caption export, **When** user selects multiple videos, **Then** all captions are exported in consistent format for batch processing

---

### User Story 8 - Public Archive Hosting (Priority: P4)

An educator wants to publish their YouTube archive as a public website (via GitHub Pages or similar), allowing others to browse and access preserved content.

**Why this priority**: Enables sharing and public access to archived content, which is valuable for educational and preservation use cases but not core to the backup functionality itself.

**Independent Test**: Can be tested by running the publish command, pushing to GitHub Pages, and verifying the archive is accessible via public URL with all functionality working.

**Acceptance Scenarios**:

1. **Given** a local archive, **When** user runs publish command, **Then** static site is generated suitable for hosting on GitHub Pages
2. **Given** published archive, **When** accessed via public URL, **Then** web interface works identically to local version
3. **Given** large video files, **When** published, **Then** system provides option to host videos separately or link to YouTube
4. **Given** published archive, **When** user wants to update, **Then** incremental publish updates only changed files

---

### Edge Cases

- **What happens when a video is deleted from YouTube?** Archive retains the downloaded content and metadata, marking video as "unavailable at source" in metadata
- **What happens when a video becomes private or unlisted?** System retains what was already archived but cannot fetch updates; metadata reflects changed availability
- **How does system handle very large channels (10,000+ videos)?** Hierarchical organization (by year, by first letter of ID, etc.) prevents filesystem limitations
- **What happens when YouTube rate-limits requests?** System implements exponential backoff, respects rate limits, and can resume interrupted operations
- **How does system handle videos with no captions?** Gracefully skips caption download, logs absence, and marks in metadata
- **What happens when comments are disabled?** Marks in metadata, skips comment fetching without error
- **How does system handle network interruptions during backup?** Implements resumable downloads and can continue from last successful point
- **What happens when a playlist is deleted?** Archive retains playlist metadata and videos, marks playlist as deleted
- **How does system handle videos in multiple playlists with different organizational strategies?** Symlink strategy ensures single storage with multiple access paths
- **What happens when disk space runs out during backup?** System detects low space, pauses gracefully, and provides clear error message with recovery options

## Requirements

### Functional Requirements

#### Core Archival Capabilities

- **FR-001**: System MUST support archiving entire YouTube channels by URL
- **FR-002**: System MUST support archiving individual playlists by URL
- **FR-003**: System MUST support archiving specific videos by URL or ID list
- **FR-004**: System MUST track video URLs without downloading content (lazy download strategy)
- **FR-005**: System MUST download and store video metadata including title, description, publication date, duration, view count, like count, channel info
- **FR-006**: System MUST download and store video thumbnails at highest available resolution
- **FR-007**: System MUST download closed captions in all available languages as separate VTT files per language
- **FR-008**: System MUST download video comments including comment text, author, timestamp, like count, and reply threads
- **FR-009**: System MUST support selective download of video content based on user configuration

#### Incremental Updates and Change Detection

- **FR-010**: System MUST efficiently detect new videos added to channels since last sync
- **FR-011**: System MUST efficiently detect new videos added to playlists since last sync
- **FR-012**: System MUST detect and fetch updated comments on existing videos
- **FR-013**: System MUST detect and fetch updated or newly available captions
- **FR-014**: System MUST detect changes in video metadata (title, description, etc.)
- **FR-015**: System MUST maintain sync state tracking last successful update per channel/playlist
- **FR-016**: System MUST complete incremental updates in reasonable time (not re-checking all content)

#### Filtering and Scope Control

- **FR-017**: System MUST support filtering videos by publication date range
- **FR-018**: System MUST support filtering videos by license type (e.g., Creative Commons, Standard YouTube License)
- **FR-019**: System MUST support filtering videos by playlist membership
- **FR-020**: System MUST support filtering videos by metadata attributes (duration, view count, etc.)
- **FR-021**: System MUST support exclusion filters (e.g., exclude shorts, exclude specific playlists)
- **FR-022**: System MUST allow users to specify what components to backup (videos, metadata, comments, captions) via configuration

#### Repository Structure and Organization

- **FR-023**: System MUST create and maintain git-annex repository for content storage, with initial configuration option to specify what content types go under git vs git-annex
- **FR-024**: System MUST use git for text metadata (JSON, TSV, VTT, markdown) and git-annex for binary/large files (videos, thumbnails), configured via .gitattributes file that persists rules for the repository
- **FR-025**: System MUST organize video content in configurable hierarchy templates (by date, by playlist, by channel, custom), supporting subdataset creation when path specification contains '//' separator (e.g., 'videos/{year}//{month}' creates year-based subdatasets)
- **FR-026**: System MUST support per-video folder structure containing video file, captions, metadata, comments
- **FR-027**: System MUST support symlink-based organization for videos in multiple playlists
- **FR-028**: System MUST store file naming templates in configuration for customization, supporting patterns like `{date}_{video_id}_{sanitized_title}/` that combine publication date, persistent video ID, and sanitized title
- **FR-029**: System MUST store video files with source URL references to enable re-downloading from original source
- **FR-030**: System MUST store metadata for videos including source URL, fetch date, video ID

#### Metadata Aggregation and Export

- **FR-031**: System MUST generate top-level videos.tsv file with summary metadata for all videos
- **FR-032**: System MUST generate playlists.tsv file with summary metadata for all playlists
- **FR-033**: System MUST include in videos.tsv: video ID, title, channel, published date, duration, view count, like count, comment count, has captions, file path
- **FR-034**: System MUST include in playlists.tsv: playlist ID, title, channel, video count, total duration, last updated
- **FR-035**: System MUST regenerate TSV files during updates to reflect current state
- **FR-036**: System MUST export metadata in standard TSV format compatible with Excel, Visidata, DuckDB

#### Web Interface

- **FR-037**: System MUST generate client-side web interface (single HTML + assets) for browsing archive
- **FR-038**: Web interface MUST work offline via file:// protocol without backend server
- **FR-039**: Web interface MUST load metadata from TSV files on demand
- **FR-040**: Web interface MUST support filtering videos by date range
- **FR-041**: Web interface MUST support filtering videos by channel, playlist, tags
- **FR-042**: Web interface MUST support text search across video titles and descriptions
- **FR-043**: Web interface MUST display video thumbnails, metadata, and allow playback
- **FR-044**: Web interface MUST display video comments with threading
- **FR-045**: Web interface MUST allow caption selection and display during playback
- **FR-046**: Web interface MUST provide shareable URLs that preserve filter and view state
- **FR-047**: Web interface MUST support exporting captions to external services for editing via standard export formats

#### Command-Line Interface

- **FR-048**: System MUST provide CLI command to initialize new archive repository (create-dataset) with options for git/git-annex configuration (what files go under git vs git-annex)
- **FR-049**: System MUST provide CLI command to backup channel by URL
- **FR-050**: System MUST provide CLI command to backup playlist by URL
- **FR-051**: System MUST provide CLI command to run incremental update
- **FR-052**: System MUST provide CLI command to generate web interface
- **FR-053**: System MUST provide CLI command to export metadata TSV files
- **FR-054**: System MUST support configurable logging levels (debug, info, warning, error)
- **FR-055**: System MUST provide option to force re-fetch of specific videos or date ranges
- **FR-056**: CLI MUST provide progress indicators for long-running operations
- **FR-057**: CLI MUST provide clear error messages with recovery suggestions

#### Caption Curation Workflow

- **FR-058**: System MUST export captions in editable VTT format
- **FR-059**: System MUST validate caption file format before marking for upload
- **FR-060**: System MUST provide interface to prepare captions for YouTube upload
- **FR-061**: System MUST provide interface to send captions to external editing services
- **FR-062**: System MUST support batch caption export for multiple videos

#### Publishing and Sharing

- **FR-063**: System MUST generate static site suitable for GitHub Pages hosting
- **FR-064**: System MUST create isolated publishing branch without main branch history
- **FR-065**: System MUST include sample/demo data generation for public demos
- **FR-066**: System MUST provide option to publish metadata without video files (link to YouTube)
- **FR-067**: System MUST support incremental publish (only update changed files)

#### Configuration and Customization

- **FR-068**: System MUST read configuration from file in repository
- **FR-069**: Configuration MUST support specifying channels and playlists to track
- **FR-070**: Configuration MUST support filter specifications
- **FR-071**: Configuration MUST support organizational hierarchy templates
- **FR-072**: Configuration MUST support file naming templates
- **FR-073**: Configuration MUST support component selection (what to backup)
- **FR-074**: Configuration MUST support rate limiting and retry settings
- **FR-075**: Configuration file containing sensitive data MUST be stored securely and not in plain version control

#### Data Integrity and Reliability

- **FR-076**: System MUST implement retry logic with exponential backoff for failed operations
- **FR-077**: System MUST respect YouTube rate limits and API quotas
- **FR-078**: System MUST detect and handle network interruptions gracefully
- **FR-079**: System MUST support resumable operations after interruption
- **FR-080**: System MUST validate downloaded content integrity
- **FR-081**: System MUST log all errors with sufficient context for troubleshooting
- **FR-082**: System MUST maintain operation state to support idempotent operations

#### CI/CD and Automation

- **FR-083**: System MUST support running as GitHub Actions workflow for automated updates
- **FR-084**: System MUST support running on Codeberg Actions and Forgejo instances (e.g., https://codeberg.org/forgejo-aneksajo/forgejo-aneksajo/)
- **FR-085**: System MUST provide CI workflow modes: (1) index-only updates (fetch metadata/comments without video content), (2) full backup with content push to configured git-annex remotes
- **FR-086**: System MUST allow configuration of git-annex special remotes (S3, WebDAV, directory, etc.) for automated content storage
- **FR-087**: System MUST support scheduled CI runs (e.g., daily/weekly) for automatic archive updates
- **FR-088**: System MUST provide workflow templates for common CI platforms (GitHub Actions, Codeberg Actions, Forgejo)
- **FR-089**: CI workflows MUST handle authentication via environment variables or secrets management
- **FR-090**: System MUST support pushing updated index/metadata to git hosting while storing content on separate git-annex remotes

#### Git-Annex Storage Backends

- **FR-091**: System MUST support configuration of multiple git-annex special remotes in repository config
- **FR-092**: System MUST support standard git-annex special remote types (such as directory, S3, WebDAV, rsync, rclone) but overall be able to just specify which configured remote to use to push to
- **FR-093**: System MUST allow specifying preferred remotes for content storage and retrieval
- **FR-094**: System MUST support storing video content on special remotes while maintaining URL keys for re-downloading
- **FR-095**: System MUST provide commands to verify content availability on configured remotes
- **FR-096**: System MUST support initializing common special remote configurations via CLI

### Key Entities

- **Channel**: Represents a YouTube channel being archived, with attributes including channel ID, name, description, subscriber count, avatar, list of videos, list of playlists, last sync timestamp
- **Video**: Represents a YouTube video with attributes including video ID, title, description, publication date, duration, view count, like count, comment count, channel, file path, thumbnail path, caption availability, license type, download status
- **Playlist**: Represents a YouTube playlist with attributes including playlist ID, title, description, channel, video IDs (ordered list), video count, total duration, last updated, privacy status
- **Caption**: Represents closed captions for a video with attributes including language code, format (VTT), auto-generated flag, file path, last fetched timestamp
- **Comment**: Represents a comment on a video with attributes including comment ID, author, author channel, text, timestamp, like count, parent comment ID (for replies), reply count
- **SyncState**: Tracks synchronization state with attributes including source URL (channel/playlist), last sync timestamp, last video ID processed, error count, next retry timestamp
- **FilterConfig**: Defines filtering rules with attributes including date range, license types, playlist inclusion/exclusion, metadata constraints, component selection flags

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can create initial archive of 100-video channel in under 30 minutes (metadata only, without downloading videos)
- **SC-002**: Incremental updates on channel with 1000 videos and 5 new videos complete in under 5 minutes
- **SC-003**: Web interface loads and displays archive of 1000 videos in under 3 seconds on modern browser
- **SC-004**: System successfully handles channels with 10,000+ videos without filesystem or performance issues
- **SC-005**: 95% of interrupted operations can resume without re-downloading content
- **SC-006**: Users can find specific video via web interface search in under 2 seconds
- **SC-007**: System detects and archives new comments within 24 hours of running update
- **SC-008**: TSV export files can be successfully opened in common spreadsheet and data analysis tools without modification
- **SC-009**: Web interface works identically when accessed locally or via web hosting
- **SC-010**: Published archives on GitHub Pages are accessible and fully functional
- **SC-011**: Archive repository can be cloned and browsed by users with only basic large-file management tools installed
- **SC-012**: System respects YouTube rate limits with zero ban incidents in testing
- **SC-013**: Users can configure and apply filters to backup only desired content without modifying code
- **SC-014**: Documentation covers all four Diataxis categories (tutorials, how-to guides, reference, explanation)
- **SC-015**: Users successfully archive their first channel following tutorial documentation within 15 minutes

## Assumptions

- Users have git and git-annex installed on their system
- Users have basic familiarity with command-line tools
- YouTube URLs and IDs follow standard YouTube format conventions
- Network connectivity is available during sync operations
- Users have appropriate permissions to access content they are archiving (public or owned content)
- Browser used for web interface supports ES6+ JavaScript and HTML5 video
- File system supports symbolic links (for symlink-based organization)
- Users understand git/DataLad concepts for advanced usage but basic operations don't require deep knowledge
- YouTube API structure and yt-dlp compatibility remain stable or system can adapt to changes
- Users accept that deleted/private YouTube content cannot be updated after archival

## Dependencies

- **git**: Version control system for metadata and repository structure
- **git-annex**: Large file management and URL backend support (git annex addurl --relaxed --fast for URL tracking)
- **YouTube Data API v3**: Primary method for metadata, playlists, comments (requires API key)
- **yt-dlp**: Video URL extraction and caption downloading (NOT for metadata - API is preferred)
- **datasalad**: Core library for efficient git/git-annex command execution (https://hub.datalad.org/datalad/datasalad)
- **Python**: Runtime for CLI and library implementation (version 3.10+)
- **google-api-python-client**: For YouTube Data API v3 access
- **Modern web browser**: For web interface (Chrome, Firefox, Safari, Edge)
- **Hugo**: Static site generator for documentation (with congo theme recommended)
- **GitHub Pages / Codeberg Pages / Forgejo**: For demo and public archive hosting (optional)

**Prototype Reference**: `/home/yoh/proj/TrueTube/Andriy_Popyk/code/` - Working cron-based backup scripts demonstrating:
- Direct API usage (not git-annex importfeed - RSS limited to 15 videos)
- Separate caption fetching workflow
- Lock file pattern for cron safety
- Config storage in .datalad/config

## Out of Scope

- Direct video upload to YouTube (only caption upload preparation)
- Real-time monitoring of YouTube channels (polling-based updates only)
- Video transcoding or format conversion
- Automated content moderation or filtering based on content analysis
- Support for non-YouTube video platforms in initial version
- Mobile app interface (web interface works on mobile browsers)
- Multi-user collaboration features (single-user archive model)
- Video playback analytics or tracking
- Integration with video editing software
- Automated caption generation (relies on YouTube's auto-captions)
- Social features like sharing, commenting within archive
