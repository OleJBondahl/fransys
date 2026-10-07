"""CG6: `just site` writes `llms.txt`, one line per guide page in nav order (llmstxt.org form)."""

import importlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

build_site = importlib.import_module("build_site")

SITE_URL = "https://example.test/fransys/"


@pytest.fixture
def staged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    monkeypatch.setattr(build_site, "SRC", tmp_path / "site-src")
    build_site.SRC.mkdir()
    return build_site.stage_guide()


def test_llms_txt_names_every_guide_page_once_in_nav_order(
    staged: list[tuple[str, str]],
) -> None:
    text = build_site.llms_txt(staged, SITE_URL)
    links = re.findall(r"^- \[[^\]]+\]\(([^)]+)\)", text, re.MULTILINE)
    names = [n if n != "index" else "" for n in (*build_site.guide_pages(), "AGENTS")]
    expected = [f"{SITE_URL}guide/{n}/" if n else f"{SITE_URL}guide/" for n in names]
    assert links == expected
    assert text.startswith("# Fransys\n\n> ")


def test_each_line_carries_the_pages_opening_paragraph(staged: list[tuple[str, str]]) -> None:
    lines = build_site.llms_txt(staged, SITE_URL).splitlines()
    for _title, page in staged:
        paragraph = build_site.opening_paragraph(build_site.SRC / page)
        assert paragraph
        assert sum(line.endswith(f": {paragraph}") for line in lines) == 1
