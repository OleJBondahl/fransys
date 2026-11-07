"""ROUTING (R404, R409): no wire passes through a reference marker's box, on every example page.

Six cases: the demo skid and the standard placement corpus (machine_panel, panel_di16p, remote_io,
distribution_board, mcc). Each set's core layout is caught where `fransys_el` solves it; a marker's
"""

import importlib
from itertools import pairwise
from typing import Any

import pytest
from _core_solves import caught_solves
from _export_signature import is_export

from fransys_layout.core import through
from fransys_layout.core.geometry import marker_box

run: Any = None if is_export() else importlib.import_module("placement_corpus.run")

_CORPUS = {"machine_panel", "panel_di16p", "remote_io", "distribution_board", "mcc"}
_CASES = (
    [("export",)]  # one placeholder, skipped by its marker (R462)
    if run is None
    else [c for c in run.circuits("standard") if c[0] in _CORPUS] + [("demo-skid", run.load(run.SKID, "demo_skid_marker_boxes"), {}, {})]
)


def _layouts(case: Any) -> list[tuple[Any, Any]]:
    """Each drawing set's (core layout, options), caught as the build solves it."""
    _, caught = caught_solves(lambda: run.build(case[0], case))
    return [(layout, options) for _, options, layout in caught]


def _struck(layout: Any, options: Any) -> list[str]:
    """`page net` of each marker some wire passes through; a wire ending at the marker's own pin may run along its edge (R1135, `core.through`)."""
    return [
        f"page {m.page} {m.net} at ({m.x}, {m.y}) {m.orient}"
        for m in layout.annotations.markers
        for page in layout.routes.pages
        if page.page == m.page
        if any(
            through(a, b, marker_box(m, options), (w.points[0], w.points[-1]), [(m.x, m.y)])
            for w in page.wires
            for a, b in pairwise(w.points)
            if a != b
        )
    ]


#: R1165: R1138 looks trade (OVERLAP -1, WIRE_OVER_MARKER +1): panel_di16p kept one struck marker, recorded not defended.
#: R1193 (KI-457): the ledger's leg and copy stubs add one to panel_di16p and one to distribution_board.
_LOOKS = {
    "panel_di16p": 2,
    "distribution_board": 1,
    "remote_io": 2,
}  # ONE-PAGE (R1830, looks class): the widest reference text names the far document

#: Strikes measured on 6a70c6824 (they stay red as rows of `tests/gap_flip_other.toml`):
#: machine_panel
#: 372, mcc 100, panel_di16p 259, remote_io 76. Every struck box WAS a route obstacle; the striking
#: wires are the fixed lane, join, trunk and drop wires (and risers at their own pin), which never
#: read obstacles (MAC-B STOP, R404 R409, R416).


@pytest.mark.private_input  # reads internal/ (R462)
@pytest.mark.rule("ROUTING")
@pytest.mark.parametrize("case", _CASES, ids=[c[0] for c in _CASES])
def test_no_wire_passes_through_a_marker_box(case: Any) -> None:
    layouts = _layouts(case)
    assert layouts, f"{case[0]}: no drawing set was solved"
    assert any(lay.annotations.markers for lay, _ in layouts), case[0]
    struck = [s for lay, opts in layouts for s in _struck(lay, opts)]
    assert len(struck) <= _LOOKS.get(case[0], 0), (len(struck), struck[:8])
