"""Render's SVG pages fit the sheet exactly; every drawn coordinate lies in the content box.

On the demo cabinet document, for every
schematic page, the SVG's `width`/`height`/`viewBox` equal the sheet `resolve_sheet_format`
"""

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import fransys as fr
import fransys_parts
from demo_designs import cabinet_design
from fransys_author.design import Design
from fransys_pdf._drawings import schematic_pages

from fransys_model.derive import document_page_kinds, document_row, documents
from fransys_model.derive import document_sheet_format as resolve_sheet_format
from fransys_model.kernel import render_id

if TYPE_CHECKING:
    from pathlib import Path

_SVG_NS = "{http://www.w3.org/2000/svg}"

# At least one schematic page, and at least one drawn coordinate, must exist before either
# is checked (root CLAUDE.md: every loop over records asserts a non-zero count first).
_MIN_PAGE_COUNT = 1
_MIN_COORDINATE_COUNT = 1


def _built_document(tmp_path: Path):
    """A cabinet document with real laid-out `SCHEMATIC` pages (mirrors `demo_cabinet_document`)."""
    parts = fransys_parts.load("demo_parts")
    design = cabinet_design(parts)
    c1 = Design(parts).location("C1", "Demo cabinet")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    return fr.build(parts, design.draft(), document_draft)


def _mm_attr(value: str) -> float:
    """`"420mm"` -> `420.0`: the SVG root's own `width`/`height` (D5), no other unit ever used."""
    assert value.endswith("mm"), value
    return float(value[: -len("mm")])


def _tag(element: ET.Element) -> str:
    return element.tag.removeprefix(_SVG_NS)


_TRANSLATE = re.compile(r"translate\(([-\d.]+)[ ,]+([-\d.]+)\)(?:\s*scale\(([-\d.]+)\))?")
_POINTS = {
    "line": (("x1", "y1"), ("x2", "y2")),
    "circle": (("cx", "cy"),),
    "text": (("x", "y"),),
}
_LISTED = frozenset({"polygon", "polyline"})


def _all_coordinates(element: ET.Element, tx: float = 0.0, ty: float = 0.0, scale: float = 1.0) -> tuple[tuple[float, float], ...]:
    """Every point `element` and its descendants draw, in page mm, through each `translate`.

    An unrecognised tag or transform fails loud, so a new shape never draws zero checked points.
    """
    tag = _tag(element)
    attrib = element.attrib
    if "transform" in attrib:
        match = _TRANSLATE.fullmatch(attrib["transform"])
        assert match, (tag, attrib["transform"], "unrecognised transform")
        tx, ty = tx + scale * float(match[1]), ty + scale * float(match[2])
        scale *= float(match[3] or 1)
    if tag in {"svg", "g"}:
        return tuple(p for child in element for p in _all_coordinates(child, tx, ty, scale))
    assert tag in _POINTS or tag in _LISTED, (tag, "unrecognised SVG tag")
    if tag in _LISTED:
        pairs = [tuple(map(float, point.split(","))) for point in attrib["points"].split()]
    else:
        pairs = [(float(attrib[x]), float(attrib[y])) for x, y in _POINTS[tag]]
    return tuple((tx + scale * x, ty + scale * y) for x, y in pairs)


def _core_pages(tmp_path: Path):
    """The sheet and each schematic page's `(page, SVG root)`, drawn on the core."""
    built = _built_document(tmp_path)
    model = built.model
    (document_id,) = documents(model)
    record = document_row(model, document_id)
    pages = document_page_kinds(model, document_id)
    sheet = resolve_sheet_format(model, record.id, pages)
    svgs = built.page_svgs
    schematic = schematic_pages(model, record, pages)
    assert len(schematic) >= _MIN_PAGE_COUNT, "no real schematic page to check"
    return sheet, [(page, ET.fromstring(svgs[render_id(page)])) for page in schematic]  # noqa: S314


def test_render_pages_fit_the_sheet(tmp_path):
    sheet, page_data = _core_pages(tmp_path)
    for page, root in page_data:
        key = render_id(page)
        assert _mm_attr(root.attrib["width"]) == float(sheet.width_mm), key
        assert _mm_attr(root.attrib["height"]) == float(sheet.height_mm), key
        assert root.attrib["viewBox"] == f"0 0 {sheet.width_mm} {sheet.height_mm}", key


def test_every_coordinate_lies_in_the_content_box(tmp_path):
    sheet, page_data = _core_pages(tmp_path)
    page_coords = [(page, root, _all_coordinates(root)) for page, root in page_data]
    total_coordinates = sum(len(coords) for _page, _root, coords in page_coords)
    assert total_coordinates >= _MIN_COORDINATE_COUNT, "no coordinate drawn to check"

    content_x0 = float(sheet.content_x_mm)
    content_y0 = float(sheet.content_y_mm)
    content_x1 = content_x0 + float(sheet.content_width_mm)
    content_y1 = content_y0 + float(sheet.content_height_mm)

    for page, _root, coords in page_coords:
        key = render_id(page)
        for x, y in coords:
            assert content_x0 <= x <= content_x1, (key, x, y, "x outside content box")
            assert content_y0 <= y <= content_y1, (key, x, y, "y outside content box")
