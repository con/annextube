# Research: Multi-Channel Collections

**Feature**: 003-multi-channel-collections
**Date**: 2026-03-21
**Purpose**: Document technical patterns and decisions for multi-channel collection support

This feature builds heavily on existing infrastructure (001-youtube-backup), so research is lightweight. Most patterns are already proven in the codebase or in the mykrok reference project.

## Research Tasks

### 1. Channel Discovery Pattern (Glob-Based Scanning)

**Question**: How should the system discover channel archives within a collection directory?

**Context**:
- Channel archives are identified by the presence of a `channel.json` file
- Users may organize channels in flat or nested directory structures
- Discovery must be fast (< 1s for 50 channels)

**Research**:

The glob-based scanning pattern is already implemented in `annextube/cli/aggregate.py`:

```python
def discover_channels(root_dir: Path, depth: int = 1) -> list[tuple[Path, Path]]:
    if depth == 1:
        pattern = "*/channel.json"
    elif depth == 2:
        pattern = "*/*/channel.json"
    elif depth == 3:
        pattern = "*/*/*/channel.json"
    # ...
    for channel_json in root_dir.glob(pattern):
        channel_dir = channel_json.parent
        rel_channel_dir = channel_dir.relative_to(root_dir)
        channels.append((rel_channel_dir, channel_json))
```

This approach is proven fast (glob is OS-level directory scanning) and flexible (no naming conventions required). The mykrok project uses the same pattern for athlete discovery.

**Decision**: Use existing glob-based discovery. No changes needed.

**Status**: IMPLEMENTED

### 2. DataLad Superdataset Patterns

**Question**: How should collections use DataLad subdatasets for composability?

**Context**:
- Constitution XIII requires DataLad-native operations
- Each channel must be independently versionable and publishable
- Operations must work recursively for batch processing

**Research**:

DataLad provides three key operations for collection management:

1. **Creating subdatasets**: `datalad create -d . <name>` creates a new dataset registered as a subdataset of the current dataset. This is the correct replacement for `git submodule add` + `git init`.

2. **Adding existing datasets**: `datalad clone -d . <url>` clones an existing dataset and registers it as a subdataset. Works for GitHub URLs, SSH paths, local paths.

3. **Recursive operations**: `datalad save -r`, `datalad push -r`, `datalad get -r` operate on all subdatasets. This enables single-command collection-wide operations.

4. **Recording commands**: `datalad run -m "message" <command>` with `--explicit --output <dir>` for operations within specific subdatasets.

**Key pattern for `collection add`**:
```bash
# Create subdataset
datalad create -d . channel-name

# Init annextube within it
cd channel-name && annextube init <url>

# First backup (with provenance)
datalad run -m "Initial backup" annextube backup

# Save at collection level
cd .. && datalad save -m "Add @handle channel"
```

**Key pattern for `collection backup`**:
```bash
# For each channel subdataset:
cd channel-dir
datalad save -m "Pre-backup state"  # if dirty
datalad run -m "Regular update" annextube backup
cd ..

# After all channels:
datalad save -d . -m "Batch update"
datalad push -r  # recursive push
```

**Decision**: Use `datalad create -d .` for new subdatasets, `datalad clone -d .` for existing archives, `datalad run` for reproducible backup operations, `datalad save` for recording state.

**Risks**: DataLad Python API may differ from CLI for some operations. Validate that `datalad.api.create()` and `datalad.api.save()` work correctly for subdataset scenarios. Fall back to CLI subprocess calls if needed.

### 3. Batch Error Handling Patterns

**Question**: How should batch operations handle per-channel failures without aborting the entire collection?

**Context**:
- `collection backup` must update all channels even if some fail
- YouTube rate limiting, network errors, and yt-dlp extraction failures are common
- Users need clear reporting of what succeeded and what failed

**Research**:

The continue-on-failure pattern is straightforward:

```python
@dataclass
class ChannelResult:
    channel_dir: str
    success: bool
    error: str | None = None
    videos_added: int = 0

def backup_all(collection_dir: Path) -> list[ChannelResult]:
    results = []
    for channel in discover_subdatasets(collection_dir):
        try:
            result = backup_channel(channel)
            results.append(ChannelResult(channel.name, True, videos_added=result.count))
        except Exception as e:
            logger.error(f"Failed to backup {channel.name}: {e}")
            results.append(ChannelResult(channel.name, False, error=str(e)))
    return results
```

**Exit code convention**: 0 if all channels succeeded, 1 if any channel failed. This matches `xargs --halt never` behavior and is standard for batch tools.

**Summary report format**:
```
Backup complete: 8/10 channels updated successfully

  [ok] @apopyk (3 new videos)
  [ok] @datalad (1 new video)
  [FAIL] @example - Network timeout after 3 retries
  [FAIL] @broken - yt-dlp extraction error: Sign in to confirm...
```

**Decision**: Use simple try/except per channel with result accumulation. Non-zero exit code on any failure.

### 4. Frontend Multi-Mode Detection

**Question**: How should the web UI detect and switch between single-channel and multi-channel modes?

**Context**:
- Must work with both file:// and http:// protocols
- Must be backward compatible (existing single-channel archives unchanged)
- Detection must be fast (no unnecessary network requests)

**Research**:

The detection pattern is already implemented in `frontend/src/services/data-loader.ts`:

```typescript
private async _discoverArchiveRoot(): Promise<{
  baseUrl: string;
  isMultiChannel: boolean;
}> {
  // file:// fast-path
  if (window.location.protocol === 'file:') {
    return { baseUrl: '..', isMultiChannel: false };
  }

  // Probe for channels.tsv (multi-channel marker)
  const resp = await fetch(`${prefix}/channels.tsv`, { method: 'HEAD' });
  if (resp.ok) return { baseUrl: prefix, isMultiChannel: true };

  // Probe for videos/videos.tsv (single-channel marker)
  // ...
}
```

**Remaining work**: The file:// fast-path currently defaults to single-channel mode. For multi-channel support over file://, we need to attempt loading `channels.tsv` directly rather than using HEAD requests (which are unreliable over file://). This can use a try/catch around `fetch()` with `GET` method.

**Per-channel data loading**:
```typescript
async loadChannelVideos(channelDir: string): Promise<Video[]> {
  const response = await fetch(`${this.baseUrl}/${channelDir}/videos/videos.tsv`);
  // ...parse TSV into Video[]
}
```

**Decision**: Extend existing `DataLoader` to handle multi-channel mode for both protocols. Add `loadChannels()` method for parsing `channels.tsv`, and `loadChannelVideos(channelDir)` for on-demand per-channel loading.

### 5. Configuration Inheritance Pattern

**Question**: How should collection-level defaults propagate to new channel archives?

**Context**:
- Collection config defines defaults for `collection add`
- Per-channel config must take precedence over collection defaults
- Common config file can be embedded into new channels

**Research**:

The config system already supports TOML parsing via `annextube/lib/config.py`. The collection config adds a `[collection]` section:

```toml
# collection/.annextube/config.toml

[collection]
comments_depth = 0
curation = true
search = true
include_playlists = "all"
include_podcasts = "none"

# Common config to embed into each new channel
common_config = ".annextube/common-config.toml"

# Push settings
push_remote = "datalad-public"
```

**Inheritance flow for `collection add`**:
1. Read `[collection]` section from collection's config
2. Generate channel config template with collection defaults as initial values
3. If `common_config` path specified, copy/embed it into channel directory
4. Channel's own config takes precedence for all subsequent operations

This is a **one-time copy** pattern (not live inheritance). Once a channel is created, its config is independent. This avoids complexity of config resolution chains and aligns with DataLad's subdataset independence model.

**Decision**: One-time config copy during `collection add`. No runtime inheritance. The `embed-config` command (already implemented) handles the common config embedding.

**Implementation**: Add `CollectionConfig` dataclass to `config.py`:
```python
@dataclass
class CollectionConfig:
    comments_depth: int = 0
    curation: bool = True
    search: bool = False
    include_playlists: str = "none"
    include_podcasts: str = "none"
    common_config: str | None = None
    push_remote: str | None = None
```
