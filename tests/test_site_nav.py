"""The staged site nav lists Roadmap right after Examples and before API (public monorepo spec)."""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

build_site = importlib.import_module("build_site")

API = [("Overview", "api/index.md")]


def _top_titles() -> list[str]:
    lines = build_site._nav_lines(build_site.nav_sections([], [], API))
    return [ln[4:].split(":")[0].strip('"') for ln in lines if ln.startswith("  - ")]


def test_roadmap_follows_examples_in_the_nav():
    """Nav order: Home, Guide, Part files, Examples, Roadmap, API; Roadmap is a page entry."""
    assert _top_titles() == ["Home", "Guide", "Part files", "Examples", "Roadmap", "API"]
    lines = build_site._nav_lines(build_site.nav_sections([], [], API))
    assert '  - "Roadmap": roadmap.md' in lines


def test_roadmap_source_page_exists_and_opens_with_its_title():
    """The page the staging step copies exists and starts with `# Roadmap`."""
    text = (ROOT / "website" / "roadmap.md").read_text(encoding="utf-8")
    assert text.startswith("# Roadmap\n")
