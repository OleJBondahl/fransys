"""Field case: a cabinet unit nests a board unit with two interface headers, each mated by a
harness plug (W4 and W5, plugs wired with single wires). The cabinet's own document draws the
board as one dash-dot outline holding the two header boxes, with each plug's box against them.

The bug, as a consumer's example showed it: the two header boxes are drawn over each other with
wires through them in the container's view. The stored boxes never overlap in the demo-parts
reduction, so this case asserts the rule as stored: every text and cell of a connector box lies
inside the box's stored rectangle, and no wire's polyline passes through the interior of a
stored box.

Measured 2026-10-16 (UNIT-MATE-SCOPE part B): this reduction passes today, so it is no xfail;
the overlap of the consumer's view is not in the stored layout. It is a guard for the unit-outline
switch (P7.4), and its two checks are proved able to fail by the synthetic test below. The
strict-inside xfail is the nearest stored shape of the consumer's defect (an outline drawn on a
box edge is ink on ink), and flips at P7.4.
"""

import itertools
from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import WH

from fransys_model.kernel import Id
from fransys_model.layout import BoxText, ConnectorBox, Outline, Route, layout_of


class _Headers(NamedTuple):
    J1: fr.Device
    J2: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-16", text="first", by="XX")
def _board(u: fr.Design) -> _Headers:
    pcb = u.device("U9", "DEMO-PCB-IO")
    k1 = u.device("K1", "DEMO-RLY-2CO-24", parent=pcb)
    j1 = u.device("J1", "DEMO-CONN-4P", parent=pcb, interface=True)
    j2 = u.device("J2", "DEMO-CONN-4P", parent=pcb, interface=True)
    u.detail.wire(j1["1"], k1.coil["A1"], wire=(WH, 0.5))
    u.detail.wire(j1["3"], k1.coil["A2"], wire=(WH, 0.5))
    u.detail.wire(j2["1"], k1.co_1["11"], wire=(WH, 0.5))
    u.detail.wire(j2["2"], k1.co_1["14"], wire=(WH, 0.5))
    return _Headers(j1, j2)


@fr.unit("demo-cabinet", revision=1, interface_version=1, date="2026-10-16", text="first", by="XX")
def _cabinet(u: fr.Design) -> _Headers:
    with u.function("PLC", "PLC"):
        io = u.device("DO1", "DEMO-PLC-DI-4P", name="io")
        board = u.add(_board, "U2")
        p4 = u.device("J1", "DEMO-CONN-4P", parent=u.harness("W4"))
        p5 = u.device("J2", "DEMO-CONN-4P", parent=u.harness("W5"))
        u.mate(p4, board.J1)
        u.mate(p5, board.J2)
        u.detail.wire(p4["2"], io.di_2["2"], wire=(WH, 0.5))
        u.detail.wire(p4["3"], io.power["0V"], wire=(WH, 0.5))
        u.detail.wire(p5["1"], io.power["24V"], wire=(WH, 0.5))
    return _Headers(board.J1, board.J2)


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_cabinet, "U1")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cabinet", cover=cover)
    return fr.build(d, doc)


def _through(box: ConnectorBox, route: Route) -> bool:
    """Whether `route` has a segment through the interior of `box`."""
    return route.page == box.page and _crosses(box, [(p.x, p.y) for p in route.points])


def _crosses(box: ConnectorBox, pts: list[tuple[int, int]]) -> bool:
    """Whether a segment of the polyline `pts` passes through the interior of `box`."""
    for (x1, y1), (x2, y2) in itertools.pairwise(pts):
        low_x, high_x, low_y, high_y = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
        if (
            low_x < box.x + box.width
            and box.x < high_x
            and low_y < box.y + box.height
            and box.y < high_y
        ):
            return True
    return False


def _inside(box: ConnectorBox) -> bool:
    """Whether every stored text anchor and cell of `box` lies inside its rectangle."""
    right, foot = box.x + box.width, box.y + box.height
    texts = all(box.x <= t.x < right and box.y <= t.y < foot for t in box.texts)
    cells = all(
        box.x <= c.x and c.x + c.width <= right and box.y <= c.y and c.y + c.height <= foot
        for c in box.cells
    )
    return texts and cells


def test_a_connector_box_holds_its_ink_and_no_wire_crosses_it(tmp_path: Path) -> None:
    model = _build(tmp_path).model
    boxes = list(layout_of(model, ConnectorBox).values())
    assert len(boxes) >= 2  # positive half: the container's document boxes the headers
    assert [b for b in boxes if not _inside(b)] == []
    routes = list(layout_of(model, Route).values())
    assert [(b.function, r.id) for b in boxes for r in routes if _through(b, r)] == []


def _box(*, texts: tuple[BoxText, ...] = ()) -> ConnectorBox:
    return ConnectorBox(
        id=Id(kind="layout.connector_box", value="b"),
        key=("k",),
        page=Id(kind="layout.page", value="p"),
        function=Id(kind="function", value="f"),
        x=0,
        y=0,
        width=10,
        height=10,
        texts=texts,
        cells=(),
        produced_by="t",
    )


def test_the_two_checks_can_fail() -> None:
    box = _box()
    assert _crosses(box, [(-5, 5), (15, 5)])
    assert not _crosses(box, [(-5, 10), (15, 10)])  # an edge is no interior
    assert not _inside(_box(texts=(BoxText(index=0, x=20, y=5),)))
    assert _inside(_box(texts=(BoxText(index=0, x=2, y=5),)))


@pytest.mark.xfail(
    strict=True,
    reason="P7.4: a header box is drawn on the board outline's edge, ink on ink; the boxes must "
    "stand strictly inside the outline",
)
def test_the_header_boxes_stand_strictly_inside_the_board_outline(tmp_path: Path) -> None:
    model = _build(tmp_path).model
    outlines = list(layout_of(model, Outline).values())
    boxes = list(layout_of(model, ConnectorBox).values())
    pairs = [
        (outline, b)
        for outline in outlines
        for b in boxes
        if b.page == outline.page
        and outline.x <= b.x
        and b.x + b.width <= outline.x + outline.width
        and outline.y <= b.y
        and b.y + b.height <= outline.y + outline.height
    ]
    assert len(pairs) >= 2  # positive half: the outline holds the header boxes
    offenders = [
        (b.x, b.y, b.width, b.height)
        for outline, b in pairs
        if not (
            outline.x < b.x
            and b.x + b.width < outline.x + outline.width
            and outline.y < b.y
            and b.y + b.height < outline.y + outline.height
        )
    ]
    assert offenders == []
