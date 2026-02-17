"""Data models for caption curation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WordTimestamp:
    """A single word with its start and end timestamps (in seconds)."""

    word: str
    start: float
    end: float


@dataclass
class GlossaryTerm:
    """A canonical term with its ASR misrecognition patterns."""

    canonical: str  # e.g., "DataLad"
    patterns: list[str]  # e.g., ["data lad", "data glad", "datal"]
    category: str = ""
    expansion: str = ""  # For acronyms, e.g., "Brain Imaging Data Structure"


@dataclass
class Glossary:
    """Collection of glossary terms loaded from YAML files."""

    terms: list[GlossaryTerm] = field(default_factory=list)

    def merge(self, other: Glossary) -> Glossary:
        """Merge: other's terms override self's (by canonical form).

        Returns a new Glossary with merged terms.
        """
        by_canonical: dict[str, GlossaryTerm] = {}
        for term in self.terms:
            by_canonical[term.canonical] = term
        for term in other.terms:
            by_canonical[term.canonical] = term
        return Glossary(terms=list(by_canonical.values()))

    @classmethod
    def from_yaml(cls, path: Path) -> Glossary:
        """Load glossary from a YAML file.

        The YAML format has category names as top-level keys,
        each containing a list of term entries with 'term' and 'patterns'.
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            return cls()

        terms: list[GlossaryTerm] = []
        for category, entries in data.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or "term" not in entry:
                    continue
                terms.append(GlossaryTerm(
                    canonical=entry["term"],
                    patterns=entry.get("patterns", []),
                    category=category,
                    expansion=entry.get("expansion", ""),
                ))

        return cls(terms=terms)

    @classmethod
    def load_merged(cls, user_path: Path | None, archive_path: Path | None) -> Glossary:
        """Load and merge user-wide + archive glossaries.

        Archive glossary terms override user-wide terms (by canonical form).
        """
        result = cls()
        if user_path and user_path.exists():
            result = cls.from_yaml(user_path)
        if archive_path and archive_path.exists():
            archive_glossary = cls.from_yaml(archive_path)
            result = result.merge(archive_glossary)
        return result

    @classmethod
    def discover(
        cls,
        start_dir: Path,
        glossary_path: str,
        collate_parents: bool = False,
    ) -> Glossary:
        """Discover and load glossaries by searching for glossary_path.

        Parameters
        ----------
        start_dir
            Directory to start searching from.
        glossary_path
            Relative path to look for (e.g. ".annextube/captions-glossary.yaml").
        collate_parents
            If True, walk up parent directories collecting all matches.
            More-specific (closer to start_dir) terms override less-specific.
        """
        found: list[Path] = []
        current = start_dir.resolve()
        while True:
            candidate = current / glossary_path
            if candidate.is_file():
                found.append(candidate)
                if not collate_parents:
                    break
            parent = current.parent
            if parent == current:
                break
            current = parent

        if not found:
            return cls()

        # Merge from farthest (least specific) to closest (most specific)
        # so closer glossaries override farther ones.
        result = cls()
        for path in reversed(found):
            result = result.merge(cls.from_yaml(path))
        return result


@dataclass
class CurationResult:
    """Result of curating a caption file through the pipeline."""

    original_word_count: int
    curated_text: str
    segments: list[dict[str, Any]]  # [{text, start, end, words: [{word, start, end}]}]
    stage_results: list[dict[str, Any]]  # per-stage change counts
    curated_at: str  # ISO 8601
