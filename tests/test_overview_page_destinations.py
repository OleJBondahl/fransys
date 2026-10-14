"""Every PDF link of the overview page opens the drawing page it names (OVERVIEW A8, O21).

The canary design is built with a cabinet document and written; the overview page is made from
the same model. Each item link `file.pdf#nameddest=label` must name a file the write produced,
and `label` a destination of that PDF that lands on the page whose title block counter `n / N`
matches the drawing page the label stands for, which is the page the link's text names.
"""

import json
import re
from collections import Counter
from typing import Any
from urllib.parse import unquote

import fransys as fr
import pypdfium2
import pytest
from fransys_overview import html
from pypdfium2 import raw
from test_page_destinations_example import _cabinet_node, _pages_of
from test_reader_order import _design

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import page_destination


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, Any, str]:
    root = tmp_path_factory.mktemp("a8page")
    design, cabinet = _design("a-")
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md")
    result = fr.build(design, doc)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    return result, root / "out", html(lay_out_overview(result.model)[0])


def _links(page: str) -> list[tuple[str, str]]:
    found = re.search(r'id="overview-data">(.*?)</script>', page, re.DOTALL)
    assert found is not None
    items = json.loads(found.group(1))["items"]
    return [(href, text) for item in items for href, text in item["pages"]]


def _landing(pdf: pypdfium2.PdfDocument, label: str) -> int | None:
    dest = raw.FPDF_GetNamedDestByName(pdf.raw, label.encode("utf-8"))
    return raw.FPDFDest_GetDestPageIndex(pdf.raw, dest) if dest else None


def test_every_link_of_the_page_lands_on_the_drawing_page_it_names(
    built: tuple[fr.BuildResult, Any, str],
) -> None:
    """A8 at page level: breaks if a label is not a destination of its PDF or lands elsewhere."""
    result, out, page = built
    pages = _pages_of(result, _cabinet_node(result))
    by_label = {page_destination(result.model, p): p for p in pages}
    totals = Counter(p.drawing_set for p in pages)
    links = _links(page)
    assert len(links) > 5
    for link, text in links:
        name, label = (unquote(part) for part in link.split("#nameddest=", 1))
        pdf = pypdfium2.PdfDocument(out / name)
        try:
            assert text.split(":")[0] == label, (link, text)
            index = _landing(pdf, label)
            assert index is not None, link
            drawn = by_label[label]
            landed = pdf[index].get_textpage().get_text_range()
            assert f"{drawn.number} / {totals[drawn.drawing_set]}" in landed, link
        finally:
            pdf.close()
