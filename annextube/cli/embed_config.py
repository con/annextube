"""Embed (merge) shared config into target TOML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import tomlkit

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


def merge_table(
    source_table: Any,
    target_table: Any,
    existing: str,
    *,
    path: str = "",
) -> dict[str, list[str]]:
    """Deep-merge source table into target table.

    Returns dict with 'added', 'updated', 'skipped' key lists.
    """
    result: dict[str, list[str]] = {"added": [], "updated": [], "skipped": []}
    for key in source_table:
        full_key = f"{path}.{key}" if path else key
        if key not in target_table:
            target_table[key] = source_table[key]
            result["added"].append(full_key)
        elif isinstance(source_table[key], dict) and isinstance(target_table[key], dict):
            sub = merge_table(source_table[key], target_table[key], existing, path=full_key)
            for k in result:
                result[k].extend(sub[k])
        elif existing == "update":
            target_table[key] = source_table[key]
            result["updated"].append(full_key)
        else:
            result["skipped"].append(full_key)
    return result


def merge_toml_docs(
    source: tomlkit.TOMLDocument,
    target: tomlkit.TOMLDocument,
    existing: str,
) -> dict[str, list[str]]:
    """Deep-merge source TOML document into target, skipping [[sources]]."""
    result: dict[str, list[str]] = {"added": [], "updated": [], "skipped": []}
    for key in source:
        if key == "sources":
            continue
        if key not in target:
            target[key] = source[key]
            result["added"].append(key)
        elif isinstance(source[key], dict) and isinstance(target[key], dict):
            sub = merge_table(source[key], target[key], existing, path=key)
            for k in result:
                result[k].extend(sub[k])
        elif existing == "update":
            target[key] = source[key]
            result["updated"].append(key)
        else:
            result["skipped"].append(key)
    return result


@click.command("embed-config")
@click.argument("src_config", type=click.Path(exists=True, path_type=Path))
@click.argument(
    "target_configs",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--existing",
    type=click.Choice(["keep", "update"]),
    default="keep",
    show_default=True,
    help="How to handle keys already present in target: "
    "'keep' preserves target values, 'update' overwrites with source values",
)
def embed_config(
    src_config: Path,
    target_configs: tuple[Path, ...],
    existing: str,
) -> None:
    """Embed shared config settings into target TOML files.

    Reads SRC_CONFIG and deep-merges its settings into each TARGET_CONFIG.
    Useful for propagating shared settings (e.g. [curation] glossary) from a
    super-dataset config to per-channel subdataset configs.

    The [[sources]] array-of-tables is always skipped since sources are
    per-subdataset.
    """
    source = tomlkit.parse(src_config.read_text())

    for target_path in target_configs:
        target = tomlkit.parse(target_path.read_text())
        result = merge_toml_docs(source, target, existing)
        target_path.write_text(tomlkit.dumps(target))

        # Report
        label = str(target_path)
        if result["added"]:
            click.echo(f"{label}: added {', '.join(result['added'])}")
        if result["updated"]:
            click.echo(f"{label}: updated {', '.join(result['updated'])}")
        if result["skipped"]:
            click.echo(f"{label}: kept {', '.join(result['skipped'])}")
        if not any(result.values()):
            click.echo(f"{label}: nothing to do")
