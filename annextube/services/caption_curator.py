"""Caption curation engine - 8-stage pipeline for fixing ASR caption errors.

Ported from standalone scripts in the ReproTube project. The pipeline:
  Stage 1: Glossary regex replacement
  Stage 2: LLM corrections (from per-video JSON)
  Stage 3: Fuzzy glossary matching
  Stage 4: Filler word removal
  Stage 5: ASR artifact fixes (truncated commands)
  Stage 6: Sentence segmentation
  Stage 7: Cue chunking (balanced splits)
  Stage 8: Word-level timestamp restoration (proportional mapping)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from annextube.lib.config import CurationConfig
from annextube.models.curation import (
    CurationResult,
    Glossary,
    WordTimestamp,
)

logger = logging.getLogger(__name__)

# Patterns from glossary that are too common in English to safely auto-replace.
SKIP_PATTERNS = {
    "do", "discover", "describe", "conduct", "connects",
    "ants", "nifty", "docker", "galaxy", "gentle",
    "gin", "slurm", "elixir", "enigma", "grab",
    "hub", "globus",
}

# Common English words/roots that false-match domain glossary terms.
# Prevents fuzzy matching from incorrectly "fixing" regular English.
_FUZZY_SKIP = {
    'conduct', 'conducted', 'conducting',
    'connect', 'connected', 'connecting', 'connections', 'connector',
    'describe', 'described', 'describes', 'describing', 'description',
    'discover', 'discovered', 'discovers', 'discovering', 'discovery',
    'install', 'installed', 'installer', 'installing', 'installation',
    'preprocess', 'preprocessed', 'preprocessing',
    'process', 'processed', 'processing', 'processings',
    'principle', 'principles', 'principal',
    'reproduce', 'reproduced', 'reproducing', 'reproducible', 'reproducibility',
    'repository', 'repositories',
    'toolkit', 'toolkits',
    'version', 'versioned', 'versioning',
    'execute', 'executed', 'executing', 'executable', 'reexecute',
    'repro',  # commonly used abbreviation, not a garbled term
}


def parse_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.mmm to seconds."""
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(ts)


def seconds_to_vtt(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


class CaptionCurator:
    """8-stage caption curation engine."""

    def __init__(self, config: CurationConfig | None = None):
        self.config = config or CurationConfig()

    # ── Stage 0: VTT Parsing ──────────────────────────────────────────────

    @staticmethod
    def parse_youtube_vtt(vtt_path: Path) -> list[WordTimestamp]:
        """Parse YouTube VTT and extract word-level timestamps.

        Handles YouTube's karaoke-style <c> tags for word-level timing.
        Deduplicates words that appear in overlapping cue blocks.
        """
        with open(vtt_path) as f:
            content = f.read()

        blocks = content.split("\n\n")
        words: list[WordTimestamp] = []
        seen_text_positions: set[tuple[str, float]] = set()

        for block in blocks:
            lines = block.strip().split("\n")
            if not lines:
                continue

            ts_line = None
            text_lines: list[str] = []
            for line in lines:
                if "-->" in line:
                    ts_line = line
                elif ts_line is not None:
                    text_lines.append(line)

            if not ts_line or not text_lines:
                continue

            ts_match = re.match(r"(\d[\d:\.]+)\s*-->\s*(\d[\d:\.]+)", ts_line)
            if not ts_match:
                continue

            cue_start = parse_timestamp(ts_match.group(1))
            cue_end = parse_timestamp(ts_match.group(2))

            # Skip near-zero-duration cues (duplicate "static" lines)
            if abs(cue_end - cue_start) < 0.02:
                continue

            for text_line in text_lines:
                if not text_line.strip():
                    continue

                if "<c>" in text_line or "<00:" in text_line or "<01:" in text_line:
                    # Parse word-level timestamps from <c> tags
                    parts = re.split(r'<(\d\d:\d\d:\d\d\.\d+)><c>(.*?)</c>', text_line)

                    # First word (before any <c> tag)
                    initial_text = re.sub(r'<[^>]+>', '', parts[0]).strip()
                    if initial_text:
                        word_start = cue_start
                        word_end = parse_timestamp(parts[1]) if len(parts) > 1 else cue_end

                        key = (initial_text.lower(), round(word_start, 1))
                        if key not in seen_text_positions:
                            seen_text_positions.add(key)
                            words.append(WordTimestamp(
                                word=initial_text,
                                start=round(word_start, 3),
                                end=round(word_end, 3),
                            ))

                    # Remaining <timestamp><c> word</c> pairs
                    i = 1
                    while i < len(parts) - 2:
                        ts_str = parts[i]
                        word_text = parts[i + 1].strip()
                        next_ts = parse_timestamp(parts[i + 3]) if i + 3 < len(parts) else cue_end

                        if word_text:
                            w_start = parse_timestamp(ts_str)
                            key = (word_text.lower(), round(w_start, 1))
                            if key not in seen_text_positions:
                                seen_text_positions.add(key)
                                words.append(WordTimestamp(
                                    word=word_text,
                                    start=round(w_start, 3),
                                    end=round(next_ts, 3),
                                ))
                        i += 3

        return words

    # ── Glossary Loading ──────────────────────────────────────────────────

    @staticmethod
    def load_glossary(user_path: Path | None, archive_path: Path | None) -> Glossary:
        """Load and merge user-wide + archive glossaries."""
        return Glossary.load_merged(user_path, archive_path)

    # ── Stage 1: Glossary Regex ───────────────────────────────────────────

    @staticmethod
    def _compile_glossary_patterns(
        glossary: Glossary,
    ) -> list[tuple[re.Pattern[str], str]]:
        """Build compiled regex patterns from glossary terms."""
        replacements: list[tuple[re.Pattern[str], str]] = []
        for term in glossary.terms:
            for pat in term.patterns:
                if pat.lower() in SKIP_PATTERNS:
                    continue
                # Skip single-word patterns that are just lowercase of the term
                if (
                    pat.lower() == term.canonical.lower()
                    and len(pat.split()) == 1
                    and len(pat) <= 4
                    and not term.canonical.isupper()
                ):
                    continue
                try:
                    compiled = re.compile(r'\b' + pat + r'\b', re.IGNORECASE)
                except re.error:
                    escaped = re.escape(pat)
                    compiled = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
                replacements.append((compiled, term.canonical))
        return replacements

    @staticmethod
    def apply_glossary(
        text: str, replacements: list[tuple[re.Pattern[str], str]]
    ) -> tuple[str, list[str]]:
        """Apply glossary regex replacements to text."""
        changes: list[str] = []
        for pattern, replacement in replacements:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                for m in pattern.finditer(text):
                    if m.group() != replacement:
                        changes.append(f"'{m.group()}' -> '{replacement}'")
                text = new_text
        return text, changes

    # ── Stage 2: LLM Corrections ─────────────────────────────────────────

    @staticmethod
    def apply_corrections(
        text: str, corrections: dict[str, str]
    ) -> tuple[str, list[str]]:
        """Apply manual/LLM corrections from a {old: new} dict."""
        changes: list[str] = []
        for old, new in corrections.items():
            if old in text:
                text = text.replace(old, new)
                changes.append(f"'{old}' -> '{new}'")
        return text, changes

    # ── Stage 3: Fuzzy Matching ───────────────────────────────────────────

    @staticmethod
    def fuzzy_glossary_correct(
        text: str, glossary: Glossary, threshold: float = 0.82
    ) -> tuple[str, list[str]]:
        """Correct words that fuzzy-match glossary terms.

        Only single-word terms (no multi-word phrases). Skips common English
        words and morphological variants. Prefers terms that the word is a
        prefix of (catches ASR truncations like 'datal' -> DataLad).
        """
        term_lookup: dict[str, str] = {}
        for term in glossary.terms:
            if ' ' in term.canonical:
                continue
            norm = term.canonical.lower().replace("-", "").replace("/", "")
            if len(norm) >= 4:
                term_lookup[norm] = term.canonical

        known_norms = set(term_lookup.keys())
        text_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', text))

        changes: list[str] = []
        for word in sorted(text_words):
            word_norm = word.lower().replace("-", "")

            if word_norm in known_norms:
                continue
            if word_norm in _FUZZY_SKIP:
                continue

            # Skip morphological variants of known terms
            is_variant = False
            for norm in known_norms:
                for suffix in (
                    's', 'es', 'ed', 'ing', 'er', 'ers', 'tion', 'tions',
                    'ly', 'ity', 'ness', 'ment', 'ive', 'ous', 'able',
                ):
                    if word_norm == norm + suffix:
                        is_variant = True
                        break
                if is_variant:
                    break
            if is_variant:
                continue

            # Find fuzzy matches; prefer terms the word is a prefix of
            candidates: list[tuple[bool, float, str]] = []
            for norm_term, canonical in term_lookup.items():
                ratio = SequenceMatcher(None, word_norm, norm_term).ratio()
                if ratio >= threshold:
                    is_prefix = norm_term.startswith(word_norm)
                    candidates.append((is_prefix, ratio, canonical))

            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                best_term = candidates[0][2]
                best_ratio = candidates[0][1]
                is_prefix = candidates[0][0]

                if best_term != word:
                    pat = re.compile(r'\b' + re.escape(word) + r'\b')
                    new_text = pat.sub(best_term, text)
                    if new_text != text:
                        marker = " prefix" if is_prefix else ""
                        changes.append(
                            f"'{word}' -> '{best_term}' (fuzzy {best_ratio:.2f}{marker})"
                        )
                        text = new_text

        return text, changes

    # ── Stage 4: Filler Removal ───────────────────────────────────────────

    @staticmethod
    def remove_fillers(text: str) -> tuple[str, int]:
        """Remove filler words (uh, um, uhm, erm, ah) from text."""
        filler_pat = re.compile(
            r'\b[Uu]h+m?\b\.?'
            r'|\b[Uu]mm?\b\.?'
            r'|\b[Ee]rm\b\.?'
            r'|\b[Aa]h\b\.?',
        )
        count = len(filler_pat.findall(text))
        text = filler_pat.sub('', text)
        text = re.sub(r'  +', ' ', text)
        text = re.sub(r'\s+,', ',', text)
        text = re.sub(r'^\s+', '', text)
        return text, count

    # ── Stage 5: ASR Artifact Fixes ───────────────────────────────────────

    @staticmethod
    def fix_truncated_commands(text: str) -> tuple[str, list[str]]:
        """Fix known ASR truncation patterns like 'g submodule' -> 'git submodule'."""
        changes: list[str] = []

        git_subcmds = (
            r"submodule|submodules|clone|grep|diff|reset|add|commit|push|pull"
            r"|fetch|log|branch|status|clean|stash|cherry|merge|rebase|annex"
        )
        pat = re.compile(r'\bg (' + git_subcmds + r')\b')
        new_text = pat.sub(r'git \1', text)
        if new_text != text:
            count = len(pat.findall(text))
            changes.append(f"'g <subcmd>' -> 'git <subcmd>' ({count}x)")
            text = new_text

        for wrong, right in [("data let", "DataLad"), ("data led", "DataLad")]:
            if wrong in text.lower():
                p = re.compile(re.escape(wrong), re.IGNORECASE)
                new_text = p.sub(right, text)
                if new_text != text:
                    count = len(p.findall(text))
                    changes.append(f"'{wrong}' -> '{right}' ({count}x)")
                    text = new_text

        return text, changes

    @staticmethod
    def quote_commands(text: str) -> tuple[str, list[str]]:
        """Wrap CLI command invocations in single quotes with lowercase form."""
        changes: list[str] = []

        # Convert backtick-quoted commands to single-quoted
        text = re.sub(r'`([^`]+)`', r"'\1'", text)

        patterns: list[tuple[str, str | None]] = [
            (r"(?<!')DataLad containers-run\b(?!')", "'datalad containers-run'"),
            (r"(?<!')DataLad rerun\b(?!')", "'datalad rerun'"),
            (r"(?<!')DataLad run\b(?!')", "'datalad run'"),
            (r"(?<!')DataLad config\b(?!')", "'datalad config'"),
            (r"(?<!')git-annex (add|get|drop|copy|computed|addcomputed)\b(?!')",
             r"'git-annex \1'"),
            (r"(?<!')git submodules?\b(?!')", None),
            (r"(?<!')git cherry[- ]?pick\b(?!')", "'git cherry-pick'"),
            (r"(?<!')git grep\b(?!')", "'git grep'"),
            (r"(?<!')git clone\b(?!')", "'git clone'"),
            (r"(?<!')git diff\b(?!')", "'git diff'"),
            (r"(?<!')git reset hard\b(?!')", "'git reset --hard'"),
            (r"(?<!')git reset\b(?!')", "'git reset'"),
            (r"(?<!')git clean\b(?!')", "'git clean'"),
            (r"(?<!')codespell -w\b(?!')", "'codespell -w'"),
            (r"(?<!')codespell\b(?!')", "'codespell'"),
            (r"(?<!')dcm2niix\b(?!')", "'dcm2niix'"),
            (r"(?<!')etckeeper\b(?!')", "'etckeeper'"),
            (r"(?<!')pip install datalad\b(?!')", "'pip install datalad'"),
            (r"(?<!')pip install\b(?!')", "'pip install'"),
        ]

        for pattern, repl in patterns:
            if repl is None:
                new_text = re.sub(pattern, lambda m: f"'{m.group()}'", text)
            else:
                new_text = re.sub(pattern, repl, text)
            if new_text != text:
                count = len(re.findall(pattern, text))
                label = repl if repl else "'git submodule[s]'"
                changes.append(f"-> {label} ({count}x)")
                text = new_text

        return text, changes

    # ── Stage 6: Sentence Segmentation ────────────────────────────────────

    @staticmethod
    def segment_into_sentences(text: str) -> list[str]:
        """Split text into sentences using rule-based approach."""
        # Handle >> markers (speaker changes)
        text = re.sub(r'\s*>>\s*', ' ', text)
        text = text.replace("&gt;", "").replace("&amp;", "&")

        sentences: list[str] = []
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) > 300:
                sub_parts = re.split(
                    r'(?<=[,.])\s+(?=So\b|And\b|But\b|Now\b|Okay\b)', part
                )
                for sp in sub_parts:
                    sp = sp.strip()
                    if sp:
                        sentences.append(sp)
            else:
                sentences.append(part)

        return sentences

    # ── Stage 7: Cue Chunking ─────────────────────────────────────────────

    @staticmethod
    def chunk_sentences(
        sentences: list[str], max_words: int = 12, min_orphan: int = 3
    ) -> list[str]:
        """Split sentences longer than max_words into balanced chunks."""
        result: list[str] = []
        for sentence in sentences:
            words = sentence.split()
            n = len(words)
            if n <= max_words:
                result.append(sentence)
                continue

            n_chunks = -(-n // max_words)  # ceiling division
            base = n // n_chunks
            extra = n % n_chunks

            chunks: list[str] = []
            idx = 0
            for i in range(n_chunks):
                size = base + (1 if i < extra else 0)
                chunks.append(" ".join(words[idx:idx + size]))
                idx += size

            if len(chunks) > 1 and len(chunks[-1].split()) < min_orphan:
                last = chunks.pop()
                chunks[-1] += " " + last

            result.extend(chunks)

        return result

    # ── Stage 8: Timestamp Restoration ────────────────────────────────────

    @staticmethod
    def map_sentences_to_timestamps(
        sentences: list[str], words: list[WordTimestamp]
    ) -> list[dict[str, Any]]:
        """Map sentences back to word-level timestamps using proportional allocation."""
        total_corrected_words = sum(len(s.split()) for s in sentences)
        total_original_words = len(words)
        if total_corrected_words == 0 or total_original_words == 0:
            return []

        result: list[dict[str, Any]] = []
        float_idx = 0.0
        ratio = total_original_words / total_corrected_words

        for sentence in sentences:
            sentence_words = sentence.split()
            if not sentence_words:
                continue

            n_words = len(sentence_words)
            start_word_idx = int(float_idx)
            end_word_idx = int(float_idx + n_words * ratio)

            start_word_idx = min(start_word_idx, len(words) - 1)
            end_word_idx = min(end_word_idx, len(words) - 1)
            end_word_idx = max(end_word_idx, start_word_idx)

            result.append({
                "text": sentence,
                "start": words[start_word_idx].start,
                "end": words[end_word_idx].end,
            })

            float_idx += n_words * ratio

        return result

    @staticmethod
    def add_word_timing_proportional(segment: dict[str, Any]) -> None:
        """Add per-word timestamps using character-length proportional distribution."""
        text_words = segment["text"].split()
        if not text_words:
            segment["words"] = []
            return

        seg_start = segment["start"]
        seg_end = segment["end"]
        total_duration = seg_end - seg_start

        char_lengths = [len(w) + 1 for w in text_words]
        total_chars = sum(char_lengths)
        if total_chars == 0:
            total_chars = 1

        word_timings: list[dict[str, Any]] = []
        t = seg_start
        for i, w in enumerate(text_words):
            frac = char_lengths[i] / total_chars
            duration = total_duration * frac
            word_timings.append({
                "word": w,
                "start": round(t, 3),
                "end": round(t + duration, 3),
            })
            t += duration

        if word_timings:
            word_timings[-1]["end"] = seg_end

        segment["words"] = word_timings

    # ── Main Pipeline ─────────────────────────────────────────────────────

    def curate(
        self,
        words: list[WordTimestamp],
        glossary: Glossary,
        corrections: dict[str, str] | None = None,
    ) -> CurationResult:
        """Run the full 8-stage curation pipeline.

        Args:
            words: Word-level timestamps from VTT parsing
            glossary: Merged glossary for corrections
            corrections: Optional manual/LLM corrections dict

        Returns:
            CurationResult with curated text, segments, and stage stats
        """
        stage_results: list[dict[str, Any]] = []
        plain_text = " ".join(w.word for w in words)
        original_word_count = len(words)

        # Stage 1: Glossary regex
        replacements = self._compile_glossary_patterns(glossary)
        text, glossary_changes = self.apply_glossary(plain_text, replacements)
        stage_results.append({
            "stage": "glossary_regex",
            "changes": len(glossary_changes),
            "details": glossary_changes,
        })

        # Stage 2: LLM/manual corrections
        correction_changes: list[str] = []
        if corrections:
            text, correction_changes = self.apply_corrections(text, corrections)
        stage_results.append({
            "stage": "llm_corrections",
            "changes": len(correction_changes),
            "details": correction_changes,
        })

        # Stage 3: Fuzzy matching
        fuzzy_changes: list[str] = []
        if self.config.fuzzy_enabled:
            text, fuzzy_changes = self.fuzzy_glossary_correct(
                text, glossary, threshold=self.config.fuzzy_threshold
            )
        stage_results.append({
            "stage": "fuzzy_matching",
            "changes": len(fuzzy_changes),
            "details": fuzzy_changes,
        })

        # Stage 4: Filler removal
        filler_count = 0
        if self.config.filler_removal:
            text, filler_count = self.remove_fillers(text)
        stage_results.append({
            "stage": "filler_removal",
            "changes": filler_count,
        })

        # Stage 5: ASR artifact fixes
        text, trunc_changes = self.fix_truncated_commands(text)
        cmd_changes: list[str] = []
        if self.config.command_quoting:
            text, cmd_changes = self.quote_commands(text)
        stage_results.append({
            "stage": "asr_fixes",
            "changes": len(trunc_changes) + len(cmd_changes),
            "details": trunc_changes + cmd_changes,
        })

        # Stage 6: Sentence segmentation
        sentences = self.segment_into_sentences(text)
        stage_results.append({
            "stage": "sentence_segmentation",
            "changes": len(sentences),
        })

        # Stage 7: Cue chunking
        chunks = self.chunk_sentences(
            sentences,
            max_words=self.config.max_words_per_cue,
            min_orphan=self.config.min_orphan_words,
        )
        stage_results.append({
            "stage": "cue_chunking",
            "changes": len(chunks),
        })

        # Stage 8: Timestamp restoration
        segments = self.map_sentences_to_timestamps(chunks, words)
        for seg in segments:
            self.add_word_timing_proportional(seg)
        stage_results.append({
            "stage": "timestamp_restoration",
            "changes": len(segments),
        })

        return CurationResult(
            original_word_count=original_word_count,
            curated_text=text,
            segments=segments,
            stage_results=stage_results,
            curated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ── VTT Output ────────────────────────────────────────────────────────

    @staticmethod
    def format_word_timing_line(words: list[dict[str, Any]]) -> str:
        """Format words with YouTube's <c> tag syntax for word-level timing."""
        if not words:
            return ""
        parts = [words[0]["word"]]
        for w in words[1:]:
            ts = seconds_to_vtt(w["start"])
            parts.append(f"<{ts}><c> {w['word']}</c>")
        return "".join(parts)

    @staticmethod
    def write_curated_vtt(
        result: CurationResult, output_path: Path, word_timing: bool = True
    ) -> None:
        """Write curated segments as a WebVTT file."""
        with open(output_path, "w") as f:
            f.write("WEBVTT\n")
            f.write("Kind: captions\n")
            f.write("Language: en\n\n")

            for seg in result.segments:
                start = seconds_to_vtt(seg["start"])
                end = seconds_to_vtt(seg["end"])
                f.write(f"{start} --> {end}\n")
                if word_timing and "words" in seg:
                    f.write(f"{CaptionCurator.format_word_timing_line(seg['words'])}\n\n")
                else:
                    f.write(f"{seg['text']}\n\n")

    # ── Convenience ───────────────────────────────────────────────────────

    def curate_vtt_file(
        self,
        vtt_path: Path,
        output_path: Path,
        glossary: Glossary,
        corrections: dict[str, str] | None = None,
        word_timing: bool = True,
    ) -> CurationResult:
        """Parse, curate, and write a VTT file in one call."""
        words = self.parse_youtube_vtt(vtt_path)
        if not words:
            logger.warning(f"No words extracted from {vtt_path}")
            return CurationResult(
                original_word_count=0,
                curated_text="",
                segments=[],
                stage_results=[],
                curated_at=datetime.now(timezone.utc).isoformat(),
            )

        result = self.curate(words, glossary, corrections)
        self.write_curated_vtt(result, output_path, word_timing=word_timing)

        logger.info(
            f"Curated {vtt_path.name}: {result.original_word_count} words -> "
            f"{len(result.segments)} cues"
        )
        return result

    # ── Optional Audio Alignment ──────────────────────────────────────────

    def align_with_audio(
        self, text: str, audio_path: Path,
        method: str | None = None, model_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform forced audio alignment to get word-level timestamps.

        Requires annextube[audio-align] optional dependencies.

        Raises:
            ImportError: If alignment libraries are not installed.
            ValueError: If method is not recognized.
        """
        method = method or self.config.audio_align_method or "stable-ts"
        model_name = model_name or self.config.audio_align_model or "base"

        if method == "stable-ts":
            return self._align_stable_ts(str(audio_path), text, model_name)
        elif method == "ctc":
            return self._align_ctc(str(audio_path), text, model_name)
        else:
            raise ValueError(
                f"Unknown alignment method '{method}'. Available: stable-ts, ctc"
            )

    @staticmethod
    def _align_stable_ts(
        audio_path: str, text: str, model_name: str = "base",
    ) -> list[dict[str, Any]]:
        """Forced alignment using stable-ts (stable-whisper)."""
        import stable_whisper

        model = stable_whisper.load_model(model_name)
        result = model.align(audio_path, text, language="en")

        aligned_words: list[dict[str, Any]] = []
        for seg in result.segments:
            for w in seg.words:
                aligned_words.append({
                    "word": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                })
        return aligned_words

    @staticmethod
    def _align_ctc(
        audio_path: str, text: str, model_name: str = "base",
    ) -> list[dict[str, Any]]:
        """Forced alignment using ctc-forced-aligner."""
        import torch
        import torchaudio
        from ctc_forced_aligner import (
            generate_emissions,
            get_alignments,
            get_spans,
            load_alignment_model,
            postprocess_results,
            preprocess_text,
        )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        alignment_model, alignment_tokenizer = load_alignment_model(
            device, dtype=torch.float32
        )

        waveform, sample_rate = torchaudio.load(audio_path)
        if sample_rate != 16000:
            waveform = torchaudio.functional.resample(waveform, sample_rate, 16000)
            sample_rate = 16000
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        emissions, stride = generate_emissions(
            alignment_model, waveform.to(device), batch_size=16
        )
        tokens_starred, text_starred = preprocess_text(
            text, romanize=True, language="en"
        )
        segments, scores, blank_id = get_alignments(
            emissions, tokens_starred, alignment_tokenizer
        )
        spans = get_spans(tokens_starred, segments, blank_id)
        word_timestamps = postprocess_results(text_starred, spans, stride, sample_rate)

        aligned_words: list[dict[str, Any]] = []
        for entry in word_timestamps:
            aligned_words.append({
                "word": entry["word"],
                "start": round(entry["start"], 3),
                "end": round(entry["end"], 3),
            })
        return aligned_words


def load_corrections(path: Path) -> dict[str, str]:
    """Load corrections from a JSON file ({old: new} pairs)."""
    if not path.exists():
        return {}
    with open(path) as f:
        data: dict[str, str] = json.load(f)
    return data
