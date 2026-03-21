# Feature Specification: Multi-Channel Collections

**Feature Branch**: `003-multi-channel-collections`
**Created**: 2026-03-21
**Status**: Draft
**Input**: Users archiving multiple YouTube channels need a composable structure that organizes channels into separate directories, provides per-channel and collection-level metadata summaries, supports a top-level overview across all channels, and works with the existing web interface.

## Clarifications

### Session 2026-03-12

- Q: Should the collection have its own configuration with a `[collection]` section? -> A: Yes, collection gets a configuration file with `[collection]` section for defaults, common config path, and push settings.
- Q: Should `collection add` run the first backup automatically? -> A: Default is init+backup; `--no-backup` flag skips the backup step.
- Q: Sequential or parallel channel backups in `collection backup`? -> A: Sequential by default, opt-in parallelism via `--parallel N` flag.
- Q: How should `collection add` derive subdataset directory names? -> A: Auto-derive from @handle, allow `--name` override. Fail if directory exists.

## User Scenarios & Testing

### User Story 1 - Aggregate Existing Channel Archives (Priority: P1)

A researcher has independently created multiple single-channel archives and wants to combine them into a unified collection with a top-level summary, without modifying any individual channel archive.

**Why this priority**: This is the foundational capability that everything else builds on. Without discovery and aggregation, there is no collection. It also delivers immediate value to users who already have single-channel archives created via 001-youtube-backup. This capability is the simplest to implement and has no dependencies on other stories.

**Independent Test**: Can be fully tested by placing two or more existing single-channel archives (each with a `channel.json` file) into a parent directory, running the aggregate command, and verifying a `channels.tsv` summary file is produced at the root with correct metadata for each channel.

> **Implementation Note**: The `aggregate` command and `export --channel-json` flag are already implemented and functional.

**Acceptance Scenarios**:

1. **Given** a directory containing two or more channel archives each with a `channel.json` file, **When** user runs the aggregate command, **Then** a `channels.tsv` file is generated at the root containing one row per channel with key metadata fields (channel ID, title, handle, video count, date range, directory path)
2. **Given** a single-channel archive without a `channel.json`, **When** user runs the export command with the channel-json flag, **Then** a `channel.json` file is generated containing channel metadata and archive statistics derived from local data
3. **Given** channel archives organized in a nested directory structure (e.g., grouped by organization), **When** user runs the aggregate command with increased discovery depth, **Then** all channels are discovered regardless of nesting level and included in `channels.tsv`
4. **Given** an existing `channels.tsv`, **When** user runs the aggregate command again after adding a new channel archive, **Then** `channels.tsv` is regenerated to include the new channel alongside existing ones
5. **Given** a directory with no `channel.json` files, **When** user runs the aggregate command, **Then** the system reports that no channels were found and does not create an empty `channels.tsv`

---

### User Story 2 - Browse Multi-Channel Collection via Web Interface (Priority: P1)

A user wants to browse their multi-channel collection through the web interface, seeing an overview of all channels with the ability to drill into individual channel video listings.

**Why this priority**: The web interface is the primary way most users interact with their archives. A collection without browsing is just files on disk. This story delivers the visual overview that makes multi-channel collections useful and navigable.

**Independent Test**: Can be tested by generating the web interface for a collection with `channels.tsv`, opening it in a browser, verifying the channel overview page loads, and clicking through to individual channel video listings.

**Acceptance Scenarios**:

1. **Given** a collection with `channels.tsv` and per-channel `videos.tsv` files, **When** user opens the web interface, **Then** a channel overview page is displayed showing all channels with their titles, statistics, and navigation links
2. **Given** the channel overview page, **When** user selects a specific channel, **Then** the interface displays that channel's video listing loaded from the channel's own `videos.tsv`
3. **Given** a single-channel archive (no `channels.tsv`), **When** user opens the web interface, **Then** the existing single-channel view is displayed unchanged (backward compatibility)
4. **Given** a multi-channel web interface, **When** user is viewing a channel's videos, **Then** breadcrumb navigation allows returning to the channel overview
5. **Given** a collection with 10 channels averaging 200 videos each, **When** user navigates to a channel, **Then** the video listing loads within 2 seconds on a standard connection

---

### User Story 3 - Add a New Channel to a Collection (Priority: P2)

An archivist maintaining a collection wants to add a new YouTube channel with a single command that handles all setup steps: creating the channel archive directory, initializing it with collection-wide defaults, and optionally running the first backup.

**Why this priority**: Adding channels to a collection manually requires multiple steps (create directory, initialize, configure, backup, register). A streamlined single-command workflow removes friction and reduces errors, especially for users managing many channels. This depends on Story 1 being functional.

**Independent Test**: Can be tested by running the add command against a collection directory with a YouTube channel URL, and verifying the new channel directory is created, initialized with collection defaults, and (optionally) populated with its first backup.

**Acceptance Scenarios**:

1. **Given** an existing collection, **When** user runs the add command with a YouTube channel URL, **Then** a new channel archive is created as a subdataset with a directory name derived from the channel handle
2. **Given** an existing collection with default settings configured, **When** user adds a new channel, **Then** the new channel inherits collection-level defaults (comment depth, curation settings, playlist inclusion)
3. **Given** a channel URL and `--name` override, **When** user runs the add command, **Then** the channel archive is created using the specified directory name instead of the auto-derived name
4. **Given** a collection where a directory with the derived name already exists, **When** user runs the add command, **Then** the system reports an error and does not overwrite the existing directory
5. **Given** the add command without `--no-backup`, **When** the channel is initialized, **Then** the first backup runs automatically and results are saved at both channel and collection levels
6. **Given** the add command with `--no-backup`, **When** the channel is initialized, **Then** only initialization occurs and no backup is performed

---

### User Story 4 - Batch Update All Channels in a Collection (Priority: P2)

A system administrator runs periodic backups of a collection containing multiple channels and wants a single command that updates all channels, reports results, and optionally pushes to a remote.

**Why this priority**: Manual per-channel updates do not scale. Automated batch backup is essential for maintaining collections as a cron job or scheduled task. This replaces fragile shell loops with robust, resumable batch processing. Depends on channels being set up (Stories 1 or 3).

**Independent Test**: Can be tested by running the batch backup command on a collection with two or more channels, verifying each channel receives an update attempt, and checking the aggregate result report.

**Acceptance Scenarios**:

1. **Given** a collection with 3 channels, **When** user runs the collection backup command, **Then** each channel is updated sequentially and a summary report shows success/failure status per channel
2. **Given** a collection backup where one channel fails, **When** backup completes, **Then** all remaining channels are still attempted, the failure is reported with reason, and the exit code indicates partial failure
3. **Given** the `--parallel N` flag, **When** user runs collection backup, **Then** up to N channels are updated concurrently
4. **Given** the `--push` flag, **When** all channels are updated, **Then** changes are pushed to the configured remote for each channel and the collection
5. **Given** the `--save` flag, **When** all channels are updated, **Then** changes are recorded at the collection level after all channel updates complete
6. **Given** a channel with uncommitted local changes, **When** collection backup runs, **Then** the system either saves those changes first or warns and skips that channel (does not lose data)

---

### User Story 5 - Collection-Level Configuration (Priority: P2)

A collection maintainer wants to define default settings once at the collection level so that every new channel added inherits consistent configuration without manual per-channel setup.

**Why this priority**: Without collection-level defaults, each channel must be configured individually, leading to inconsistency and extra effort. This is a force multiplier for Stories 3 and 4.

**Independent Test**: Can be tested by creating a collection with default settings, adding a new channel, and verifying the channel inherits the collection defaults.

**Acceptance Scenarios**:

1. **Given** a collection with default settings (comment depth, curation mode, playlist inclusion), **When** user adds a new channel, **Then** the channel's configuration reflects those defaults
2. **Given** a collection with a common configuration file path specified, **When** user adds a new channel, **Then** the common configuration is embedded into the new channel's setup
3. **Given** a collection with a configured push remote, **When** user runs collection backup with the push flag, **Then** changes are pushed to that configured remote
4. **Given** a channel that was added with collection defaults, **When** user modifies the channel's own configuration, **Then** the per-channel settings override the collection defaults for that channel

---

### User Story 6 - Add an Existing External Archive to a Collection (Priority: P3)

A collaborator wants to incorporate an existing channel archive (hosted on a remote or shared via a URL) into their local collection without re-downloading all the content.

**Why this priority**: Sharing and composing archives is a natural extension of the collection model. This enables collaboration and distribution of archival effort across teams. Lower priority because it requires existing archives to be published first.

**Independent Test**: Can be tested by cloning a published channel archive into a collection directory and verifying it appears in the aggregated `channels.tsv`.

**Acceptance Scenarios**:

1. **Given** a published channel archive URL, **When** user clones it into a collection directory, **Then** the archive is registered as a subdataset
2. **Given** a newly cloned archive in a collection, **When** user runs the aggregate command, **Then** `channels.tsv` includes the newly added channel with correct metadata
3. **Given** a cloned archive, **When** user runs collection backup, **Then** the cloned channel is updated alongside locally created channels

---

### User Story 7 - Cross-Channel Search and Navigation (Priority: P4)

A researcher browsing a multi-channel collection wants to search across all channels simultaneously, finding videos by keyword, date, or other metadata regardless of which channel they belong to.

**Why this priority**: Cross-channel search adds significant value for large collections but requires all per-channel data to be loaded and indexed. This is an enhancement on top of the core browsing experience (Story 2).

**Independent Test**: Can be tested by opening the web interface for a multi-channel collection, entering a search query, and verifying results include matching videos from multiple channels.

**Acceptance Scenarios**:

1. **Given** a multi-channel collection web interface, **When** user enters a search term, **Then** results include matching videos from all channels with channel attribution
2. **Given** a date range filter on the overview page, **When** user applies the filter, **Then** only channels with videos in that range are highlighted, and drill-down shows matching videos
3. **Given** search results spanning multiple channels, **When** user selects a video, **Then** navigation includes context for returning to cross-channel results

---

### Edge Cases

- What happens when a channel archive has no `channel.json`? The aggregate command skips it and logs a warning. The archive continues to work standalone.
- What happens when `channels.tsv` references a channel directory that no longer exists? The web interface handles the missing directory gracefully, displaying an error for that channel without affecting others.
- How does the system handle a collection with only one channel? It works identically to multi-channel mode but displays a single channel in the overview.
- What happens when two channels in a collection have the same channel ID? The aggregate command warns about duplicates and includes both entries with their distinct directory paths.
- How does the system handle channels with very large video counts (10,000+)? Per-channel loading in the web interface prevents memory issues since only one channel's data is loaded at a time.
- What happens when the user adds a channel whose handle conflicts with an existing directory name? The add command fails with a clear error suggesting the `--name` override flag.
- How does the system handle interrupted batch backups? Each channel is processed independently; partial progress within a channel is preserved, and the summary report indicates which channels completed.
- What happens when collection configuration defaults conflict with a channel's existing settings? Per-channel configuration always takes precedence over collection defaults.

## Requirements

### Functional Requirements

#### Discovery and Aggregation

- **FR-001**: System MUST discover channel archives by scanning for `channel.json` files within a directory tree up to a configurable depth (default: 1, maximum: 3)
- **FR-002**: System MUST generate a `channels.tsv` summary file at the collection root containing one row per discovered channel with: channel ID, title, custom URL/handle, description, subscriber count, video count, playlist count, total videos archived, first video date, last video date, last sync timestamp, and relative directory path
- **FR-003**: System MUST compute archive statistics (total videos archived, date range) from each channel's local `videos.tsv` rather than relying on remote API data
- **FR-004**: System MUST generate a `channel.json` metadata file for a single-channel archive containing channel metadata and archive statistics derived from local data
- **FR-005**: System MUST sort channels in `channels.tsv` by channel title for consistent ordering

> **Note**: FR-001 through FR-005 are implemented via the existing `aggregate` command and `export --channel-json` flag.

#### Collection Management

- **FR-006**: System MUST provide a command to add a new channel to a collection that creates a subdataset, initializes the channel archive, and optionally runs the first backup
- **FR-007**: System MUST auto-derive the subdataset directory name from the channel's @handle when no explicit name is provided
- **FR-008**: System MUST fail with a clear error if the derived or specified directory name conflicts with an existing directory
- **FR-009**: System MUST apply collection-level default settings to newly added channels
- **FR-010**: System MUST support a flag to skip the initial backup when adding a channel (init-only mode)
- **FR-011**: System MUST embed a common configuration file into new channels when a common config path is specified at the collection level

#### Batch Operations

- **FR-012**: System MUST provide a command to update all channels in a collection sequentially by default
- **FR-013**: System MUST support opt-in parallel channel updates with a configurable concurrency limit
- **FR-014**: System MUST continue processing remaining channels when one channel's update fails
- **FR-015**: System MUST produce a summary report after batch operations showing per-channel success/failure status with failure reasons
- **FR-016**: System MUST exit with a non-zero code when any channel update fails, while still completing all remaining attempts
- **FR-017**: System MUST support an option to save all changes at the collection level after batch updates complete
- **FR-018**: System MUST support an option to push changes to a configured remote after batch updates complete

#### Configuration

- **FR-019**: System MUST support a collection-level configuration section defining default settings for new channels (comment depth, curation mode, playlist inclusion, podcast inclusion)
- **FR-020**: System MUST support specifying a common configuration file path at the collection level for embedding into new channels
- **FR-021**: System MUST support configuring a push remote at the collection level for batch push operations
- **FR-022**: Per-channel configuration MUST take precedence over collection-level defaults

#### Web Interface

- **FR-023**: Web interface MUST auto-detect multi-channel mode by checking for the presence of `channels.tsv` at the archive root
- **FR-024**: In multi-channel mode, web interface MUST display a channel overview page showing all channels with titles, statistics, and navigation
- **FR-025**: In multi-channel mode, web interface MUST load per-channel video listings from each channel's own `videos.tsv` on demand
- **FR-026**: Web interface MUST provide breadcrumb navigation between channel overview and individual channel views
- **FR-027**: In single-channel mode (no `channels.tsv`), web interface MUST behave identically to existing behavior (full backward compatibility)

#### Backward Compatibility and Composability

- **FR-028**: Single-channel archives created by the existing backup system MUST continue to work without modification
- **FR-029**: Each channel archive within a collection MUST be independently usable as a standalone archive
- **FR-030**: Collections MUST use composable subdatasets so that individual channels can be independently versioned, pushed, pulled, and shared (Constitution Principle XIII: DataLad-Native Operations)
- **FR-031**: System MUST NOT require a database or server process for collection management (Constitution Principle XI: Storage Simplicity)
- **FR-032**: Directory naming within a collection MUST be flexible -- discovery relies on `channel.json` presence, not naming conventions

### Key Entities

- **Collection**: A container for multiple channel archives. Represented as a directory (superdataset) containing channel subdirectories, a `channels.tsv` summary, and optional collection-level configuration. Each channel is an independent, composable subdataset.
- **Channel Archive**: An independent archive of a single YouTube channel containing videos, metadata, captions, comments, and summary files (`videos.tsv`, `playlists.tsv`, `channel.json`). Can exist standalone or as part of a collection.
- **channels.tsv**: A tab-separated summary file at the collection root providing an overview of all channels with key metadata and directory paths. Analogous to `videos.tsv` at the channel level.
- **channel.json**: A per-channel metadata file containing detailed channel information and computed archive statistics. Used for discovery by the aggregate command.
- **Collection Configuration**: A configuration section at the collection level defining defaults for new channels, common config paths, and push remote settings.

## Success Criteria

### Measurable Outcomes

- **SC-001**: User can combine two or more existing single-channel archives into a collection and generate a unified summary within 5 manual steps or fewer
- **SC-002**: Web interface correctly displays channel overview when `channels.tsv` is present and falls back to single-channel mode when it is absent, with zero user configuration required
- **SC-003**: Adding a new channel to an existing collection requires a single command (excluding the initial collection creation)
- **SC-004**: Batch backup of a 10-channel collection completes with per-channel status reporting, continuing past individual failures without manual intervention
- **SC-005**: A channel archive created within a collection works identically when extracted and used standalone (full independence)
- **SC-006**: Collection-level defaults are correctly inherited by newly added channels, reducing per-channel configuration steps to zero for standard setups
- **SC-007**: The batch backup command can replace existing multi-channel cron scripts, reducing the cron configuration to a single command per collection
- **SC-008**: Channel overview page in the web interface loads within 2 seconds for collections of up to 50 channels
- **SC-009**: All collection data is stored in human-readable, version-controllable file formats (TSV, JSON, TOML) with no database dependency
