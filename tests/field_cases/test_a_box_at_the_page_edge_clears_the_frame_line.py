"""Field case: a box at the left edge of a schematic page's content keeps a gap to the frame line.

The engineering shape: a cabinet with one relay in one function, in a `CABINET_SCHEMATIC`
document. The relay is the only thing on the page, so it sits in the first column, at the
content box's left edge.

The bug (a consumer's repro, v0.14.0): the schematic placed its ink at the content edge, so the
box and its tag sat on the frame line and read as touching it. The block diagram already kept a
gap of `PAGE_PAD`, two wiring lanes.
The rule (decision layout-0187, spec EXACT-SIZES E11): schematic content keeps the diagram's one
`PAGE_PAD` inside the frame line. The page coordinates start at the frame line, x = 0.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import PAGE_PAD
from fransys_layout.stages.lookups import placed_keepout


@cache
def _placed_boxes() -> tuple:
    """The keep-out boxes of every function the layout placed, for one built relay."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        d.device("K1", "DEMO-RLY-2CO-24")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    return tuple(placed_keepout(one) for one in results.layout.placed)


def test_a_box_at_the_left_edge_clears_the_frame_line_by_the_page_pad() -> None:
    """The one relay is placed, and its left edge is at least `PAGE_PAD` from x = 0."""
    (box,) = _placed_boxes()
    assert box.width > 0
    assert box.x >= PAGE_PAD, (box.x, PAGE_PAD)
