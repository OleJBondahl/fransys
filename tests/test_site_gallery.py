"""The gallery links every file under the example's `out/` (public monorepo spec PM7, acceptance 6).

Staging only, no Zensical: `site_gallery.build_gallery` on a tiny invented example folder.
"""

import importlib
import re
import sys
from pathlib import Path, PurePosixPath

import pypdfium2
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

site_gallery = importlib.import_module("site_gallery")

LINK = re.compile(r"\]\(([^)\s]+)\)")


def _two_page_pdf(path: Path) -> None:
    document = pypdfium2.PdfDocument.new()
    document.new_page(200, 100)
    document.new_page(200, 100)
    document.save(path)


@pytest.fixture
def staged(tmp_path):
    """An example folder with exports in two `out/` subfolders, staged into `src/`."""
    example = tmp_path / "demo"
    (example / "out" / "all").mkdir(parents=True)
    (example / "out" / "board").mkdir()
    (example / "README.md").write_text("# Demo\n\nA demo.\n", encoding="utf-8")
    _two_page_pdf(example / "out" / "all" / "demo.pdf")
    (example / "out" / "all" / "demo-bom.csv").write_text("mpn,count\nA|1,2\n", encoding="utf-8")
    (example / "out" / "all" / "demo-overview.html").write_text("<html></html>", encoding="utf-8")
    (example / "out" / "board" / "demo-wago-U1.xml").write_text("<x/>", encoding="utf-8")
    (example / "out" / "board" / "demo.net").write_text("(export)", encoding="utf-8")
    _two_page_pdf(example / "out" / "board" / "demo.pdf")
    src = tmp_path / "src"
    pages = site_gallery.build_gallery(example, src, tmp_path / "snippets")
    return example, src, pages


def _out_files(example: Path) -> set[str]:
    out = example / "out"
    return {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}


def _linked(src: Path, pages: list[tuple[str, str]]) -> tuple[set[str], list[str]]:
    """Out-relative paths of the files the gallery pages link, and their picture targets."""
    targets = [t for _, page in pages for t in LINK.findall((src / page).read_text("utf-8"))]
    files = {str(PurePosixPath(t).relative_to("files")) for t in targets if t.startswith("files/")}
    return files, [t for t in targets if t.startswith("img/")]


def test_gallery_links_every_file_under_out(staged):
    """The set of linked files equals the set of files under `out/`; PDFs show every page."""
    example, src, pages = staged
    files, pictures = _linked(src, pages)
    assert files == _out_files(example)
    page_dir = src / pages[0][1]
    assert all((page_dir.parent / t).is_file() for t in pictures)
    assert sorted(set(pictures)) == [
        "img/all/demo-p01.png",
        "img/all/demo-p02.png",
        "img/board/demo-p01.png",
        "img/board/demo-p02.png",
    ]
    text = page_dir.read_text("utf-8")
    assert "| A\\|1 | 2 |" in text
    assert "Open the overview page: [demo-overview.html](files/all/demo-overview.html)" in text


def test_a_planted_unlinked_file_breaks_the_equality(staged):
    """Can-fail proof: a file the staged gallery never saw makes the two sets differ."""
    example, src, pages = staged
    (example / "out" / "extra").mkdir()
    (example / "out" / "extra" / "planted.step").write_text("x", encoding="utf-8")
    files, _ = _linked(src, pages)
    assert files != _out_files(example)
    assert _out_files(example) - files == {"extra/planted.step"}
