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
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK

from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.geometry import text_width
from fransys_model.layout import (
    ConnectorBox,
    HarnessLine,
    LinkMarker,
    Outline,
    Page,
    StubEnd,
    layout_of,
)
from fransys_model.vocab.tables import ports


class _Io(NamedTuple):
    X7: fr.Device


class _Open(NamedTuple):
    pass


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    x7 = u.device("X7", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    lamp = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.wire(x7[1], lamp["1"], wire=(BK, 0.5))
    u.wire(x7[2], lamp["2"], wire=(BK, 0.5))
    return _Io(x7)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    board = u.add(_board, "U1")
    j1 = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    for n in (1, 2):
        u.wire(j1[n], u.device(f"H{n}", "DEMO-LAMP-24")["1"], wire=(BK, 0.5))
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


def _line_stubs() -> list[LinkMarker]:
    return [m for m in layout_of(_built().model, LinkMarker).values() if "line_stub" in m.key]


def test_the_line_runs_to_the_interface_box_on_its_own_page_and_leaves_no_stub() -> None:
    assert _line_stubs() == []


def test_the_line_reaches_the_interface_box() -> None:
    model = _built().model
    boxes = [b for b in layout_of(model, ConnectorBox).values() if "U1" in b.key and not b.cells]
    lines = layout_of(model, HarnessLine).values()
    touched = [
        (b, line)
        for b in boxes
        for line in lines
        if line.page == b.page
        and any(b.x <= p.x <= b.x + b.width and b.y <= p.y <= b.y + b.height for p in line.points)
    ]
    assert touched != []


def test_no_stub_end_names_a_box_of_its_own_drawing_set_without_a_page() -> None:
    """The printed page of an arrow box is set whenever its far end's box is in the stub's set."""
    model = _built().model
    pages, markers = layout_of(model, Page), layout_of(model, LinkMarker)
    boxed = {
        (b.function, pages[b.page].drawing_set) for b in layout_of(model, ConnectorBox).values()
    }
    unpaged = [
        end.key
        for end in layout_of(model, StubEnd).values()
        if end.page is None
        and (ports(model)[end.port].function, pages[markers[end.marker].page].drawing_set) in boxed
    ]
    assert unpaged == []


def _route() -> tuple[ConnectorBox, HarnessLine, ConnectorBox]:
    """`-U1-X7`'s box, `-W1`'s line on its page and `-J1`'s box beyond (the route's far end)."""
    model = _built().model
    boxes = list(layout_of(model, ConnectorBox).values())
    line = next(iter(layout_of(model, HarnessLine).values()))
    interface = next(b for b in boxes if "U1" in b.key and b.page == line.page)
    other = next(b for b in boxes if "J1" in b.key and b.page == line.page)
    return interface, line, other


def test_the_line_ends_on_the_box_edge_facing_its_route_and_never_wraps_round_the_box() -> None:
    """The far box lies below, so the line ends on the bottom edge and stays below the box."""
    box, line, other = _route()
    assert other.y > box.y + box.height
    bottom = box.y + box.height
    ends = [line.points[0], line.points[-1]]
    on_edge = [p for p in ends if p.y == bottom and box.x <= p.x <= box.x + box.width]
    assert len(on_edge) == 1
    assert all(p.y >= bottom for p in line.points)


def test_the_cable_label_clears_the_interface_box_and_the_board_outline() -> None:
    model = _built().model
    box, line, _ = _route()
    outline = next(o for o in layout_of(model, Outline).values() if o.page == box.page)
    height = DEFAULT_PROFILE.text_height
    width = text_width("-W1", height=height)
    label = (line.text_x - width // 2, line.text_y - height // 2, width, height)
    assert not _meets(label, (box.x, box.y, box.width, box.height))
    assert not _meets_border(label, (outline.x, outline.y, outline.width, outline.height))


def _meets(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    """Whether two rectangles (x, y, width, height) share a point, a touching edge too."""
    return (
        a[0] <= b[0] + b[2] and b[0] <= a[0] + a[2] and a[1] <= b[1] + b[3] and b[1] <= a[1] + a[3]
    )


def _meets_border(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    """Whether rectangle `a` meets `b` without lying wholly inside it."""
    inside = b[0] < a[0] and b[1] < a[1] and a[0] + a[2] < b[0] + b[2] and a[1] + a[3] < b[1] + b[3]
    return _meets(a, b) and not inside
