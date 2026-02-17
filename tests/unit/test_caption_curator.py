"""Unit tests for the caption curation engine (all 8 stages)."""

from __future__ import annotations

from pathlib import Path

import pytest

from annextube.lib.config import CurationConfig
from annextube.models.curation import (
    CurationResult,
    Glossary,
    GlossaryTerm,
    WordTimestamp,
)
from annextube.services.caption_curator import (
    CaptionCurator,
    load_corrections,
    seconds_to_vtt,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ── Helper factories ──────────────────────────────────────────────────────


def _make_words(text: str, start: float = 0.0, word_dur: float = 0.3) -> list[WordTimestamp]:
    """Create WordTimestamp list from plain text with evenly spaced timing."""
    words = []
    t = start
    for w in text.split():
        words.append(WordTimestamp(word=w, start=round(t, 3), end=round(t + word_dur, 3)))
        t += word_dur
    return words


def _small_glossary() -> Glossary:
    """Return a small glossary for testing."""
    return Glossary(terms=[
        GlossaryTerm(canonical="DataLad", patterns=["data lad", "data glad"], category="projects"),
        GlossaryTerm(canonical="git-annex", patterns=["git annex", "get annex"], category="projects"),
        GlossaryTerm(canonical="fMRI", patterns=["f mri", "f m r i"], category="acronyms"),
        GlossaryTerm(canonical="BIDS", patterns=["bids"], category="acronyms"),
        GlossaryTerm(canonical="ReproNim", patterns=["repro nim", "repronim"], category="projects"),
        GlossaryTerm(canonical="NeuroDebian", patterns=["neuro debian"], category="projects"),
        GlossaryTerm(canonical="dataset", patterns=["data set"], category="technical"),
        GlossaryTerm(canonical="neuroimaging", patterns=["neuro imaging"], category="technical"),
        GlossaryTerm(canonical="subdataset", patterns=["sub dataset", "sub-dataset"], category="technical"),
    ])


# ── Stage 0: VTT Parsing ─────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestParseYoutubeVtt:
    """Test YouTube VTT parsing with karaoke-style <c> tags."""

    def test_parse_sample_karaoke_vtt(self) -> None:
        """Parse the sample karaoke VTT fixture."""
        vtt_path = FIXTURES / "sample_karaoke.vtt"
        words = CaptionCurator.parse_youtube_vtt(vtt_path)

        assert len(words) > 0
        # Check first word
        assert words[0].word == "so"
        assert words[0].start == 0.0

        # Check that all words have valid timestamps
        for w in words:
            assert w.start >= 0.0
            assert w.end >= w.start
            assert w.word.strip() != ""

    def test_deduplication(self) -> None:
        """Words appearing in overlapping cue blocks should be deduplicated."""
        vtt_path = FIXTURES / "sample_karaoke.vtt"
        words = CaptionCurator.parse_youtube_vtt(vtt_path)

        # Count occurrences of each word at each position
        seen = set()
        for w in words:
            key = (w.word.lower(), round(w.start, 1))
            assert key not in seen, f"Duplicate word found: {w.word} at {w.start}"
            seen.add(key)

    def test_empty_vtt(self, tmp_path: Path) -> None:
        """Empty VTT file returns empty word list."""
        vtt = tmp_path / "empty.vtt"
        vtt.write_text("WEBVTT\n\n")
        words = CaptionCurator.parse_youtube_vtt(vtt)
        assert words == []


# ── Glossary Loading ──────────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestGlossaryLoading:
    """Test glossary YAML loading and merging."""

    def test_load_sample_glossary(self) -> None:
        """Load the sample glossary fixture."""
        glossary = Glossary.from_yaml(FIXTURES / "sample_glossary.yaml")
        assert len(glossary.terms) > 0

        # Check that DataLad term is loaded
        datalad_terms = [t for t in glossary.terms if t.canonical == "DataLad"]
        assert len(datalad_terms) == 1
        assert "data lad" in datalad_terms[0].patterns

    def test_glossary_merge_override(self) -> None:
        """Merge should override terms by canonical form."""
        base = Glossary(terms=[
            GlossaryTerm(canonical="DataLad", patterns=["data lad"]),
            GlossaryTerm(canonical="fMRI", patterns=["f mri"]),
        ])
        override = Glossary(terms=[
            GlossaryTerm(canonical="DataLad", patterns=["data lad", "data glad"]),
        ])
        merged = base.merge(override)
        datalad = [t for t in merged.terms if t.canonical == "DataLad"][0]
        assert "data glad" in datalad.patterns
        # fMRI should still be there
        assert any(t.canonical == "fMRI" for t in merged.terms)

    def test_load_merged_missing_paths(self) -> None:
        """Load merged with non-existent paths returns empty glossary."""
        glossary = Glossary.load_merged(
            Path("/nonexistent/user.yaml"),
            Path("/nonexistent/archive.yaml"),
        )
        assert len(glossary.terms) == 0

    def test_load_merged_user_only(self) -> None:
        """Load merged with only user glossary."""
        glossary = Glossary.load_merged(
            FIXTURES / "sample_glossary.yaml",
            None,
        )
        assert len(glossary.terms) > 0


# ── Stage 1: Glossary Regex ──────────────────────────────────────────────


@pytest.mark.ai_generated
class TestGlossaryRegex:
    """Test glossary regex replacement (Stage 1)."""

    def test_basic_replacement(self) -> None:
        """'data lad' should become 'DataLad'."""
        glossary = _small_glossary()
        replacements = CaptionCurator._compile_glossary_patterns(glossary)
        text, changes = CaptionCurator.apply_glossary(
            "today we talk about data lad and git annex", replacements
        )
        assert "DataLad" in text
        assert "git-annex" in text
        assert len(changes) > 0

    def test_skip_patterns(self) -> None:
        """SKIP_PATTERNS should not be replaced."""
        # "hub" is in SKIP_PATTERNS, so a glossary term with pattern "hub"
        # should not trigger replacement
        glossary = Glossary(terms=[
            GlossaryTerm(canonical="HUB", patterns=["hub"]),
        ])
        replacements = CaptionCurator._compile_glossary_patterns(glossary)
        text, changes = CaptionCurator.apply_glossary(
            "the github hub is great", replacements
        )
        assert changes == []

    def test_case_insensitive(self) -> None:
        """Glossary matches should be case-insensitive."""
        glossary = _small_glossary()
        replacements = CaptionCurator._compile_glossary_patterns(glossary)
        text, _ = CaptionCurator.apply_glossary("Data Lad is great", replacements)
        assert "DataLad" in text

    def test_multi_word_pattern(self) -> None:
        """Multi-word patterns like 'f mri' should work."""
        glossary = _small_glossary()
        replacements = CaptionCurator._compile_glossary_patterns(glossary)
        text, _ = CaptionCurator.apply_glossary("the f mri data is in bids format", replacements)
        assert "fMRI" in text


# ── Stage 2: LLM Corrections ─────────────────────────────────────────────


@pytest.mark.ai_generated
class TestLLMCorrections:
    """Test LLM/manual correction application (Stage 2)."""

    def test_apply_corrections(self) -> None:
        """Corrections should replace matching text."""
        text, changes = CaptionCurator.apply_corrections(
            "the yarn stall command works",
            {"yarn stall": "install"},
        )
        assert "install" in text
        assert len(changes) == 1

    def test_no_match(self) -> None:
        """No changes when corrections don't match."""
        text, changes = CaptionCurator.apply_corrections(
            "hello world",
            {"nonexistent": "replacement"},
        )
        assert text == "hello world"
        assert changes == []


# ── Stage 3: Fuzzy Matching ──────────────────────────────────────────────


@pytest.mark.ai_generated
class TestFuzzyMatching:
    """Test fuzzy glossary matching (Stage 3)."""

    def test_prefix_match(self) -> None:
        """ASR truncations like 'datal' should match 'DataLad'."""
        glossary = _small_glossary()
        text, changes = CaptionCurator.fuzzy_glossary_correct(
            "the datal tool is useful", glossary, threshold=0.82
        )
        assert "DataLad" in text
        assert len(changes) > 0

    def test_skip_common_english(self) -> None:
        """Common English words in _FUZZY_SKIP should not be matched."""
        glossary = _small_glossary()
        text, changes = CaptionCurator.fuzzy_glossary_correct(
            "describe the process of version control", glossary
        )
        # None of these common words should be "corrected"
        assert "describe" in text
        assert "process" in text
        assert "version" in text

    def test_skip_morphological_variants(self) -> None:
        """Plurals/conjugations of known terms should be skipped."""
        glossary = Glossary(terms=[
            GlossaryTerm(canonical="BIDS", patterns=["bids"]),
        ])
        text, changes = CaptionCurator.fuzzy_glossary_correct(
            "the BIDSs format is great", glossary
        )
        # "BIDSs" is a variant of BIDS (BIDS + s), should be skipped
        assert changes == []

    def test_exact_match_skipped(self) -> None:
        """Exact matches of known terms should not be modified."""
        glossary = _small_glossary()
        text, changes = CaptionCurator.fuzzy_glossary_correct(
            "DataLad is a great tool", glossary
        )
        assert text == "DataLad is a great tool"
        assert changes == []

    def test_short_words_ignored(self) -> None:
        """Words shorter than 4 characters should be ignored."""
        glossary = _small_glossary()
        text, changes = CaptionCurator.fuzzy_glossary_correct(
            "use the git tool", glossary
        )
        # "git" is only 3 chars, should not trigger fuzzy match
        assert changes == []


# ── Stage 4: Filler Removal ──────────────────────────────────────────────


@pytest.mark.ai_generated
class TestFillerRemoval:
    """Test filler word removal (Stage 4)."""

    def test_remove_uh_um(self) -> None:
        """Standard fillers (uh, um) should be removed."""
        text, count = CaptionCurator.remove_fillers("so uh we can um use this tool")
        assert "uh" not in text
        assert "um" not in text
        assert count == 2

    def test_remove_variants(self) -> None:
        """Filler variants (uhm, erm, ah) should be removed."""
        text, count = CaptionCurator.remove_fillers("uhm the erm data ah looks good")
        assert count == 3
        assert "uhm" not in text
        assert "erm" not in text

    def test_no_double_spaces(self) -> None:
        """Filler removal should not leave double spaces."""
        text, _ = CaptionCurator.remove_fillers("hello uh world")
        assert "  " not in text

    def test_no_fillers(self) -> None:
        """Text without fillers should be unchanged."""
        text, count = CaptionCurator.remove_fillers("hello world")
        assert text == "hello world"
        assert count == 0


# ── Stage 5: ASR Artifact Fixes ──────────────────────────────────────────


@pytest.mark.ai_generated
class TestASRArtifactFixes:
    """Test ASR truncation and artifact fixes (Stage 5)."""

    def test_g_to_git(self) -> None:
        """'g clone' should become 'git clone'."""
        text, changes = CaptionCurator.fix_truncated_commands(
            "you run g clone to get the repo"
        )
        assert "git clone" in text
        assert len(changes) > 0

    def test_g_submodule(self) -> None:
        """'g submodule' should become 'git submodule'."""
        text, _ = CaptionCurator.fix_truncated_commands("g submodule init")
        assert "git submodule" in text

    def test_data_let_to_datalad(self) -> None:
        """'data let' should become 'DataLad'."""
        text, _ = CaptionCurator.fix_truncated_commands("use data let for versioning")
        assert "DataLad" in text

    def test_command_quoting(self) -> None:
        """CLI commands should be quoted."""
        text, changes = CaptionCurator.quote_commands(
            "run DataLad run to execute"
        )
        assert "'datalad run'" in text

    def test_git_annex_quoting(self) -> None:
        """git-annex commands should be quoted."""
        text, _ = CaptionCurator.quote_commands("use git-annex get to download")
        assert "'git-annex get'" in text

    def test_no_double_quoting(self) -> None:
        """Already-quoted commands should not be re-quoted."""
        text, changes = CaptionCurator.quote_commands(
            "run 'datalad run' to execute"
        )
        # Should not add extra quotes
        assert text.count("'datalad run'") == 1


# ── Stage 6: Sentence Segmentation ───────────────────────────────────────


@pytest.mark.ai_generated
class TestSentenceSegmentation:
    """Test sentence segmentation (Stage 6)."""

    def test_basic_segmentation(self) -> None:
        """Sentences should split on period + capital letter."""
        sentences = CaptionCurator.segment_into_sentences(
            "This is one. And this is two."
        )
        assert len(sentences) == 2

    def test_speaker_markers(self) -> None:
        """>> markers should be treated as sentence boundaries."""
        sentences = CaptionCurator.segment_into_sentences(
            "hello >> welcome to the talk"
        )
        assert len(sentences) >= 1
        assert ">>" not in sentences[0]

    def test_long_segment_split(self) -> None:
        """Very long segments (>300 chars) should be split at natural breaks."""
        long_text = "This is a very long sentence. " * 15 + "So we should split here."
        sentences = CaptionCurator.segment_into_sentences(long_text)
        assert len(sentences) >= 2


# ── Stage 7: Cue Chunking ────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestCueChunking:
    """Test sentence chunking (Stage 7)."""

    def test_short_sentence_unchanged(self) -> None:
        """Sentences <= max_words should not be split."""
        result = CaptionCurator.chunk_sentences(["hello world"], max_words=12)
        assert result == ["hello world"]

    def test_long_sentence_split(self) -> None:
        """Long sentences should be split into balanced chunks."""
        long = " ".join(["word"] * 24)
        result = CaptionCurator.chunk_sentences([long], max_words=12)
        assert len(result) == 2
        for chunk in result:
            assert len(chunk.split()) == 12

    def test_orphan_merge(self) -> None:
        """Last chunk with < min_orphan words should be merged."""
        # 13 words: would split to 12 + 1, but orphan merge gives 13
        text = " ".join(["word"] * 13)
        result = CaptionCurator.chunk_sentences([text], max_words=12, min_orphan=3)
        # With balanced chunking: 13 words, 2 chunks -> 7+6 or similar
        for chunk in result:
            assert len(chunk.split()) >= 3

    def test_multiple_sentences(self) -> None:
        """Multiple sentences should each be chunked independently."""
        sentences = ["short one", " ".join(["word"] * 24)]
        result = CaptionCurator.chunk_sentences(sentences, max_words=12)
        assert len(result) >= 3  # 1 short + 2 long chunks


# ── Stage 8: Timestamp Restoration ────────────────────────────────────────


@pytest.mark.ai_generated
class TestTimestampRestoration:
    """Test proportional timestamp mapping (Stage 8)."""

    def test_proportional_mapping(self) -> None:
        """Timestamps should be proportionally distributed."""
        words = _make_words("one two three four five six", start=0.0, word_dur=1.0)
        sentences = ["one two three", "four five six"]
        segments = CaptionCurator.map_sentences_to_timestamps(sentences, words)

        assert len(segments) == 2
        assert segments[0]["start"] == 0.0
        assert segments[1]["end"] == words[-1].end

    def test_empty_inputs(self) -> None:
        """Empty inputs should return empty results."""
        assert CaptionCurator.map_sentences_to_timestamps([], []) == []
        assert CaptionCurator.map_sentences_to_timestamps(["hello"], []) == []

    def test_word_timing_proportional(self) -> None:
        """Word-level timing should be character-proportional."""
        segment = {"text": "hi world", "start": 0.0, "end": 1.0}
        CaptionCurator.add_word_timing_proportional(segment)

        assert "words" in segment
        assert len(segment["words"]) == 2
        assert segment["words"][0]["start"] == 0.0
        assert segment["words"][-1]["end"] == 1.0

        # "world" is longer than "hi", so it should get more time
        hi_dur = segment["words"][0]["end"] - segment["words"][0]["start"]
        world_dur = segment["words"][1]["end"] - segment["words"][1]["start"]
        assert world_dur > hi_dur


# ── Full Pipeline ─────────────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestFullPipeline:
    """Test the complete curation pipeline end-to-end."""

    def test_curate_basic(self) -> None:
        """Full pipeline should produce a valid CurationResult."""
        words = _make_words(
            "so uh today we talk about data lad and git annex for f mri data",
            start=0.0, word_dur=0.4,
        )
        glossary = _small_glossary()
        config = CurationConfig()
        curator = CaptionCurator(config)

        result = curator.curate(words, glossary)

        assert isinstance(result, CurationResult)
        assert result.original_word_count == len(words)
        assert result.curated_text != ""
        assert len(result.segments) > 0
        assert len(result.stage_results) == 8
        assert result.curated_at != ""

        # Check that glossary corrections were applied
        assert "DataLad" in result.curated_text
        assert "git-annex" in result.curated_text
        assert "fMRI" in result.curated_text

        # Check that fillers were removed
        assert " uh " not in result.curated_text

    def test_curate_with_corrections(self) -> None:
        """Pipeline should apply manual corrections."""
        words = _make_words("the yarn stall command works", word_dur=0.4)
        glossary = Glossary()
        config = CurationConfig()
        curator = CaptionCurator(config)

        result = curator.curate(words, glossary, corrections={"yarn stall": "install"})
        assert "install" in result.curated_text

    def test_curate_vtt_file(self, tmp_path: Path) -> None:
        """curate_vtt_file should parse, curate, and write."""
        vtt_path = FIXTURES / "sample_karaoke.vtt"
        output_path = tmp_path / "curated.vtt"
        glossary = Glossary.from_yaml(FIXTURES / "sample_glossary.yaml")
        config = CurationConfig()
        curator = CaptionCurator(config)

        result = curator.curate_vtt_file(vtt_path, output_path, glossary)

        assert result.original_word_count > 0
        assert output_path.exists()

        # Verify output is valid VTT
        content = output_path.read_text()
        assert content.startswith("WEBVTT")
        assert "-->" in content

    def test_curate_vtt_no_word_timing(self, tmp_path: Path) -> None:
        """curate_vtt_file with word_timing=False should write plain text cues."""
        vtt_path = FIXTURES / "sample_karaoke.vtt"
        output_path = tmp_path / "curated.vtt"
        glossary = Glossary.from_yaml(FIXTURES / "sample_glossary.yaml")
        config = CurationConfig()
        curator = CaptionCurator(config)

        curator.curate_vtt_file(
            vtt_path, output_path, glossary, word_timing=False
        )
        content = output_path.read_text()
        assert "<c>" not in content

    def test_curate_empty_vtt(self, tmp_path: Path) -> None:
        """Curating an empty VTT should return empty result without error."""
        vtt = tmp_path / "empty.vtt"
        vtt.write_text("WEBVTT\n\n")
        output = tmp_path / "out.vtt"
        config = CurationConfig()
        curator = CaptionCurator(config)

        result = curator.curate_vtt_file(vtt, output, Glossary())
        assert result.original_word_count == 0


# ── VTT Output ────────────────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestVTTOutput:
    """Test VTT file output formatting."""

    def test_seconds_to_vtt(self) -> None:
        """seconds_to_vtt should produce correct HH:MM:SS.mmm format."""
        assert seconds_to_vtt(0.0) == "00:00:00.000"
        assert seconds_to_vtt(61.5) == "00:01:01.500"
        assert seconds_to_vtt(3661.123) == "01:01:01.123"

    def test_format_word_timing_line(self) -> None:
        """Word timing should produce <c> tag format."""
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
        ]
        line = CaptionCurator.format_word_timing_line(words)
        assert line.startswith("hello")
        assert "<c> world</c>" in line

    def test_write_curated_vtt(self, tmp_path: Path) -> None:
        """write_curated_vtt should produce valid VTT with word timing."""
        result = CurationResult(
            original_word_count=4,
            curated_text="hello world foo bar",
            segments=[{
                "text": "hello world",
                "start": 0.0,
                "end": 1.0,
                "words": [
                    {"word": "hello", "start": 0.0, "end": 0.5},
                    {"word": "world", "start": 0.5, "end": 1.0},
                ],
            }, {
                "text": "foo bar",
                "start": 1.0,
                "end": 2.0,
                "words": [
                    {"word": "foo", "start": 1.0, "end": 1.5},
                    {"word": "bar", "start": 1.5, "end": 2.0},
                ],
            }],
            stage_results=[],
            curated_at="2026-02-16T00:00:00Z",
        )
        output = tmp_path / "test.vtt"
        CaptionCurator.write_curated_vtt(result, output)

        content = output.read_text()
        assert content.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:01.000" in content
        assert "<c> world</c>" in content


# ── Corrections Loading ───────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestLoadCorrections:
    """Test loading corrections from JSON files."""

    def test_load_existing(self, tmp_path: Path) -> None:
        """Load corrections from a valid JSON file."""
        path = tmp_path / "corrections.json"
        path.write_text('{"old text": "new text"}')
        corrections = load_corrections(path)
        assert corrections == {"old text": "new text"}

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        """Loading from non-existent path returns empty dict."""
        corrections = load_corrections(tmp_path / "nope.json")
        assert corrections == {}
