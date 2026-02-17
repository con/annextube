"""LLM-assisted correction generation for caption curation.

Supports Ollama, OpenAI, and Anthropic providers via simple HTTP calls.
No heavy SDK dependencies -- uses httpx for HTTP.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# System prompt for LLM correction generation
_SYSTEM_PROMPT = """\
You are a transcript correction assistant. You will receive an auto-generated \
caption transcript that has already been partially corrected using a glossary \
of domain-specific terms. Your job is to identify REMAINING errors that the \
glossary did not catch.

Focus on:
1. Domain terms that were mangled by speech recognition but not in the glossary
2. Proper nouns (people, institutions, software) that were misspelled
3. Technical terms that were split or merged incorrectly
4. Context-dependent corrections (e.g., "g" should be "git" before a subcommand)

Output a JSON object mapping old text fragments to corrected text.
Use enough context in the key to avoid false positives (e.g., use \
"g is about version" not just "g").

Example output:
{
  "yarn stall": "install",
  "the dee bug tool": "the debug tool"
}

If no corrections are needed, output an empty object: {}
"""


class LLMCorrectionGenerator:
    """Generate correction proposals via LLM (Ollama/OpenAI/Anthropic)."""

    def __init__(
        self,
        provider: str,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or self._get_api_key(provider)

    @staticmethod
    def _get_api_key(provider: str) -> str | None:
        """Get API key from environment variables."""
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        var = env_vars.get(provider)
        return os.environ.get(var) if var else None

    def generate_corrections(
        self, text: str, glossary_terms: list[str]
    ) -> dict[str, str]:
        """Send glossary-corrected text to LLM, get {old: new} proposals.

        Args:
            text: The glossary-corrected transcript text
            glossary_terms: List of canonical term names for context

        Returns:
            Dictionary of {old_fragment: corrected_text} corrections
        """
        import httpx

        terms_str = ", ".join(glossary_terms[:100])  # Limit to avoid prompt overflow
        user_prompt = (
            f"Domain terms already corrected: {terms_str}\n\n"
            f"Transcript to review:\n{text[:8000]}"  # Limit text length
        )

        try:
            if self.provider == "ollama":
                return self._call_ollama(user_prompt)
            elif self.provider == "openai":
                return self._call_openai(user_prompt)
            elif self.provider == "anthropic":
                return self._call_anthropic(user_prompt)
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
        except httpx.HTTPError as e:
            logger.error(f"LLM API call failed: {e}")
            return {}
        except Exception as e:
            logger.error(f"LLM correction generation failed: {e}")
            return {}

    def _call_ollama(self, user_prompt: str) -> dict[str, str]:
        """Call Ollama API."""
        import httpx

        base_url = self.base_url or "http://localhost:11434"
        response = httpx.post(
            f"{base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "format": "json",
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        return self._parse_json_response(content)

    def _call_openai(self, user_prompt: str) -> dict[str, str]:
        """Call OpenAI-compatible API."""
        import httpx

        base_url = self.base_url or "https://api.openai.com/v1"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return self._parse_json_response(content)

    def _call_anthropic(self, user_prompt: str) -> dict[str, str]:
        """Call Anthropic API."""
        import httpx

        base_url = self.base_url or "https://api.anthropic.com"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        response = httpx.post(
            f"{base_url}/v1/messages",
            headers=headers,
            json={
                "model": self.model,
                "max_tokens": 4096,
                "system": _SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json()["content"][0]["text"]
        return self._parse_json_response(content)

    @staticmethod
    def _parse_json_response(content: str) -> dict[str, str]:
        """Parse JSON response from LLM, extracting {old: new} corrections."""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                # Validate all keys and values are strings
                return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            match = re.search(r'```(?:json)?\s*(\{[^`]+\})\s*```', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, dict):
                        return {str(k): str(v) for k, v in data.items()}
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse LLM response as JSON: {content[:200]}")
        return {}

    def save_corrections(self, corrections: dict[str, str], path: Path) -> None:
        """Save corrections to per-video llm_corrections.json for human review."""
        with open(path, "w") as f:
            json.dump(corrections, f, indent=2)
        logger.info(f"Saved {len(corrections)} LLM corrections to {path}")


def load_corrections(path: Path) -> dict[str, str]:
    """Load approved corrections from llm_corrections.json."""
    if not path.exists():
        return {}
    with open(path) as f:
        data: Any = json.load(f)
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    return {}
