"""Field case: a unit strip wired inside to buttons and outside to a field strip, drawn by the core.

The engineering shape: a cabinet unit holds an interface strip `-X` of four terminals and one push
button per terminal. The container wires each terminal's outer side to a field strip `-X9`. Every
net therefore crosses the unit's boundary.

The bug (study, P7.4): today's engine drew the unit's terminals off their column (13 on the
strip-to-module instance) and a unit page with a reference marker at every crossing. The core path
must draw each terminal on the straight vertical wire of its column and end each crossing net in a
stub at the unit's boundary pins (two per net).

The decision: el-0009 (the unit family needs no builder beyond the generic one; the facts
`Facts.units` and `Net.crosses_unit` carry it). The markers are on main (ELECTRICAL-MARKERS) but
`fransys_el.lay_out_drawn` still writes `markers=()`, so the stubs wait on CORE-TEXTS (Ruling 57;
strict xfail); the same counts pass at solve level
in `packages/fransys-el/tests/test_unit_outline.py`.
"""

import fransys as fr
from _drawn_pages import drawn_pages
from _unit_outline_case import TERMINALS, unit_outline_case_drafts

_MARKER = "reference-marker"  # the library symbol a stub draws as (ELECTRICAL-MARKERS)


def _terminals_off_column(result: fr.BuildResult) -> int:
    """Terminals with no straight vertical drawn wire on their x (the scorer's junction rule)."""
    pages = drawn_pages(result.model)
    straight = {
        (page, w.points[0][0])
        for page, drawing in pages.items()
        for w in drawing.wires
        if len({x for x, _ in w.points}) == 1 and w.points
    }
    return sum(
        1
        for page, drawing in pages.items()
        for s in drawing.symbols
        if s.key == "terminal" and (page, s.x) not in straight
    )


def _stubs(result: fr.BuildResult) -> int:
    return sum(
        1
        for drawing in drawn_pages(result.model).values()
        for m in drawing.markers
        if m.key == _MARKER
    )


def test_the_unit_case_is_drawn_on_the_core_path_with_its_terminals_on_column() -> None:
    """No xfail: a core-path or terminal failure shows here, not as the strict xfail below."""
    result = fr.build(*unit_outline_case_drafts())
    assert _terminals_off_column(result) == 0


def test_a_unit_wired_inside_and_out_ends_each_crossing_net_in_a_stub() -> None:
    assert _stubs(fr.build(*unit_outline_case_drafts())) == 2 * TERMINALS
