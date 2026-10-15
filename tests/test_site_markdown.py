"""Markdown copies and the link check of the site build (DOCS-FOR-AGENTS D2, D5).

Staging only, no Zensical: `site_markdown` on a tiny invented page tree.
"""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

site_markdown = importlib.import_module("site_markdown")


@pytest.fixture
def src(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    (src / "guide").mkdir(parents=True)
    (src / "assets").mkdir()
    (src / "assets" / "a.png").write_bytes(b"png")
    (src / "index.md").write_text("# Home\n\n[guide](guide/index.md) ![a](assets/a.png)\n")
    (src / "guide" / "index.md").write_text("# Guide\n\n[the end](end.md#top)\n")
    (src / "guide" / "end.md").write_text(
        "# End\n\n[back](index.md) [home](../index.md) [web](https://x.test/y.md)\n"
        "```\n[code](nope.md)\n```\n"
    )
    return src


def test_a_relative_md_link_becomes_the_pages_index_md_copy(src: Path) -> None:
    text = site_markdown.markdown_copy(src, src, "guide/end.md")
    assert "[back](../index.md)" in text
    assert "[home](../../index.md)" in text
    assert "[web](https://x.test/y.md)" in text
    assert "[code](nope.md)" in text  # inside a fence: left alone
    assert "![a](assets/a.png)" in site_markdown.markdown_copy(src, src, "index.md")


def test_an_absolute_copy_names_the_site_url(src: Path) -> None:
    text = site_markdown.markdown_copy(src, src, "guide/index.md", "https://s.test/1.0.0/")
    assert "[the end](https://s.test/1.0.0/guide/end/index.md#top)" in text


def test_a_link_to_a_repository_path_fails_naming_it(src: Path) -> None:
    (src / "guide" / "end.md").write_text("# End\n\n[doc](../../docs/contracts/part-file.md)\n")
    with pytest.raises(site_markdown.SiteLinkError, match=r"docs/contracts/part-file\.md"):
        site_markdown.markdown_copy(src, src, "guide/end.md")


def test_a_link_to_a_missing_page_fails(src: Path) -> None:
    (src / "guide" / "end.md").write_text("# End\n\n[x](findings.md)\n")
    with pytest.raises(site_markdown.SiteLinkError, match=r"findings\.md"):
        site_markdown.markdown_copy(src, src, "guide/end.md")


def test_the_built_link_check_fails_on_a_source_md_path_and_a_dead_link(tmp_path: Path) -> None:
    """A planted `findings.md` link in a built page, and a missing page, each fail the check."""
    site = tmp_path / "site"
    (site / "guide").mkdir(parents=True)
    (site / "index.html").write_text('<a id="top"></a><a href="guide/">g</a>')
    (site / "guide" / "index.html").write_text('<a id="top"></a><a href="../index.html#top">h</a>')
    assert site_markdown.check_links(site, "") == 2
    (site / "guide" / "index.html").write_text('<a href="findings.md">x</a>')
    with pytest.raises(site_markdown.SiteLinkError, match=r"findings\.md is a source \.md path"):
        site_markdown.check_links(site, "")
    (site / "guide" / "index.html").write_text('<a href="../gone/">x</a><a href="../#nope">y</a>')
    with pytest.raises(site_markdown.SiteLinkError, match=r"gone/ does not exist"):
        site_markdown.check_links(site, "")


def test_a_findings_row_gets_its_anchor_and_the_markdown_copy_drops_it(src: Path) -> None:
    build_site = importlib.import_module("build_site")
    row = "| NET_UNREALISED | ERROR | x |\n"
    assert (
        build_site.anchor_rows(row) == '| <a id="net_unrealised"></a>NET_UNREALISED | ERROR | x |\n'
    )
    (src / "rows.md").write_text("# Rows\n\n" + build_site.anchor_rows(row))
    assert "<a id" not in site_markdown.markdown_copy(src, src, "rows.md")
