"""Field case: a unit strip wired inside to buttons and outside to a field strip, drawn by the core.
The bug: today's engine drew the unit's terminals off their column and put a reference marker at every crossing.
Closed: the stubs draw as marker-arrow-turned and the test asserts them (OC-REMEASURE, R1431)."""

import fransys as fr
from _drawn_pages import drawn_pages, markers_in
from _unit_outline_case import TERMINALS, unit_outline_case_drafts

_MARKER = "marker-arrow-turned"  # the library symbol a stub draws as (ELECTRICAL-MARKERS)


def _terminals_off_column(result: fr.BuildResult) -> int:
    """Terminals with no straight vertical drawn wire on their x (the scorer's junction rule)."""
    pages = drawn_pages(result.model)
    straight = {(page, w.points[0][0]) for page, drawing in pages.items() for w in drawing.wires if len({x for x, _ in w.points}) == 1 and w.points}
    return sum(1 for page, drawing in pages.items() for s in drawing.symbols if s.key == "terminal" and (page, s.x) not in straight)


def _stubs(result: fr.BuildResult) -> int:
    return sum(1 for drawing in drawn_pages(result.model).values() for m in markers_in(drawing) if m.key == _MARKER)


def test_the_unit_case_is_drawn_on_the_core_path_with_its_terminals_on_column() -> None:
    """A core-path or terminal failure shows here, apart from the stub count below."""
    result = fr.build(*unit_outline_case_drafts())
    assert _terminals_off_column(result) == 0


def test_a_unit_wired_inside_and_out_ends_each_crossing_net_in_a_stub() -> None:
    assert _stubs(fr.build(*unit_outline_case_drafts())) == 2 * TERMINALS
