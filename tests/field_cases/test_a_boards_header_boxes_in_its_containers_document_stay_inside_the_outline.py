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
from _drawn_extent import Rect, body_g
from _drawn_pages import drawn_pages
from fransys.colours import WH

lazy from fransys_layout.drawing import Drawing


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


def _crosses(box: Rect, pts: tuple[tuple[int, int], ...]) -> bool:
    """Whether a segment of the polyline `pts` passes through the interior of `box`."""
    x0, y0, x1, y1 = box
    for (ax, ay), (bx, by) in itertools.pairwise(pts):
        if min(ax, bx) < x1 and x0 < max(ax, bx) and min(ay, by) < y1 and y0 < max(ay, by):
            return True
    return False


def _inside(box: Rect, texts: list[Rect]) -> bool:
    """Whether every stored text rectangle of `box` lies inside its rectangle."""
    x0, y0, x1, y1 = box
    return all(x0 <= a and b <= x1 and y0 <= c and d <= y1 for a, c, b, d in texts)


def _boxes(drawing: Drawing) -> list[tuple[Rect, list[Rect]]]:
    """Each box symbol of the page with the rectangles of the texts that touch it."""
    out = []
    for s in drawing.symbols:
        if s.key != "generic-box":
            continue
        box = body_g(s)
        texts = [
            (t.box.x, t.box.y, t.box.x + t.box.w, t.box.y + t.box.h)
            for t in drawing.texts
            if t.box.x < box[2]
            and box[0] < t.box.x + t.box.w
            and t.box.y < box[3]
            and box[1] < t.box.y + t.box.h
        ]
        out.append((box, texts))
    return out


def test_a_connector_box_holds_its_ink_and_no_wire_crosses_it(tmp_path: Path) -> None:
    pages = drawn_pages(_build(tmp_path).model).values()
    boxes = [(b, t, d) for d in pages for b, t in _boxes(d)]
    assert len(boxes) >= 2  # positive half: the container's document boxes the headers
    assert [b for b, t, _ in boxes if not _inside(b, t)] == []
    assert [(b, w.id) for b, _, d in boxes for w in d.wires if _crosses(b, w.points)] == []


def test_the_two_checks_can_fail() -> None:
    box = (0, 0, 10, 10)
    assert _crosses(box, ((-5, 5), (15, 5)))
    assert not _crosses(box, ((-5, 10), (15, 10)))  # an edge is no interior
    assert not _inside(box, [(20, 5, 22, 7)])
    assert _inside(box, [(2, 5, 4, 7)])


def test_the_header_boxes_stand_strictly_inside_the_board_outline(tmp_path: Path) -> None:
    pairs = []
    for d in drawn_pages(_build(tmp_path).model).values():
        for o in d.outlines:
            ox0, oy0 = min(p[0] for p in o.points), min(p[1] for p in o.points)
            ox1, oy1 = max(p[0] for p in o.points), max(p[1] for p in o.points)
            pairs += [
                ((ox0, oy0, ox1, oy1), b)
                for b, _ in _boxes(d)
                if ox0 <= b[0] and b[2] <= ox1 and oy0 <= b[1] and b[3] <= oy1
            ]
    assert len(pairs) >= 2  # positive half: the outline holds the header boxes
    offenders = [
        b
        for (ox0, oy0, ox1, oy1), b in pairs
        if not (ox0 < b[0] and b[2] < ox1 and oy0 < b[1] and b[3] < oy1)
    ]
    assert offenders == []


def test_the_nested_board_is_drawn_inside_an_outline(tmp_path: Path) -> None:
    """The nested board gets its frame and caption: one drawn outline per unit boundary.

    The core path sets `outlines=()` (UNIT-SCOPE, pending OUTLINES; GAP-FLIP-208, designer R302).
    Read from the drawn pages, as the test above does.
    """
    assert sum(len(d.outlines) for d in drawn_pages(_build(tmp_path).model).values()) >= 1
