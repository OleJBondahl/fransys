"""Render's SVG pages fit the sheet exactly; every drawn coordinate lies in the content box.

Spec acceptance (render work order, PART 5): on the demo cabinet document, for every
schematic page, the SVG's `width`/`height`/`viewBox` equal the sheet `resolve_sheet_format`
gives PDF, and every coordinate the SVG draws lies inside that sheet's content box. Root
tests are the one place `fransys_render` and `fransys_pdf` may both be imported (spec
section 5's boundary table holds neither to import the other; mirrors
`tests/test_marker_text_compiles_inside_box.py` and
`tests/test_symbol_not_installed_compiles_grey.py`'s cross-package pattern).
`resolve_sheet_format` and `schematic_pages` are not in
`fransys_pdf`'s `__all__`, so they are imported from their own private modules directly,
the same way that package's own `tests/test_source.py` and `tests/test_determinism.py`
already import `_geometry` -- there is no public equivalent to reach for instead.
"""

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import fransys as fr
import fransys_author
import fransys_parts
import fransys_render
from demo_designs import cabinet_design
from fransys_pdf import document_pages
from fransys_pdf._drawings import schematic_pages
from fransys_pdf._geometry import resolve_sheet_format

from fransys_model.kernel.ids import render_id
from fransys_model.vocab import documents

if TYPE_CHECKING:
    from pathlib import Path

_SVG_NS = "{http://www.w3.org/2000/svg}"

# At least one schematic page, and at least one drawn coordinate, must exist before either
# is checked (root CLAUDE.md: every loop over records asserts a non-zero count first).
_MIN_PAGE_COUNT = 1
_MIN_COORDINATE_COUNT = 1

# Every direct child `_render_page` can put on a page (D11's fixed content-group order):
# `<style>` carries no coordinate, the rest are checked by `_element_coordinates`. An
# unrecognised top-level tag is a real gap in this test, not something to skip quietly.
_KNOWN_TOP_TAGS = frozenset({"style", "g", "rect", "text", "polyline", "circle", "line"})

# Inside a `<g class="symbol">` wrapper, the toolkit's own fragment tags
# (`graphical_symbols.svg._element`/`to_fragment`): `line`, `polygon`/`polyline`, `circle`,
# `text` carry a simple local x/y pair; `path` (an SVG arc, `_arc`) does not -- its `d`
# mixes coordinate and flag numbers in path-command syntax, not a plain point list, and is
# a known gap here (see `_symbol_fragment_coordinates`'s docstring). Bare `g` is the
# toolkit's own non-transformed style wrapper, carrying no coordinate of its own.
_FRAGMENT_POINT_TAGS = frozenset({"line", "polygon", "polyline", "circle", "text"})
_FRAGMENT_IGNORED_TAGS = frozenset({"g", "path"})


def _built_document_model(tmp_path: Path):
    """A cabinet document with real laid-out `SCHEMATIC` pages (mirrors `demo_cabinet_document`)."""
    parts = fransys_parts.load("demo_parts")
    design = cabinet_design(parts)
    c1 = fransys_author.Design(parts).location("C1", "Demo cabinet")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    result = fr.build(parts, design.draft(), document_draft)
    return result.model


def _mm_attr(value: str) -> float:
    """`"420mm"` -> `420.0`: the SVG root's own `width`/`height` (D5), no other unit ever used."""
    assert value.endswith("mm"), value
    return float(value[: -len("mm")])


def _tag(element: ET.Element) -> str:
    return element.tag.removeprefix(_SVG_NS)


def _point(x_text: str, y_text: str) -> tuple[float, float]:
    return (float(x_text), float(y_text))


def _fragment_local_points(element: ET.Element) -> tuple[tuple[float, float], ...]:
    """One toolkit fragment element's own local (pre-transform) x/y pair(s)."""
    tag = _tag(element)
    attrib = element.attrib
    if tag == "line":
        return (_point(attrib["x1"], attrib["y1"]), _point(attrib["x2"], attrib["y2"]))
    if tag == "circle":
        return (_point(attrib["cx"], attrib["cy"]),)
    if tag in ("polygon", "polyline"):
        points = attrib.get("points", "").split()
        return tuple(_point(*point.split(",")) for point in points)
    if tag == "text":
        return (_point(attrib["x"], attrib["y"]),)
    return ()


def _symbol_fragment_coordinates(g_element: ET.Element) -> tuple[tuple[float, float], ...]:
    """A `<g class="symbol"...>` wrapper's real drawn coordinates, in absolute page mm.

    `_symbols.py`'s `_symbol_fragment`: `transform="translate(tx,ty) scale(s)"` on the outer
    `<g>`, wrapping the toolkit's own fragment elements in the symbol's local, unscaled
    coordinate space. SVG's `transform` composes right-to-left onto a point, so the true
    absolute page point of a local `(lx, ly)` is `(tx + s*lx, ty + s*ly)` -- exactly
    `_symbol_fragment`'s own docstring formula. Every descendant's own local point(s) are
    read via `_fragment_local_points` and mapped through that formula; `path` (an SVG arc)
    is skipped, a known gap (module docstring).

    Raises:
        AssertionError: a descendant tag is neither a known point tag nor a known ignored
            one -- an unrecognised toolkit output shape, not something to skip quietly.
    """
    transform = g_element.attrib.get("transform", "")
    match = re.match(r"translate\(([^,]+),([^)]+)\)\s*scale\(([^)]+)\)", transform)
    if match is None:
        return ()
    tx, ty, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
    coords: list[tuple[float, float]] = []
    for element in g_element.iter():
        if element is g_element:
            continue
        tag = _tag(element)
        assert tag in _FRAGMENT_POINT_TAGS or tag in _FRAGMENT_IGNORED_TAGS, (
            g_element.attrib.get("class"),
            tag,
            "unrecognised symbol-fragment tag",
        )
        for lx, ly in _fragment_local_points(element):
            coords.append((tx + s * lx, ty + s * ly))
    return tuple(coords)


def _element_coordinates(  # noqa: PLR0911 -- one branch per SVG tag `_render_page` can emit
    element: ET.Element,
) -> tuple[tuple[float, float], ...]:
    """Every x/y-shaped coordinate `element` itself draws, including a symbol's real body.

    `.attrib[...]` (not `.get(...)`) throughout except where a default is meaningful:
    every attribute checked here is one `_render_page`'s own glyph functions always write
    for that tag, so a missing attribute is a real bug to raise on, not a `None` to
    silently thread through `float()`.
    """
    tag = _tag(element)
    attrib = element.attrib
    if tag == "circle":
        return (_point(attrib["cx"], attrib["cy"]),)
    if tag == "line":
        return (_point(attrib["x1"], attrib["y1"]), _point(attrib["x2"], attrib["y2"]))
    if tag == "rect":
        x, y = float(attrib["x"]), float(attrib["y"])
        w, h = float(attrib["width"]), float(attrib["height"])
        return ((x, y), (x + w, y), (x, y + h), (x + w, y + h))
    if tag == "text":
        return (_point(attrib["x"], attrib["y"]),)
    if tag == "polyline":
        points = attrib.get("points", "").split()
        return tuple(_point(*point.split(",")) for point in points)
    if tag == "g":
        return _symbol_fragment_coordinates(element)
    return ()


def _all_coordinates(root: ET.Element) -> tuple[tuple[float, float], ...]:
    """Every coordinate of every page-level element -- direct children of `<svg>` only.

    Not `root.iter()`: a `<g class="symbol">` wrapper's own descendants are handled by
    `_symbol_fragment_coordinates` instead, which transforms each one from the fragment's
    local, unscaled coordinate space into absolute page mm before returning it -- recursing
    here too would double-count them as untransformed, absolute-looking numbers, a parsing
    bug, not a real off-page coordinate. Every other content group (routes, junctions,
    markers, labels, the placeholder rect+text) is flat, one level deep, so plain direct
    children cover them correctly. Every direct child's own tag must be recognised
    (`_KNOWN_TOP_TAGS`): a future content group emitting an unhandled tag must fail loud,
    not silently draw zero checked coordinates.
    """
    coords: list[tuple[float, float]] = []
    for element in root:
        tag = _tag(element)
        assert tag in _KNOWN_TOP_TAGS, (tag, "unrecognised top-level SVG tag")
        coords.extend(_element_coordinates(element))
    return tuple(coords)


def test_render_pages_fit_the_sheet_and_every_coordinate_lies_in_the_content_box(tmp_path):
    model = _built_document_model(tmp_path)
    (document_id,) = documents(model)
    record = documents(model)[document_id]
    pages = document_pages(model, document_id)
    sheet = resolve_sheet_format(model, record, pages)
    svgs = fransys_render.pages(model)

    schematic = schematic_pages(model, record, pages)
    assert len(schematic) >= _MIN_PAGE_COUNT, "no real schematic page to check"

    page_data = [
        (page, ET.fromstring(svgs[render_id(page.id)]))  # noqa: S314 -- render's own trusted output
        for page in schematic
    ]
    page_coords = [(page, root, _all_coordinates(root)) for page, root in page_data]
    total_coordinates = sum(len(coords) for _page, _root, coords in page_coords)
    assert total_coordinates >= _MIN_COORDINATE_COUNT, "no coordinate drawn to check"

    content_x0 = float(sheet.content_x_mm)
    content_y0 = float(sheet.content_y_mm)
    content_x1 = content_x0 + float(sheet.content_width_mm)
    content_y1 = content_y0 + float(sheet.content_height_mm)

    for page, root, coords in page_coords:
        key = render_id(page.id)
        assert _mm_attr(root.attrib["width"]) == float(sheet.width_mm), key
        assert _mm_attr(root.attrib["height"]) == float(sheet.height_mm), key
        assert root.attrib["viewBox"] == f"0 0 {sheet.width_mm} {sheet.height_mm}", key
        for x, y in coords:
            assert content_x0 <= x <= content_x1, (key, x, y, "x outside content box")
            assert content_y0 <= y <= content_y1, (key, x, y, "y outside content box")
