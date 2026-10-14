"""The overview's links to the PDFs (OVERVIEW O21, O27, A7).

Each link is a relative `name.pdf#nameddest=<label>` whose file name is one `export_names` gives
for the same write.
"""

import json
import re
import sys
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import fransys as fr
import fransys_parts
from fransys_overview import html
from fransys_overview._app import APP_JS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _model_build_cover import layout_trigger_document
from test_units_worked_example import _system_design

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import unit_release
from fransys_model.kernel import Origin, evolve, make_id
from fransys_model.layout import DrawingSet, layout_of
from fransys_model.vocab import Document, DocumentPreset, PageKind, documents

_RELATIVE = re.compile(r"^[^:/?#\\]+#nameddest=[^#:/]+$")


def _with_cabinet_documents(result: Any) -> Any:
    """`result` with a cabinet schematic document for each top-level set's location."""
    model = result.model
    sets = layout_of(model, DrawingSet).values()
    places = sorted({s.location for s in sets if s.unit is None and s.location})
    by_release = {unit_release(model, s.unit).name: s.unit for s in sets if s.unit is not None}
    owners = sorted(by_release.values())
    docs = [
        Document(
            id=make_id(Document, ("link-doc", str(n))),
            key=("link-doc", str(n)),
            preset=DocumentPreset.CABINET_SCHEMATIC,
            location=place,
            unit=owner,
            item=None,
            add=(),
            remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
            cover="# Cover",
            notes=None,
        )
        for n, (place, owner) in enumerate(
            [*((p, None) for p in places), *((None, u) for u in owners)]
        )
    ]
    origin = Origin(file="tests/test_overview_links.py", line=1, note="invented documents")
    kept = evolve(model, remove=tuple(documents(model)), put=docs, origin=origin)
    return replace(result, model=kept)


@cache
def _built() -> tuple[Any, str]:
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    result = _with_cabinet_documents(fr.build(parts, design.draft(), layout_trigger_document()))
    return result, html(lay_out_overview(result.model)[0])


def _items() -> list[dict[str, Any]]:
    found = re.search(r'id="overview-data">(.*?)</script>', _built()[1], re.DOTALL)
    assert found is not None
    return json.loads(found.group(1))["items"]


def _links() -> list[str]:
    return [href for item in _items() for href, _text in item["pages"]]


def test_an_item_drawn_on_a_page_links_to_it() -> None:
    """Breaks if no item carries a link: the example's cabinets draw many items."""
    assert len(_links()) > 5
    assert any(text.startswith("p") for item in _items() for _href, text in item["pages"])


def test_every_link_is_relative_and_names_a_file_the_same_write_produces() -> None:
    """A7: breaks if a link has a scheme, a `//` or a file `export_names` does not give."""
    names = set(fr.export_names(_built()[0]).values())
    assert names
    for link in _links():
        assert _RELATIVE.match(link), link
        assert unquote(link.split("#", 1)[0]) in names, link


def test_a_model_with_no_document_has_no_links() -> None:
    """O21: no document, no PDF, no link."""
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    page = html(lay_out_overview(fr.build(parts, design.draft()).model)[0])
    assert "nameddest" not in page


def test_the_script_names_no_address_of_its_own() -> None:
    """A7: the links come from the data; the script holds no file name or scheme."""
    assert "nameddest" not in APP_JS
    assert not re.search(r"https?:|\.pdf", APP_JS)
