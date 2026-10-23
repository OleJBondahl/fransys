"""Field case: a cable core between a device and a nested unit's interface on one page.

The engineering shape: a cabinet unit holds a header `-J1` wired to two lamps and a board unit `-U1`
whose connector `-X7` is its interface. A cable `-W1` has two cores from `-J1` to `-X7`. The
cabinet's page draws `-J1`, the board's outline and `-X7`'s box on it.

The bug: the end at `-X7` had no pins on the page (its views leave their columns, the box stands in
the outline), so the line counted one end here and ran out to an off-page stub whose arrow box
named `-U1-X7`, a box on the same page, with no page and no cell (`StubEnd.page` was `None`).

Rule (layout-0155, harness-lines HL18): when the far end stands on the same page, the harness
line runs to it; an arrow box that leads elsewhere prints its page and cell. Decision layout-0206.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_extent import Rect, body_g
from _drawn_pages import drawn_pages
from fransys.colours import BK

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnWire


class _Io(NamedTuple):
    X7: fr.Device


class _Open(NamedTuple):
    pass


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    x7 = u.device("X7", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    lamp = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.detail.wire(x7[1], lamp["1"], wire=(BK, 0.5))
    u.detail.wire(x7[2], lamp["2"], wire=(BK, 0.5))
    return _Io(x7)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    board = u.add(_board, "U1")
    j1 = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    for n in (1, 2):
        u.detail.wire(j1[n], u.device(f"H{n}", "DEMO-LAMP-24")["1"], wire=(BK, 0.5))
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, board.X7[1], j1[1])
    cable.core(2, board.X7[2], j1[2])
    return _Open()


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover))


def _pages() -> list[Drawing]:
    return list(drawn_pages(_built().model).values())


def _stub_markers() -> list[DrawnSymbol]:
    """The reference markers that stand for the cable `-W1` (a stub to its far end)."""
    return [
        s
        for d in _pages()
        for s in d.symbols
        if s.key == "reference-marker" and any("-W1" in v for _, v in s.slots)
    ]


def _boxes(d: Drawing) -> list[Rect]:
    """The bodies of the interface connector `-U1-X7` on page `d`, found by its tag texts."""
    tags = {t.text.split(":")[0] for t in d.texts if t.text.startswith("-C1-U1-X7")}
    return [body_g(s) for s in d.symbols if s.key.startswith("connector") and tags]


def test_the_line_runs_to_the_interface_box_on_its_own_page_and_leaves_no_stub() -> None:
    assert _stub_markers() == []


def test_the_line_reaches_the_interface_box() -> None:
    touched = [
        (b, w)
        for d in _pages()
        for b in _boxes(d)
        for w in d.wires
        if w.lanes > 1 and any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in w.points)
    ]
    assert touched != []


def test_no_stub_end_names_a_box_of_its_own_drawing_set_without_a_page() -> None:
    """A stub whose far end's box is in its own drawing set prints its page: here, none stands."""
    unpaged = [m.slots for m in _stub_markers() if not any("/" in v for _, v in m.slots)]
    assert unpaged == []


def _route() -> tuple[Rect, DrawnWire, Rect]:
    """`-U1-X7`'s box, `-W1`'s line on its page and `-J1`'s box beyond (the route's far end)."""
    for d in _pages():
        line = next((w for w in d.wires if w.lanes > 1), None)
        if line is not None:
            boxes = sorted(_boxes(d), key=lambda b: b[1])
            return boxes[0], line, boxes[-1]
    msg = "no harness line is drawn"
    raise AssertionError(msg)


def test_the_line_ends_on_the_box_edge_facing_its_route_and_never_wraps_round_the_box() -> None:
    """The far box lies below, so the line ends on the bottom edge and stays below the box."""
    box, line, other = _route()
    assert other[1] > box[3]
    ends = [line.points[0], line.points[-1]]
    on_edge = [p for p in ends if p[1] == box[3] and box[0] <= p[0] <= box[2]]
    assert len(on_edge) == 1
    assert all(p[1] >= box[3] for p in line.points)


def test_the_cable_label_clears_the_interface_box_and_the_board_outline() -> None:
    box, line, _ = _route()
    assert line.label is not None
    label = line.label.box
    label_rect = (label.x, label.y, label.x + label.w, label.y + label.h)
    (outline,) = (o for d in _pages() for o in d.outlines)
    xs, ys = [p[0] for p in outline.points], [p[1] for p in outline.points]
    assert not _meets(label_rect, box)
    assert not _meets_border(label_rect, (min(xs), min(ys), max(xs), max(ys)))


def _meets(a: Rect, b: Rect) -> bool:
    """Whether two rectangles (x0, y0, x1, y1) share a point, a touching edge too."""
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def _meets_border(a: Rect, b: Rect) -> bool:
    """Whether rectangle `a` meets `b` without lying wholly inside it."""
    inside = b[0] < a[0] and b[1] < a[1] and a[2] < b[2] and a[3] < b[3]
    return _meets(a, b) and not inside
