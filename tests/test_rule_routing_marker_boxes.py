"""ROUTING (R404, R409): no wire passes through a reference marker's box, on every example page.

Six cases: the demo skid and the standard placement corpus (machine_panel, panel_di16p, remote_io,
distribution_board, mcc). Each set's core layout is caught where `fransys_el` solves it; a marker's
box is the one the router took as an obstacle (`marker_box`), and a strike is a wire segment
through the box's interior (`struck_texts`). The markers stand before the routes (owner O2).
"""

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from _export_signature import is_export
from fransys_el import lay_out_core

from fransys_layout.core.geometry import marker_box
from fransys_layout.drawing import struck_texts

sys.path.insert(0, str(Path(__file__).parents[1] / "internal"))
run: Any = None if is_export() else importlib.import_module("placement_corpus.run")

_CORPUS = {"machine_panel", "panel_di16p", "remote_io", "distribution_board", "mcc"}
_CASES = (
    [("export",)]  # one placeholder, skipped by its marker (R462)
    if run is None
    else [c for c in run.circuits("standard") if c[0] in _CORPUS]
    + [("demo-skid", run.load(run.SKID, "demo_skid_marker_boxes"), {}, {})]
)


@dataclass(frozen=True)
class _Boxed:
    """A marker's box in the shape `struck_texts` reads."""

    box: Any
    what: str


@dataclass(frozen=True)
class _Line:
    """A routed wire in the shape `struck_texts` reads."""

    id: str
    points: Any
    label: None = None


def _layouts(case: Any) -> list[tuple[Any, Any]]:
    """Each drawing set's (core layout, options), caught as the build solves it."""
    caught: list[tuple[Any, Any]] = []
    solve = lay_out_core.solve

    def catching(problem: Any, options: Any) -> Any:
        layout = solve(problem, options)
        caught.append((layout, options))
        return layout

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(lay_out_core, "solve", catching)
        run.build(case[0], case)
    return caught


def _struck(layout: Any, options: Any) -> list[str]:
    """`page net` of each marker some wire passes through."""
    wires = {
        page.page: [_Line(f"{w.net}#{i}", w.points) for i, w in enumerate(page.wires)]
        for page in layout.routes.pages
    }
    return [
        f"page {m.page} {m.net} at ({m.x}, {m.y}) {m.orient}"
        for m in layout.annotations.markers
        if struck_texts(wires.get(m.page, []), [_Boxed(marker_box(m, options), "")])
    ]


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
    assert not struck, (len(struck), struck[:8])
