"""Every PDF link of the overview page opens the drawing page it names (OVERVIEW A8, O21).

The canary design is built with a cabinet document and written; the overview page is made from
the same model. Each item link `file.pdf#nameddest=label` must name a file the write produced,
"""

import json
import re
from typing import Any
from urllib.parse import unquote

import fransys as fr
import pypdfium2
import pytest
from fransys_overview import html
from test_page_destinations_example import _cabinet_node, _canary, _landing, _pages_of

from electrical_symbols import LIBRARY
from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import page_destination, pdf_page


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, Any, str]:
    root = tmp_path_factory.mktemp("a8page")
    design, documents = _canary(root)
    result = fr.build(design, *documents)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    return result, root / "out", html(lay_out_overview(result.model, LIBRARY)[0], text_height=8)


def _links(page: str) -> list[tuple[str, str]]:
    found = re.search(r'id="overview-data">(.*?)</script>', page, re.DOTALL)
    assert found is not None
    items = json.loads(found.group(1))["items"]
    return [(href, text) for item in items for href, text in item["pages"]]


def test_every_link_of_the_page_lands_on_the_drawing_page_it_names(
    built: tuple[fr.BuildResult, Any, str],
) -> None:
    """A8 at page level: breaks if a label is not a destination of its PDF or lands elsewhere."""
    result, out, page = built
    pages = _pages_of(result, _cabinet_node(result))
    by_label = {page_destination(result.model, p): p for p in pages}
    links = [(link, text) for link, text in _links(page) if "-C1.pdf#" in link]  # the labels repeat in each document's PDF
    assert len(links) > 5
    for link, text in links:
        name, label = (unquote(part) for part in link.split("#nameddest=", 1))
        pdf = pypdfium2.PdfDocument(out / name)
        try:
            assert text.split(":")[0] == label, (link, text)
            index = _landing(pdf, label)
            assert index is not None, link
            drawn = by_label[label]
            assert index == pdf_page(result.model, drawn) - 1, link
        finally:
            pdf.close()
