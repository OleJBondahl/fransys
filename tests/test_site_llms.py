"""`just site` writes `llms.txt`: the version on line 1, one line per page in nav order (D3)."""

import importlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

build_site = importlib.import_module("build_site")

SITE_URL = "https://example.test/fransys/9.9.9/"


@pytest.fixture
def staged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    monkeypatch.setattr(build_site, "SRC", tmp_path / "site-src")
    build_site.SRC.mkdir()
    return build_site.stage_guide()


def test_llms_txt_names_every_guide_page_once_in_nav_order(
    staged: list[tuple[str, str]],
) -> None:
    text = build_site.llms_txt([("Guide", staged)], SITE_URL, "9.9.9")
    links = re.findall(r"^- \[[^\]]+\]\(([^)]+)\)", text, re.MULTILINE)
    names = [n if n != "index" else "" for n in (*build_site.guide_pages(), "AGENTS")]
    expected = [
        f"{SITE_URL}guide/{n}/index.md" if n else f"{SITE_URL}guide/index.md" for n in names
    ]
    assert links == expected
    assert text.startswith("# Fransys 9.9.9\n\n> ")


def test_each_line_carries_the_pages_opening_paragraph(staged: list[tuple[str, str]]) -> None:
    lines = build_site.llms_txt([("Guide", staged)], SITE_URL, "9.9.9").splitlines()
    for _title, page in staged:
        paragraph = build_site.plain(build_site.opening_paragraph(build_site.SRC / page))
        assert paragraph
        assert sum(line.endswith(f": {paragraph}") for line in lines) == 1


def test_a_summary_line_holds_no_markdown_link(staged: list[tuple[str, str]]) -> None:
    """`findings.md` links in an opening paragraph are dead on the site: `plain` drops them."""
    text = build_site.llms_txt([("Guide", staged)], SITE_URL, "9.9.9")
    assert not re.search(r"\]\([^)]*\.md\)[^:]", text.replace(SITE_URL, ""))
    assert build_site.plain("see [`findings.md`](findings.md) now") == "see `findings.md` now"


def test_the_staged_site_pages_drop_the_offline_banner(staged: list[tuple[str, str]]) -> None:
    """The banner says "read this copy only offline": on the site itself it would be wrong."""
    for _title, page in staged:
        assert "Offline copy" not in (build_site.SRC / page).read_text(encoding="utf-8")
