"""Curate-captions command for annextube."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

from annextube.lib.logging_config import get_logger

if TYPE_CHECKING:
    from annextube.lib.config import CurationConfig
    from annextube.models.curation import Glossary

logger = get_logger(__name__)


@click.command("curate-captions")
@click.argument(
    "video_path",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Archive directory (default: current directory)",
)
@click.option(
    "--video-id",
    multiple=True,
    help="Specific video ID(s) to curate (repeatable)",
)
@click.option(
    "-l", "--language",
    default=None,
    help="Caption language to curate (default: all auto-generated)",
)
@click.option(
    "--all", "curate_all",
    is_flag=True,
    help="Curate all videos in archive",
)
@click.option(
    "--glossary",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Additional glossary YAML to merge",
)
@click.option(
    "--corrections",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to corrections JSON file",
)
@click.option(
    "--generate-corrections",
    is_flag=True,
    help="Generate LLM correction proposals",
)
@click.option(
    "--audio",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Audio file for forced alignment",
)
@click.option(
    "--align-method",
    type=click.Choice(["stable-ts", "ctc"]),
    default=None,
    help="Alignment backend",
)
@click.option(
    "--align-model",
    default=None,
    help="Whisper model name for alignment",
)
@click.option(
    "--no-word-timing",
    is_flag=True,
    help="Plain text output (no <c> tags)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show changes without writing files",
)
@click.pass_context
def curate_captions(
    ctx: click.Context,
    video_path: Path | None,
    output_dir: Path | None,
    video_id: tuple[str, ...],
    language: str | None,
    curate_all: bool,
    glossary: Path | None,
    corrections: Path | None,
    generate_corrections: bool,
    audio: Path | None,
    align_method: str | None,
    align_model: str | None,
    no_word_timing: bool,
    dry_run: bool,
) -> None:
    """Curate auto-generated captions using glossary-based corrections.

    Applies an 8-stage pipeline to fix ASR errors in YouTube auto-generated
    captions: glossary regex, LLM corrections, fuzzy matching, filler removal,
    ASR artifact fixes, sentence segmentation, cue chunking, and timestamp
    restoration.

    \b
    Examples:
      annextube curate-captions /path/to/video/dir
      annextube curate-captions --all -o ~/my-archive
      annextube curate-captions --video-id dQw4w9WgXcQ \\
        --glossary my-terms.yaml
    """
    from annextube.lib.config import load_config, load_user_config
    from annextube.services.caption_curator import CaptionCurator, load_corrections

    # Direct video directory mode
    if video_path is not None:
        _curate_video_dir(
            ctx, video_path, glossary, corrections, generate_corrections,
            language, no_word_timing, dry_run,
        )
        return

    if output_dir is None:
        output_dir = Path.cwd()

    if not video_id and not curate_all:
        raise click.UsageError(
            "Specify VIDEO_PATH, --video-id, or --all"
        )

    # Load config
    config_path = ctx.obj.get("config_path")
    try:
        config = load_config(config_path, output_dir)
    except FileNotFoundError:
        # No archive config -- use defaults
        from annextube.lib.config import Config
        config = Config()
        config.user = load_user_config()

    curation_config = config.curation

    merged_glossary = _load_glossary(
        ctx, curation_config, output_dir, glossary,
        user_glossary_path_str=config.user.glossary_path,
    )

    # Load corrections
    corrections_dict: dict[str, str] = {}
    if corrections:
        corrections_dict = load_corrections(corrections)
        click.echo(f"Loaded {len(corrections_dict)} corrections from {corrections}")

    # Find VTT files to curate
    videos_dir = output_dir / "videos"
    if not videos_dir.exists():
        click.echo(f"No videos directory found at {videos_dir}", err=True)
        ctx.exit(1)

    vtt_files: list[tuple[Path, Path]] = []  # (input_vtt, output_vtt)

    if curate_all:
        for vtt_path in videos_dir.rglob("*.vtt"):
            if _should_curate_vtt(vtt_path, language, curation_config.curated_suffix):
                out = _curated_output_path(vtt_path, curation_config.curated_suffix)
                vtt_files.append((vtt_path, out))
    else:
        for vid in video_id:
            # Find video directory by ID
            for metadata_path in videos_dir.rglob("metadata.json"):
                try:
                    with open(metadata_path) as f:
                        meta = json.load(f)
                    if meta.get("video_id") == vid:
                        video_dir = metadata_path.parent
                        for vtt_path in video_dir.glob("*.vtt"):
                            if _should_curate_vtt(
                                vtt_path, language, curation_config.curated_suffix
                            ):
                                out = _curated_output_path(
                                    vtt_path, curation_config.curated_suffix
                                )
                                vtt_files.append((vtt_path, out))
                        break
                except (json.JSONDecodeError, OSError):
                    continue

    if not vtt_files:
        click.echo("No VTT files found to curate")
        return

    click.echo(f"Found {len(vtt_files)} VTT file(s) to curate")

    # Initialize curator
    curator = CaptionCurator(curation_config)

    # Process each file
    total_changes = 0
    for vtt_path, out_path in vtt_files:
        click.echo(f"\nProcessing: {vtt_path.relative_to(output_dir)}")

        # Load per-video corrections if they exist
        per_video_corrections = dict(corrections_dict)
        llm_corr_path = vtt_path.parent / "llm_corrections.json"
        if llm_corr_path.exists():
            per_video = load_corrections(llm_corr_path)
            per_video_corrections.update(per_video)

        words = curator.parse_youtube_vtt(vtt_path)
        if not words:
            click.echo("  No words extracted, skipping")
            continue

        result = curator.curate(words, merged_glossary, per_video_corrections)

        # Report changes
        for stage in result.stage_results:
            if stage["changes"]:
                click.echo(f"  {stage['stage']}: {stage['changes']} changes")
                total_changes += stage["changes"]

        if dry_run:
            click.echo(f"  [dry-run] Would write: {out_path.relative_to(output_dir)}")
        else:
            curator.write_curated_vtt(
                result, out_path, word_timing=not no_word_timing
            )
            click.echo(f"  Wrote: {out_path.relative_to(output_dir)}")

        # Generate LLM corrections if requested
        if generate_corrections and not dry_run:
            try:
                from annextube.services.llm_corrector import LLMCorrectionGenerator

                if not curation_config.llm_provider or not curation_config.llm_model:
                    click.echo(
                        "  LLM provider/model not configured in [curation] config",
                        err=True,
                    )
                else:
                    generator = LLMCorrectionGenerator(
                        provider=curation_config.llm_provider,
                        model=curation_config.llm_model,
                        base_url=curation_config.llm_base_url,
                    )
                    terms = [t.canonical for t in merged_glossary.terms]
                    llm_corrections = generator.generate_corrections(
                        result.curated_text, terms
                    )
                    if llm_corrections:
                        generator.save_corrections(
                            llm_corrections, vtt_path.parent / "llm_corrections.json"
                        )
                        click.echo(
                            f"  Generated {len(llm_corrections)} LLM correction proposals"
                        )
            except ImportError:
                click.echo("  httpx not installed, skipping LLM corrections", err=True)

    click.echo(f"\nDone: {len(vtt_files)} file(s), {total_changes} total changes")


def _load_glossary(
    ctx: click.Context,
    curation_config: CurationConfig,
    start_dir: Path,
    glossary_extra: Path | None,
    user_glossary_path_str: str | None = None,
) -> Glossary:
    """Load glossary using configured discovery, with CLI extra merged on top.

    Glossary sources (merged in order, later overrides earlier):
    1. User-wide glossary (from UserConfig.glossary_path)
    2. Discovered via CurationConfig.glossary_path (+collate_parents)
    3. CLI --glossary extra
    """
    from annextube.models.curation import Glossary

    merged = Glossary()

    # 1. User-wide glossary
    if user_glossary_path_str:
        user_path = Path(user_glossary_path_str).expanduser()
        if user_path.exists():
            merged = Glossary.from_yaml(user_path)

    # 2. Discover via glossary_path config
    if curation_config.glossary_path:
        discovered = Glossary.discover(
            start_dir,
            curation_config.glossary_path,
            collate_parents=curation_config.glossary_collate_parents,
        )
        merged = merged.merge(discovered)

    # 3. CLI --glossary extra
    if glossary_extra:
        extra = Glossary.from_yaml(glossary_extra)
        merged = merged.merge(extra)

    if not merged.terms:
        if curation_config.glossary_path:
            click.echo(
                f"No glossary found at '{curation_config.glossary_path}' "
                f"(searched from {start_dir}"
                f"{', including parents' if curation_config.glossary_collate_parents else ''}). "
                f"Provide one with --glossary or configure [curation] glossary_path",
                err=True,
            )
        else:
            click.echo(
                "No glossary configured. Set glossary_path in [curation] config "
                "or provide one with --glossary",
                err=True,
            )
        ctx.exit(1)

    click.echo(f"Loaded {len(merged.terms)} glossary terms")
    return merged


def _should_curate_vtt(
    vtt_path: Path, language: str | None, curated_suffix: str
) -> bool:
    """Check if a VTT file should be curated.

    Skips already-curated files and filters by language if specified.
    """
    name = vtt_path.stem
    # Skip already-curated files
    if f"-{curated_suffix}" in name:
        return False
    # Filter by language if specified
    if language:
        # VTT files are named like video.en.vtt
        parts = name.split(".")
        if len(parts) >= 2:
            lang = parts[-1]
            if lang != language:
                return False
    return True


def _curated_output_path(vtt_path: Path, curated_suffix: str) -> Path:
    """Generate the curated output path for a VTT file.

    video.en.vtt -> video.en-curated.vtt
    """
    name = vtt_path.stem  # e.g., "video.en"
    return vtt_path.parent / f"{name}-{curated_suffix}.vtt"


def _curate_video_dir(
    ctx: click.Context,
    video_dir: Path,
    glossary_extra: Path | None,
    corrections: Path | None,
    generate_corrections: bool,
    language: str | None,
    no_word_timing: bool,
    dry_run: bool,
) -> None:
    """Curate VTT files in a standalone video directory."""
    from annextube.lib.config import CurationConfig, load_user_config
    from annextube.services.caption_curator import CaptionCurator, load_corrections

    user_config = load_user_config()
    curation_config = CurationConfig()

    merged_glossary = _load_glossary(
        ctx, curation_config, video_dir, glossary_extra,
        user_glossary_path_str=user_config.glossary_path,
    )

    # Load corrections
    corrections_dict: dict[str, str] = {}
    if corrections:
        corrections_dict = load_corrections(corrections)
        click.echo(f"Loaded {len(corrections_dict)} corrections from {corrections}")

    # Find VTT files
    vtt_files: list[tuple[Path, Path]] = []
    for vtt_path in video_dir.glob("*.vtt"):
        if _should_curate_vtt(vtt_path, language, curation_config.curated_suffix):
            out = _curated_output_path(vtt_path, curation_config.curated_suffix)
            vtt_files.append((vtt_path, out))

    if not vtt_files:
        click.echo("No VTT files found to curate")
        return

    click.echo(f"Found {len(vtt_files)} VTT file(s) to curate")

    curator = CaptionCurator(curation_config)

    total_changes = 0
    for vtt_path, out_path in vtt_files:
        click.echo(f"\nProcessing: {vtt_path.name}")

        # Load per-video corrections
        per_video_corrections = dict(corrections_dict)
        llm_corr_path = video_dir / "llm_corrections.json"
        if llm_corr_path.exists():
            per_video = load_corrections(llm_corr_path)
            per_video_corrections.update(per_video)

        words = curator.parse_youtube_vtt(vtt_path)
        if not words:
            click.echo("  No words extracted, skipping")
            continue

        result = curator.curate(words, merged_glossary, per_video_corrections)

        for stage in result.stage_results:
            if stage["changes"]:
                click.echo(f"  {stage['stage']}: {stage['changes']} changes")
                total_changes += stage["changes"]

        if dry_run:
            click.echo(f"  [dry-run] Would write: {out_path.name}")
        else:
            curator.write_curated_vtt(
                result, out_path, word_timing=not no_word_timing
            )
            click.echo(f"  Wrote: {out_path.name}")

        if generate_corrections and not dry_run:
            try:
                from annextube.services.llm_corrector import LLMCorrectionGenerator

                if not curation_config.llm_provider or not curation_config.llm_model:
                    click.echo(
                        "  LLM provider/model not configured in [curation] config",
                        err=True,
                    )
                else:
                    generator = LLMCorrectionGenerator(
                        provider=curation_config.llm_provider,
                        model=curation_config.llm_model,
                        base_url=curation_config.llm_base_url,
                    )
                    terms = [t.canonical for t in merged_glossary.terms]
                    llm_corrections = generator.generate_corrections(
                        result.curated_text, terms
                    )
                    if llm_corrections:
                        generator.save_corrections(
                            llm_corrections, video_dir / "llm_corrections.json"
                        )
                        click.echo(
                            f"  Generated {len(llm_corrections)} LLM correction proposals"
                        )
            except ImportError:
                click.echo(
                    "  httpx not installed, skipping LLM corrections", err=True
                )

    click.echo(f"\nDone: {len(vtt_files)} file(s), {total_changes} total changes")
