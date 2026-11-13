"""Field case: a cable between a cabinet header and a nested board unit's interface connector, drawn on one page.
The bug: the end at `-X7` had no pins on the page, so the line ran out to an off-page stub that named `-U1-X7`, a box on the same page.
Fixed by layout-0206, under layout-0155 (HL18) the harness line runs to a far end on this page; an arrow box prints its page and cell."""

from functools import cache
from typing import TYPE_CHECKING

from _drawn_extent import Rect, body_g
from _drawn_pages import drawn_pages
from board_cab import build_board_cab
lazy import fransys as fr

from electrical_symbols import MARKER_TURNED, marker_symbol

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnWire


@cache
def _built() -> fr.BuildResult:
    return build_board_cab()


def _pages() -> list[Drawing]:
    return list(drawn_pages(_built().model).values())


def _stub_markers() -> list[DrawnSymbol]:
    """The reference markers that stand for the cable `-W1` (a stub to its far end)."""
    return [s for d in _pages() for s in d.symbols if s.key in {marker_symbol("stub"), MARKER_TURNED} and any("-W1" in v for _, v in s.slots)]


def _boxes(d: Drawing) -> list[Rect]:
    """The bodies of the interface connector `-U1-X7` on page `d`, found by its tag texts."""
    tags = {t.text.split(":")[0] for t in d.texts if t.text.startswith("-C1-U1-X7")}
    return [body_g(s) for s in d.symbols if s.key.startswith("connector") and tags]


def _line_drawn() -> bool:
    return any(w.style == "trunk" for d in _pages() for w in d.wires)


def _unpaired() -> list[str]:
    """The nets of `-W1` whose markers are not one pair that names each far end: the cabinet end names `-C1-J1`, the board end `-U1-X7` (R1683)."""
    texts: dict[str, list[str]] = {}
    for m in _stub_markers():
        texts.setdefault(m.net, []).extend(v.split()[-1] for _, v in m.slots)
    return [net for net, ends in texts.items() if sorted(ends) != ["-C1-J1", "-U1-X7"]]


def test_the_line_runs_to_the_interface_box_or_a_complete_pair_names_each_far_end() -> None:
    """The two ends stand in two drawing sets, so no path joins them on a page: the reference pair is the drawing (owner 2026-10-27)."""
    assert _line_drawn() or (len(_stub_markers()) == 4 and _unpaired() == [])


def test_the_line_reaches_the_interface_box() -> None:
    touched = [
        (b, w)
        for d in _pages()
        for b in _boxes(d)
        for w in d.wires
        if w.style == "trunk" and any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in w.points)
    ]
    assert touched != []


def test_no_stub_end_names_a_box_standing_on_its_own_page() -> None:
    """A marker names the far end's box, which stands in the other drawing set: none names a box of its own page."""
    own = [
        m.slots
        for d in _pages()
        for m in _stub_markers()
        if m in d.symbols and any(t.text.startswith(v.split()[-1] + ":") for t in d.texts for _, v in m.slots)
    ]
    assert own == []


def _route() -> tuple[Rect, DrawnWire, Rect]:
    """`-U1-X7`'s box, `-W1`'s line on its page and `-J1`'s box beyond (the route's far end)."""
    for d in _pages():
        line = next((w for w in d.wires if w.style == "trunk"), None)
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
