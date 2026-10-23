"""Field case: boxed connector pairs pack by their boxes, not by their pin views.

The engineering shape: a cabinet holds eight 4-way headers, each wired on its first pin to a lamp
and mated to the plug of its own loom; each loom's other plug ends at the far side. Each header and
each plug draws as a box on a harness line, so 24 boxes stand on the cabinet's drawing.

The bug: a boxed connector's pin views kept their packing columns and widths though they draw no
symbol, so a pair took as many columns as its pins and the eight pairs ran onto a second page.

Rule (harness-lines.md Pipeline step 2, decision layout-0206): a boxed connector's pin views with
no cell leave their columns, and a boxed connector takes one packing column of its box's width.
"""

import tempfile
from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BK

from fransys_model.layout import Page, layout_of

PAIRS = 8


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    for k in range(PAIRS):
        header = d.device(f"J{k}", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
        d.detail.wire(header[1], d.device(f"H{k}", "DEMO-LAMP-24")["1"], wire=(BK, 0.5))
        loom = d.harness(f"W{k}")
        near = d.device(f"P{k}", "DEMO-HSG-4M", parent=loom, contacts="DEMO-CRIMP-M")
        far = d.device(f"Q{k}", "DEMO-HSG-4M", parent=loom, contacts="DEMO-CRIMP-M")
        d.mate(near, header)
        for pin in (1, 2, 3, 4):
            d.detail.wire(near[pin], far[pin], wire=(BK, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_the_eight_pairs_stand_on_one_page() -> None:
    model = _build().model
    pages = drawn_pages(model)
    boxes = [
        (page, s)
        for page, drawing in pages.items()
        for s in drawing.symbols
        if s.key == "connector-fixed"
    ]
    assert len(boxes) == 3 * PAIRS
    assert len({page for page, _ in boxes}) == 1
    assert len(layout_of(model, Page)) == 1


def test_a_plugs_pin_views_with_no_cell_or_wire_leave_their_columns() -> None:
    """Only the eight lamps draw as symbols; no pin of a boxed connector keeps a column of its own.

    A pin view that kept its column would show as a per-pin symbol drawn beside the box.
    """
    others = [
        s
        for drawing in drawn_pages(_build().model).values()
        for s in drawing.symbols
        if s.key not in ("connector-fixed", "junction-dot")
    ]
    assert len(others) == PAIRS
