"""Field case: a box at the left edge of a schematic page's content keeps a gap to the frame line.

The engineering shape: a cabinet with one relay fed from a two-terminal strip in one function,
in a `CABINET_SCHEMATIC` document. The first column sits at the content box's left edge.
(Layout-0218: an unwired relay is drawn on no page, so the relay's coil is fed.)

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
from _drawn_pages import drawn_pages

from electrical_symbols import LIBRARY
from fransys_layout.geometry import PAGE_PAD
from fransys_layout.symbols import library_symbol, symbol_shape


@cache
def _left_edges() -> tuple:
    """The left edge of the keep-out (body and text slots) of every drawn symbol, for one relay."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        k = d.device("K1", "DEMO-RLY-2CO-24")
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        d.detail.wire(x1[1], k.coil["A1"], wire=("WH", 0.75))
        d.detail.wire(x1[2], k.coil["A2"], wire=("WH", 0.75))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    edges = []
    for drawing in drawn_pages(fr.build(d, doc).model).values():
        for one in drawing.symbols:
            shape = symbol_shape(library_symbol(LIBRARY, one.key), LIBRARY)
            edges.append(one.x + min(box.x for box in (shape.body, *shape.slots.values())))
    return tuple(edges)


def test_a_box_at_the_left_edge_clears_the_frame_line_by_the_page_pad() -> None:
    """The leftmost drawn box's left edge is at least `PAGE_PAD` from x = 0."""
    edge = min(_left_edges())
    assert edge >= PAGE_PAD, (edge, PAGE_PAD)
