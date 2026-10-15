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
from functools import cache
from pathlib import Path
from typing import Any
from unittest import mock

import fransys as fr
from fransys.colours import BK

from fransys_layout.engines.schematic import engine
from fransys_model.layout import ConnectorBox, Page, layout_of

PAIRS = 8


@cache
def _built() -> tuple[fr.BuildResult, int]:
    """The build, and how many pin views the layout placed (one build serves both tests)."""
    real = engine.stage_layout
    placed: list[int] = []

    def counting(model: Any, inputs: Any) -> Any:
        staged = real(model, inputs)
        placed.append(len(staged[0].layout.placed))
        return staged

    with mock.patch.object(engine, "stage_layout", counting):
        return _build(), placed[-1]


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
    model = _built()[0].model
    boxes = layout_of(model, ConnectorBox).values()
    assert len(boxes) == 3 * PAIRS
    assert len({b.page for b in boxes}) == 1
    assert len(layout_of(model, Page)) == 1


def test_a_plugs_pin_views_with_no_cell_or_wire_leave_their_columns() -> None:
    """Eight lamps, the headers' four celled views each, and one view for each of 16 plugs."""
    assert _built()[1] == PAIRS * (1 + 4 + 2)
