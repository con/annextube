"""Collection management service for multi-channel archives.

Provides functions for adding channels to a collection (as DataLad
subdatasets) and performing batch backups across all channels.
"""

import logging
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from datalad.api import create as datalad_create
from datalad.api import save as datalad_save

from annextube.lib.config import load_collection_config

logger = logging.getLogger(__name__)


@dataclass
class ChannelResult:
    """Result of a per-channel operation (backup, add, etc.)."""

    name: str
    success: bool
    message: str = ""


def extract_handle(url: str) -> str | None:
    """Extract the @handle from a YouTube channel URL.

    Supports:
      - https://www.youtube.com/@Handle
      - https://youtube.com/@Handle
      - https://www.youtube.com/c/ChannelName
      - https://www.youtube.com/channel/UCxxxxxxxx

    Args:
        url: YouTube channel URL

    Returns:
        The handle/name portion (without @), or None if not extractable
    """
    # Match @handle pattern
    m = re.search(r"youtube\.com/@([^/?&#]+)", url)
    if m:
        return m.group(1)

    # Match /c/Name pattern
    m = re.search(r"youtube\.com/c/([^/?&#]+)", url)
    if m:
        return m.group(1)

    # Match /channel/UCxxxx pattern
    m = re.search(r"youtube\.com/channel/([^/?&#]+)", url)
    if m:
        return m.group(1)

    return None


def discover_subdatasets(collection_dir: Path) -> list[Path]:
    """Discover channel subdatasets in a collection.

    A directory is considered a channel archive if it contains
    ``.annextube/config.toml``.

    Args:
        collection_dir: Root collection directory

    Returns:
        Sorted list of channel directory paths (absolute)
    """
    channels: list[Path] = []
    for entry in sorted(collection_dir.iterdir()):
        if not entry.is_dir():
            continue
        config_path = entry / ".annextube" / "config.toml"
        if config_path.exists():
            channels.append(entry)
    return channels


def add_channel(
    collection_dir: Path,
    url: str,
    name: str | None = None,
    no_backup: bool = False,
) -> None:
    """Add a new YouTube channel to a collection as a DataLad subdataset.

    Steps:
      1. Extract @handle from URL (or use --name override)
      2. Check that target directory does not already exist
      3. Read [collection] defaults if present
      4. Create DataLad subdataset
      5. Run ``annextube init`` with collection defaults
      6. If common_config configured: copy into channel
      7. Unless no_backup: run backup + export --channel-json
      8. Save at collection level

    Args:
        collection_dir: Path to the collection root (DataLad superdataset)
        url: YouTube channel URL
        name: Override directory name (default: derived from handle)
        no_backup: Skip the initial backup

    Raises:
        ValueError: If handle cannot be extracted and no name given,
                    or if the target directory already exists
        RuntimeError: If a subprocess command fails
    """
    # 1. Determine directory name
    handle = extract_handle(url)
    dir_name = name or handle
    if dir_name is None:
        raise ValueError(
            f"Cannot extract handle from URL: {url}\n"
            "Use --name to specify a directory name."
        )

    channel_dir = collection_dir / dir_name
    print(f"Creating channel archive: {dir_name}/")

    # 2. Check directory conflict
    if channel_dir.exists():
        raise ValueError(
            f"Directory already exists: {channel_dir}\n"
            "Use --name to specify a different name."
        )

    # 3. Read collection defaults
    coll_cfg = load_collection_config(collection_dir)

    # 4. Create DataLad subdataset
    logger.info(f"Creating DataLad subdataset at {channel_dir}")
    datalad_create(
        path=str(channel_dir),
        dataset=str(collection_dir),
        annex=True,
        description=f"annextube channel archive: {dir_name}",
        force=False,
        result_renderer="disabled",
    )
    print("  [ok] DataLad subdataset created")

    # 5. Build annextube init command with collection defaults
    init_cmd: list[str] = [
        "annextube", "init", str(channel_dir), url,
        "--datalad",
    ]
    if coll_cfg is not None:
        if coll_cfg.comments_depth is not None:
            init_cmd.extend(["--comments-depth", str(coll_cfg.comments_depth)])
        if coll_cfg.curation:
            init_cmd.append("--curation")
        else:
            init_cmd.append("--no-curation")
        if coll_cfg.search:
            init_cmd.append("--search")
        else:
            init_cmd.append("--no-search")
        init_cmd.extend(["--include-playlists", coll_cfg.include_playlists])
        init_cmd.extend(["--include-podcasts", coll_cfg.include_podcasts])
        defaults_msg = "  [ok] annextube initialized with collection defaults"
    else:
        defaults_msg = "  [ok] annextube initialized"

    _run(init_cmd, "annextube init")
    print(defaults_msg)

    # 6. Common config
    if coll_cfg and coll_cfg.common_config:
        common_src = collection_dir / coll_cfg.common_config
        if common_src.exists():
            common_dst = channel_dir / ".annextube" / "common-config.toml"
            shutil.copy2(common_src, common_dst)
            # Also run embed-config so the common values merge into the
            # channel's own config.toml (if the command exists).
            try:
                _run(
                    ["annextube", "embed-config",
                     "--config-file", str(common_dst),
                     "--output-dir", str(channel_dir)],
                    "embed common config",
                )
                print("  [ok] Common config embedded")
            except RuntimeError:
                # embed-config may not support this yet; the copy is enough
                print("  [ok] Common config copied")
        else:
            logger.warning(f"common_config not found: {common_src}")

    # 7. Backup unless --no-backup
    if not no_backup:
        _run(
            ["annextube", "backup", "--output-dir", str(channel_dir)],
            "annextube backup",
        )
        print("  [ok] Initial backup complete")

        _run(
            ["annextube", "export", "--channel-json", "--output-dir", str(channel_dir)],
            "annextube export --channel-json",
        )
        print("  [ok] channel.json generated")

    # 8. Save at collection level
    datalad_save(
        path=str(channel_dir),
        dataset=str(collection_dir),
        message=f"Add @{handle or dir_name} channel",
        result_renderer="disabled",
    )
    print("  [ok] Saved at collection level")
    print()
    print(f"Channel @{handle or dir_name} added to collection.")
    print("Run 'annextube aggregate --force' to update channels.tsv.")


def _backup_one_channel(channel_dir: Path) -> ChannelResult:
    """Back up a single channel subdataset.

    Runs ``annextube backup`` then ``annextube export --channel-json``
    inside the channel directory.

    Args:
        channel_dir: Absolute path to the channel subdataset

    Returns:
        ChannelResult with success/failure info
    """
    name = channel_dir.name
    try:
        _run(
            ["annextube", "backup", "--output-dir", str(channel_dir)],
            f"backup {name}",
        )
        _run(
            ["annextube", "export", "--channel-json", "--output-dir", str(channel_dir)],
            f"export {name}",
        )
        return ChannelResult(name=name, success=True, message="ok")
    except RuntimeError as exc:
        return ChannelResult(name=name, success=False, message=str(exc))


def backup_all(
    collection_dir: Path,
    parallel: int = 1,
    save: bool = False,
    push: bool = False,
) -> list[ChannelResult]:
    """Batch-backup all channel subdatasets in a collection.

    Args:
        collection_dir: Root collection directory
        parallel: Number of channels to process concurrently
        save: If True, run aggregate + datalad save after all backups
        push: If True, push to configured remote (requires save=True)

    Returns:
        List of per-channel ChannelResult objects
    """
    channels = discover_subdatasets(collection_dir)

    if not channels:
        print("No channel subdatasets found.")
        return []

    print(f"Backing up {len(channels)} channels in {collection_dir}...")
    print()

    results: list[ChannelResult] = []

    if parallel <= 1:
        # Sequential
        for i, ch_dir in enumerate(channels, 1):
            print(f"  [{i}/{len(channels)}] {ch_dir.name}...", end=" ", flush=True)
            result = _backup_one_channel(ch_dir)
            status = "ok" if result.success else f"FAILED: {result.message}"
            print(status)
            results.append(result)
    else:
        # Parallel
        futures = {}
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            for i, ch_dir in enumerate(channels, 1):
                fut = pool.submit(_backup_one_channel, ch_dir)
                futures[fut] = (i, ch_dir)
            for fut in as_completed(futures):
                idx, ch_dir = futures[fut]
                result = fut.result()
                status = "ok" if result.success else f"FAILED: {result.message}"
                print(f"  [{idx}/{len(channels)}] {ch_dir.name}... {status}")
                results.append(result)

    # Summary
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    print()
    print(f"Backup complete: {len(successes)}/{len(results)} channels updated successfully")
    if successes:
        for r in successes:
            print(f"  [ok] {r.name}")
    if failures:
        for r in failures:
            print(f"  [FAIL] {r.name} - {r.message}")

    # Save
    if save:
        _run(
            ["annextube", "aggregate", "--force", str(collection_dir)],
            "aggregate",
        )
        datalad_save(
            dataset=str(collection_dir),
            message="Batch update",
            recursive=True,
            result_renderer="disabled",
        )
        print("[ok] Collection saved")

    # Push
    if push:
        coll_cfg = load_collection_config(collection_dir)
        push_cmd = ["datalad", "push", "-d", str(collection_dir), "-r"]
        if coll_cfg and coll_cfg.push_remote:
            push_cmd.extend(["--to", coll_cfg.push_remote])
            remote_label = coll_cfg.push_remote
        else:
            remote_label = "default"
        _run(push_cmd, "datalad push")
        print(f"[ok] Pushed to remote: {remote_label}")

    return results


def _run(cmd: list[str], label: str) -> None:
    """Run a subprocess command, raising RuntimeError on failure.

    Args:
        cmd: Command and arguments
        label: Human-readable label for error messages

    Raises:
        RuntimeError: If the command exits with a non-zero code
    """
    logger.debug(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{label} failed (exit {result.returncode}): {stderr}")
