"""Render's own acceptance list (spec, "Test data and acceptance"), against the real golden.

Reads the layout package's golden laid-out cabinets through `conftest.py`'s
`cabinet_laid_out`/`cabinet_narrow_laid_out` fixtures (JSON loaded with the model's own
`loads`); this file never imports `fransys_layout` (spec section 5). The spec's own four
acceptance items for render are here, each its own test: every page of both goldens renders
and its SVG parses as XML; every TAG designation, marker text and wire label of a page
appears in that page's SVG; two calls give equal bytes; a model loaded from shuffled JSON
gives equal bytes.

`test_pin_map_not_covering_symbol_ports_is_a_finding`, the stub this file used to carry, is
gone: `PIN_MAP_INCOMPLETE` left render's own `check()` for `fransys_layout`'s `resolve`
stage (decision layout-0041, D12's amendment) -- render's `check()` has no such code left to
test.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
from fransys_render import pages

from fransys_model.derive.drawing_text import label_text, marker_text
from fransys_model.kernel import loads
from fransys_model.kernel.ids import render_id
from fransys_model.layout import Label, LabelKind, LinkMarker, Page, layout_of

pytestmark = pytest.mark.wp("render")

# Render's own resolution of the layout golden directory, mirroring `conftest.py`'s
# `_GOLDEN_DIR`: the shuffled-JSON check (test 4) needs the raw text `loads()` reads a
# golden from, not just the already-loaded `Model` the fixtures hand back.
_GOLDEN_DIR = (
    next(
        p
        for p in Path(__file__).resolve().parents
        if (p / "fransys-layout" / "tests" / "golden").is_dir()
    )
    / "fransys-layout"
    / "tests"
    / "golden"
)

# Page counts, known independently of `pages()` (`conftest.py`'s own docstrings: the wide
# cabinet's 2 pages, the narrow cabinet's 5).
_EXPECTED_PAGE_COUNTS = {"cabinet_laid_out": 2, "cabinet_narrow_laid_out": 5}


def _goldens(cabinet_laid_out, cabinet_narrow_laid_out):
    return {
        "cabinet_laid_out": cabinet_laid_out,
        "cabinet_narrow_laid_out": cabinet_narrow_laid_out,
    }


# --- 1. every page renders; each SVG parses as XML (page count independent of `pages()`) -------


def test_every_golden_page_renders_and_parses_as_xml(cabinet_laid_out, cabinet_narrow_laid_out):
    for name, model in _goldens(cabinet_laid_out, cabinet_narrow_laid_out).items():
        expected_count = _EXPECTED_PAGE_COUNTS[name]
        assert expected_count > 0
        assert len(layout_of(model, Page)) == expected_count

        svgs = pages(model)
        assert len(svgs) == expected_count
        for svg in svgs.values():
            ET.fromstring(svg)  # noqa: S314 -- parsing our own generated SVG, not untrusted input


# --- 2. every TAG designation, marker text and wire label of a page appears in its SVG ----------


def _expected_texts(model, page):
    """Every TAG/WIRE label text and marker text of `page`, escaped as render itself escapes them.

    Built independently of `pages()`, straight from the records (`layout.label`,
    `layout.link_marker`) and the shared D2 readers render's own `_labels.py`/`_markers.py`
    call -- the same pattern `tests/test_symbol_geometry.py` and `tests/test_labels.py` use
    for their own hand-computed expectations.
    """
    texts = [
        escape(label_text(model, label))
        for label in layout_of(model, Label).values()
        if label.page == page.id and label.kind in (LabelKind.TAG, LabelKind.WIRE)
    ]
    texts.extend(
        escape(marker_text(model, marker))
        for marker in layout_of(model, LinkMarker).values()
        if marker.page == page.id
    )
    return texts


def test_every_tag_marker_and_wire_text_appears_on_its_page(
    cabinet_laid_out, cabinet_narrow_laid_out
):
    """Each expected text appears line by line: `_markers.py::_text_element` (decision
    layout-0089) draws one `<text>` element per line of a multi-line marker (LD3 (d), symmetric,
    no more `LINE`-packing), never one element holding an embedded newline, so the joined,
    multi-line block `_expected_texts` builds can never appear as one substring past one line.
    """
    for model in _goldens(cabinet_laid_out, cabinet_narrow_laid_out).values():
        svgs = pages(model)
        for page in layout_of(model, Page).values():
            expected = _expected_texts(model, page)
            assert len(expected) > 0
            svg = svgs[render_id(page.id)]
            for text in expected:
                for line in text.split("\n"):
                    assert line in svg


# --- 3. two calls give equal bytes (D11: the same model digest gives the same bytes) ------------


def test_two_calls_give_equal_bytes(cabinet_laid_out, cabinet_narrow_laid_out):
    for model in _goldens(cabinet_laid_out, cabinet_narrow_laid_out).values():
        assert pages(model) == pages(model)


# --- 4. a model loaded from shuffled JSON gives equal bytes (D11) -------------------------------


def _shuffled(name):
    """`name`'s golden JSON with every table's record order reversed, then reloaded.

    Mirrors `fransys_model`'s own canonical-order proof
    (`packages/fransys-model/tests/kernel/test_decode.py::
    test_loading_does_not_depend_on_the_order_of_keys_or_records_in_the_text`, which
    reverses one table's record list with plain `json` and re-`loads`s it) and the layout
    engine's own stage-input shuffle
    (`packages/fransys-layout/tests/usecases/test_usecases.py`): every table's record
    list, reversed, is the established "does this depend on order" probe in this codebase.
    """
    raw = json.loads((_GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))
    for records in raw["tables"].values():
        records.reverse()
    return loads(json.dumps(raw))


def test_shuffled_json_gives_equal_bytes(cabinet_laid_out, cabinet_narrow_laid_out):
    for name, model in _goldens(cabinet_laid_out, cabinet_narrow_laid_out).items():
        assert pages(_shuffled(name)) == pages(model)
