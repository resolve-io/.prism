"""Shape-only tests for the four v5.1 analyzer prompts.

These do not invoke claude; they verify each prompt is well-formed
(YAML frontmatter + required sections + Brain MCP refs + budget +
output_schema). Coverage protects against accidental edits that
break the engine's contract before any expensive inference runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:
    yaml = None


PROMPTS_DIR = (
    Path(__file__).resolve().parents[2] / "app" / "inference" / "prompts"
)

ANALYZERS = [
    "tour_builder",
    "architecture_analyzer",
    "domain_analyzer",
    "onboarding_writer",
]


def _read_with_frontmatter(path: Path) -> tuple[dict, str]:
    """Split a markdown-with-yaml-frontmatter doc into (meta, body)."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: missing frontmatter"
    end = text.find("\n---\n", 4)
    assert end > 0, f"{path.name}: unterminated frontmatter"
    raw_meta = text[4:end]
    body = text[end + len("\n---\n"):]
    if yaml is None:
        # Lightweight fallback parser: just grab `name:` and `output_schema:`.
        meta: dict = {}
        for ln in raw_meta.splitlines():
            if ":" in ln and not ln.startswith(" "):
                k, _, v = ln.partition(":")
                meta[k.strip()] = v.strip()
        return meta, body
    return yaml.safe_load(raw_meta) or {}, body


@pytest.mark.parametrize("analyzer", ANALYZERS)
def test_prompt_file_exists(analyzer):
    assert (PROMPTS_DIR / f"{analyzer}.md").exists()


@pytest.mark.parametrize("analyzer", ANALYZERS)
def test_prompt_has_frontmatter_name(analyzer):
    meta, _ = _read_with_frontmatter(PROMPTS_DIR / f"{analyzer}.md")
    assert meta.get("name") == analyzer


@pytest.mark.parametrize("analyzer", ANALYZERS)
def test_prompt_has_output_schema(analyzer):
    meta, _ = _read_with_frontmatter(PROMPTS_DIR / f"{analyzer}.md")
    schema = meta.get("output_schema") or ""
    assert schema.startswith(analyzer), (
        f"{analyzer}: output_schema {schema!r} doesn't start with name"
    )


@pytest.mark.parametrize("analyzer", ANALYZERS)
def test_prompt_has_budget_directive(analyzer):
    """Every analyzer must declare a token budget per T7 AC."""
    meta, body = _read_with_frontmatter(PROMPTS_DIR / f"{analyzer}.md")
    has_meta_budget = bool(meta.get("budget"))
    has_body_budget = (
        "budget" in body.lower()
        and ("token" in body.lower() or "ceiling" in body.lower())
    )
    assert has_meta_budget or has_body_budget, (
        f"{analyzer}: no budget directive found in frontmatter or body"
    )


@pytest.mark.parametrize("analyzer", ["tour_builder",
                                       "architecture_analyzer",
                                       "domain_analyzer"])
def test_ported_prompts_carry_mit_attribution(analyzer):
    meta, _ = _read_with_frontmatter(PROMPTS_DIR / f"{analyzer}.md")
    src = meta.get("source") or {}
    if isinstance(src, str):
        pytest.fail(f"{analyzer}: source must be a mapping with attribution")
    assert src.get("license") == "MIT"
    assert "Lum1104/Understand-Anything" in (src.get("upstream") or "")
    assert src.get("upstream_sha") == (
        "57a25ed4aaca8a116a6f6e011a578985c18e78c6"
    )


def test_prism_original_onboarding_writer_attribution():
    meta, _ = _read_with_frontmatter(PROMPTS_DIR / "onboarding_writer.md")
    assert meta.get("source") == "prism-original"


@pytest.mark.parametrize("analyzer", ANALYZERS)
def test_prompt_body_references_brain_mcp_tools(analyzer):
    _, body = _read_with_frontmatter(PROMPTS_DIR / f"{analyzer}.md")
    # Each prompt must mention Brain or at least one Brain MCP tool.
    body_lower = body.lower()
    assert ("brain_search" in body_lower
            or "brain_find_symbol" in body_lower
            or "brain_call_chain" in body_lower
            or "brain mcp" in body_lower), (
        f"{analyzer}: prompt body must reference Brain MCP tools"
    )
