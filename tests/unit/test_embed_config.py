"""Tests for the embed-config CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
import tomlkit
from click.testing import CliRunner

from annextube.cli.embed_config import embed_config, merge_toml_docs


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_toml(tmp_path):
    """Helper to write TOML content to a temp file and return its path."""

    def _write(name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content)
        return p

    return _write


@pytest.mark.ai_generated
class TestMergeTomlDocs:
    def test_embed_new_section(self):
        source = tomlkit.parse("[curation]\nglossary = \"glossary.yaml\"\n")
        target = tomlkit.parse("[general]\ntitle = \"My Channel\"\n")
        result = merge_toml_docs(source, target, "keep")

        assert "curation" in target
        assert target["curation"]["glossary"] == "glossary.yaml"
        assert "curation" in result["added"]

    def test_embed_existing_keep(self):
        source = tomlkit.parse("[curation]\nglossary = \"new.yaml\"\ntimeout = 30\n")
        target = tomlkit.parse("[curation]\nglossary = \"old.yaml\"\n")
        result = merge_toml_docs(source, target, "keep")

        assert target["curation"]["glossary"] == "old.yaml"
        assert target["curation"]["timeout"] == 30
        assert "curation.glossary" in result["skipped"]
        assert "curation.timeout" in result["added"]

    def test_embed_existing_update(self):
        source = tomlkit.parse("[curation]\nglossary = \"new.yaml\"\n")
        target = tomlkit.parse("[curation]\nglossary = \"old.yaml\"\n")
        result = merge_toml_docs(source, target, "update")

        assert target["curation"]["glossary"] == "new.yaml"
        assert "curation.glossary" in result["updated"]

    def test_sources_skipped(self):
        source = tomlkit.parse(
            '[[sources]]\nurl = "https://youtube.com/@Test"\n\n'
            "[curation]\nglossary = \"g.yaml\"\n"
        )
        target = tomlkit.parse("[general]\ntitle = \"Target\"\n")
        result = merge_toml_docs(source, target, "keep")

        assert "sources" not in target
        assert "curation" in target
        assert "curation" in result["added"]

    def test_merge_adds_new_keys_to_existing_section(self):
        source = tomlkit.parse("[curation]\nnew_key = \"value\"\n")
        target = tomlkit.parse("[curation]\nexisting = \"kept\"\n")
        merge_toml_docs(source, target, "keep")

        assert target["curation"]["existing"] == "kept"
        assert target["curation"]["new_key"] == "value"

    def test_nested_table_merge(self):
        source = tomlkit.parse("[curation.sub]\na = 1\nb = 2\n")
        target = tomlkit.parse("[curation.sub]\na = 99\n")
        result = merge_toml_docs(source, target, "keep")

        assert target["curation"]["sub"]["a"] == 99
        assert target["curation"]["sub"]["b"] == 2
        assert "curation.sub.a" in result["skipped"]
        assert "curation.sub.b" in result["added"]


@pytest.mark.ai_generated
class TestEmbedConfigCLI:
    def test_basic_merge(self, runner, tmp_toml):
        src = tmp_toml("source.toml", "[curation]\nglossary = \"g.yaml\"\n")
        tgt = tmp_toml("target.toml", "[general]\ntitle = \"T\"\n")

        result = runner.invoke(embed_config, [str(src), str(tgt)])
        assert result.exit_code == 0
        assert "added" in result.output

        merged = tomlkit.parse(tgt.read_text())
        assert merged["curation"]["glossary"] == "g.yaml"

    def test_multiple_targets(self, runner, tmp_toml):
        src = tmp_toml("source.toml", "[curation]\nglossary = \"g.yaml\"\n")
        tgt1 = tmp_toml("target1.toml", "[general]\ntitle = \"A\"\n")
        tgt2 = tmp_toml("target2.toml", "[general]\ntitle = \"B\"\n")

        result = runner.invoke(embed_config, [str(src), str(tgt1), str(tgt2)])
        assert result.exit_code == 0

        for tgt in (tgt1, tgt2):
            merged = tomlkit.parse(tgt.read_text())
            assert merged["curation"]["glossary"] == "g.yaml"

    def test_existing_keep_flag(self, runner, tmp_toml):
        src = tmp_toml("source.toml", "[curation]\nglossary = \"new.yaml\"\n")
        tgt = tmp_toml("target.toml", "[curation]\nglossary = \"old.yaml\"\n")

        result = runner.invoke(embed_config, ["--existing", "keep", str(src), str(tgt)])
        assert result.exit_code == 0
        assert "kept" in result.output

        merged = tomlkit.parse(tgt.read_text())
        assert merged["curation"]["glossary"] == "old.yaml"

    def test_existing_update_flag(self, runner, tmp_toml):
        src = tmp_toml("source.toml", "[curation]\nglossary = \"new.yaml\"\n")
        tgt = tmp_toml("target.toml", "[curation]\nglossary = \"old.yaml\"\n")

        result = runner.invoke(embed_config, ["--existing", "update", str(src), str(tgt)])
        assert result.exit_code == 0
        assert "updated" in result.output

        merged = tomlkit.parse(tgt.read_text())
        assert merged["curation"]["glossary"] == "new.yaml"

    def test_comments_preserved(self, runner, tmp_toml):
        src = tmp_toml("source.toml", "[curation]\nglossary = \"g.yaml\"\n")
        target_content = "# Important comment\n[general]\ntitle = \"T\"  # inline\n"
        tgt = tmp_toml("target.toml", target_content)

        result = runner.invoke(embed_config, [str(src), str(tgt)])
        assert result.exit_code == 0

        output = tgt.read_text()
        assert "# Important comment" in output
        assert "# inline" in output

    def test_nothing_to_do(self, runner, tmp_toml):
        src = tmp_toml("source.toml", "[curation]\nglossary = \"g.yaml\"\n")
        tgt = tmp_toml("target.toml", "[curation]\nglossary = \"g.yaml\"\n")

        result = runner.invoke(embed_config, ["--existing", "keep", str(src), str(tgt)])
        assert result.exit_code == 0
        assert "kept" in result.output
