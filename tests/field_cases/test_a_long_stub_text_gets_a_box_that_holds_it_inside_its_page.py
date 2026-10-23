"""Field case: a stub whose text is longer than the plain flag gets a box that holds it, in-page.

Engineering shape: one relay coil net fans out to thirty-eight other coils, so each end's marker
names the cell of its first place and counts the rest (`#1-2B +4`).

The bug class: the flag was reserved at the plain 48 G box whatever it printed, so a long text
stood outside its flag, past the page edge or on a neighbour.
The rule: the box a stub is written with is fitted to its text (symdef's `fitted_marker_views`),
the core reserves that box, and the box lies inside the content of its page (R318, R329).

The decision that fixes it: layout-0374 (R318, R329).
"""

from typing import cast

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from electrical_symbols import LIBRARY, MARKER_FACING, MARKER_SLOT
from fransys_layout.symbols import fitted_marker_views, library_symbol
from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, Page, layout_of, sheet_format_of
lazy from fransys_layout.core import Orientation

_PLAIN = 48


def _side(one: LinkMarker) -> str:
    """The side a stub's box sits out from its port; a stub always stores one."""
    assert one.facing is not None
    return one.facing.name


def _box(one: LinkMarker) -> tuple[float, float, float, float]:
    """The record's box: the tip at (x, y), the long extent along the facing, the cross centred."""
    along = one.height if _side(one) in ("N", "S") else one.width
    cross = one.width if _side(one) in ("N", "S") else one.height
    lo, hi = {"E": (0, along), "S": (0, along), "W": (-along, 0), "N": (-along, 0)}[_side(one)]
    if _side(one) in ("N", "S"):
        return one.x - cross // 2, one.y + lo, one.x + cross - cross // 2, one.y + hi
    return one.x + lo, one.y - cross // 2, one.x + hi, one.y + cross - cross // 2


def _fan_out() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Marker", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        coils = [d.device(f"K{n}", "DEMO-RLY-2CO-24").coil["A2"] for n in range(1, 40)]
    for end in coils[1:]:
        d.detail.wire(coils[0], end, wire=(BU, 0.5))
    return fr.build(d, cabinet_document(cabinet))


def _stubs(built: fr.BuildResult) -> list[LinkMarker]:
    return list(layout_of(built.model, LinkMarker).values())


def test_a_stub_box_holds_its_text_and_stands_inside_its_page() -> None:
    built = _fan_out()
    pages = layout_of(built.model, Page)
    symbol = library_symbol(LIBRARY, "reference-marker")
    stubs = _stubs(built)
    assert stubs
    for one in stubs:
        need = fitted_marker_views(symbol, MARKER_SLOT, marker_text(built.model, one), LIBRARY)
        wanted = need[cast("Orientation", MARKER_FACING[_side(one)])]
        along = one.height if _side(one) in ("N", "S") else one.width
        assert along >= (wanted.h if _side(one) in ("N", "S") else wanted.w), one.key
        sheet = sheet_format_of(built.model, pages[one.page].sheet_format)
        g = float(sheet.module_mm) / 8
        x0, y0, x1, y1 = _box(one)
        assert x0 >= 0, (one.key, x0)
        assert x1 <= sheet.content_width_mm / g, (one.key, x1)
        assert y0 >= 0, (one.key, y0)
        assert y1 <= sheet.content_height_mm / g, (one.key, y1)


def test_some_stub_text_outgrows_the_plain_flag() -> None:
    """The case is not vacuous: at least one stub is wider than the plain box."""
    assert any(max(m.width, m.height) > _PLAIN for m in _stubs(_fan_out()))
