"""Field case: a box at the left edge of a schematic page's content keeps a gap to the frame line.
The bug: the schematic placed its ink on the content edge, so the box and its tag sat on the frame line and read as touching it.
Fixed by layout-0187, schematic content keeps the diagram's one `PAGE_PAD` inside the frame line (spec EXACT-SIZES E11)."""

from functools import cache
from typing import Any

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document

from electrical_symbols import LIBRARY
from fransys_layout.geometry import PAGE_PAD
from fransys_layout.symbols import library_symbol, symbol_shape


@cache
def _left_edges() -> tuple[Any, ...]:
    """The left edge of the keep-out (body and text slots) of every drawn symbol, for one relay."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        k = d.device("K1", "DEMO-RLY-2CO-24")
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        d.series(x1[1].inner, k.coil["A1"], wire=("WH", 0.75))
        d.series(x1[2].inner, k.coil["A2"], wire=("WH", 0.75))
    doc = unit_document(cab)
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
