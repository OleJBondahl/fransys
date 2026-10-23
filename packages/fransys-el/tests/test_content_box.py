"""CONTENT-BOX (layout-0334): everything the core draws or routes stands inside the content box.

The rules are layout-0031 (three lanes free above row 0), layout-0035 (one lane free below the
last row) and layout-0068 (nothing past the content box). The values are typed here on purpose:
they are the rule, and a probe that drops the headroom from the options must fail this test.
The cases are the study instances w04 and p02, the unit outline, the drawn supply and the pilot.
"""

import pytest
from content_box_cases import CASES, solved, solved_in

from fransys_layout.core import Box, CoreLayout, Size

LANE = 8
TOP = 3 * LANE
BOTTOM = 1 * LANE


def _outside(layout: CoreLayout) -> list[str]:
    """Every drawn or routed element past the content box, or a footprint inside the headroom."""
    w, h = layout.area.w, layout.area.h
    found: list[str] = []

    def box(what: str, b: Box, top: int, bottom: int) -> None:
        if b.x < 0 or b.x + b.w > w or b.y < top or b.y + b.h > h - bottom:
            found.append(f"{what} {b}")

    for page in layout.placement.pages:
        for p in page.placed:
            box(f"symbol {p.sym}", p.footprint, TOP, BOTTOM)
    wires = [wire for page in layout.routes.pages for wire in page.wires]
    found += [
        f"wire {wire.net} {wire.points}"
        for wire in wires
        if any(not (0 <= x <= w and 0 <= y <= h) for x, y in wire.points)
    ]
    notes = layout.annotations
    for item in (*notes.annexes, *notes.tables, *notes.wire_labels):
        box(f"{type(item).__name__} page {item.page}", item.box, 0, 0)
    found += [
        f"marker {m.net} at {m.x},{m.y}"
        for m in notes.markers
        if not (0 <= m.x <= w and 0 <= m.y <= h)
    ]
    return found


@pytest.mark.parametrize("name", sorted(CASES))
def test_nothing_drawn_or_routed_stands_outside_the_content_box(name: str) -> None:
    layout = solved(name)[0]
    assert layout.placement.pages, name
    assert _outside(layout) == []


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_first_row_stands_three_lanes_down_and_the_last_ends_a_lane_up(name: str) -> None:
    layout = solved(name)[0]
    feet = [p.footprint for page in layout.placement.pages for p in page.placed]
    assert min(f.y for f in feet) >= TOP
    assert max(f.y + f.h for f in feet) <= layout.area.h - BOTTOM


@pytest.mark.parametrize("name", ["drawn-supply", "pilot"])
def test_a_page_too_short_for_the_headroom_names_the_overflow_and_the_fix(name: str) -> None:
    layout = solved_in(name, Size(solved(name)[0].area.w, 80))
    overflow = [f for f in layout.findings if f.code == "PAGE_OVERFLOW"]
    assert overflow
    assert all("enlarge the page" in f.text for f in overflow)
