"""Field case: a chain stood beside a host joins it by one end net, or by one end net and a box.

The engineering shape: a fuse feeds a lamp, the lamp feeds a relay coil, and the coil returns to a
terminal strip. The lamp-coil branch is a chain of its own, advised `beside=` the fuse. Only the
lamp's end net is a net of the fuse; the coil's return runs elsewhere. A second shape ends the
branch in a one-pin PLC channel, which has no net of its own and so joins nothing.

The bug: `check_beside` demanded two end nets that were both nets of the host, so a branch with one
end on the host, or with a box at its tail, raised `AuthorError` and the branch drew in a column of
its own with reference markers. Fixed by decision layout-0174 (amended, CHAIN-BESIDE-ENDS): one or
two end nets, at least one on the host, and the end on the host reads first.
"""

import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _drawn_facts import Placed, symbol_subjects
from _drawn_pages import drawn_pages

from electrical_symbols import LIBRARY
from fransys_layout.symbols import library_symbol, symbol_shape

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}
_RED = ("RD", 50)


class _Strips(NamedTuple):
    X1: Any


def _wire(d: Any, shape: str, parts: tuple[Any, ...], tail: Any) -> None:
    """The shared wiring: the lamp hangs from the fuse's lower (`low`) or upper (`up`) net."""
    x1, f1, f2, h1 = parts
    if shape == "mcb":  # the worked example: a 3-pole breaker, a host net of two ports
        for a, b in [
            (x1[1], f2.element["1"]),
            (f2.element["2"], h1["1"]),
            (h1["2"], tail.coil["A1"]),
            (tail.coil["A2"], x1[4]),
        ]:
            d.detail.wire(a, b, wire=_RED)
        return
    hung = f2.element["1"] if shape == "up" else f2.element["2"]
    wires = [(x1[1], f1.element["1"]), (f1.element["2"], f2.element["1"]), (hung, h1["1"])]
    if shape != "up":  # the host net needs a third port: a join is a star net's wire
        wires.append((hung, x1[2]))
    if shape == "box":
        wires.append((h1["2"], tail["1"]))
    else:
        wires += [(h1["2"], tail.coil["A1"]), (tail.coil["A2"], x1[4])]
    for a, b in wires:
        d.detail.wire(a, b, wire=_RED)


def _unit(shape: str, *, beside: bool, bottom_up: bool = False) -> Any:
    @fr.unit("demo-bc", **_UNIT)
    def _bc(d: Any) -> _Strips:
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=True)
        with d.function("MAIN", "Main supply"):
            f1 = d.device("F1", "DEMO-FUSE-DC-160")
            f2 = d.device("F2", "DEMO-MCB-3P" if shape == "mcb" else "DEMO-FUSE-DC-160")
            h1 = d.device("H1", "DEMO-LAMP-24")
            tag, mpn = ("A1", "DEMO-PLC-DO-2") if shape == "box" else ("K1", "DEMO-RLY-2CO-24")
            end = d.device(tag, mpn)
        _wire(d, shape, (x1, f1, f2, h1), end)
        if shape != "mcb":
            d.layout.chain(x1[1], f1.element, f2.element)
        tail = end.do_1 if shape == "box" else end.coil
        steps = (tail, h1.lamp) if bottom_up else (h1.lamp, tail)
        if beside:
            d.layout.chain(*steps, beside=f2.element)
        else:
            d.layout.chain(*steps)
        return _Strips(x1)

    return _bc


def _build(shape: str, *, beside: bool = True, bottom_up: bool = False) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_unit(shape, beside=beside, bottom_up=bottom_up), "U1")
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-bc", cover=root / "c.md")
    return fr.build(d, cover)


type Point = tuple[int, int]


def _drawn(result: fr.BuildResult, tag: str) -> Placed:
    """The one drawn symbol of the item `tag`, not its contact head."""
    (one,) = (
        r
        for r in symbol_subjects(result.model)
        if r.tag == f"U1-{tag}" and r.symbol != "contact-head"
    )
    return one


def _shape(one: Placed):  # the symbol's pins and body at R0, from symdef's data
    return symbol_shape(library_symbol(LIBRARY, one.key, one.poles), LIBRARY)


def _pin(result: fr.BuildResult, tag: str, pin: str) -> Point:
    one, turn = _drawn(result, tag), _shape(_drawn(result, tag)).pins[pin]
    return one.x + turn.dx, one.y + turn.dy


def _at(result: fr.BuildResult, tag: str) -> Point:
    """The drawn position of the item `tag`, as (x, y)."""
    one = _drawn(result, tag)
    return one.x, one.y


def _top(result: fr.BuildResult) -> int:
    """The y of the page's topmost drawn symbol."""
    return min(s.y for drawing in drawn_pages(result.model).values() for s in drawing.symbols)


def _join(result: fr.BuildResult, start: Point, end: Point) -> list[Point]:
    """The corners of the drawn wires from `start` to `end`: wires meet end to end or at a dot."""
    wires = [
        list(w.points) for drawing in drawn_pages(result.model).values() for w in drawing.wires
    ]
    dots = {p for w in wires for p in w}
    edges: dict[Point, set[Point]] = {}
    for wire in wires:
        for a, b in pairwise(wire):
            on = sorted(
                p
                for p in dots
                if min(a, b) <= p <= max(a, b) and (p[0] == a[0] == b[0] or p[1] == a[1] == b[1])
            )
            for p, q in pairwise(on if a <= b else on[::-1]):
                edges.setdefault(p, set()).add(q)
                edges.setdefault(q, set()).add(p)
    came, queue = {start: start}, [start]
    for here in queue:
        for n in sorted(edges.get(here, ())):
            if n not in came:
                came[n] = here
                queue.append(n)
    assert end in came, f"no drawn wires join {start} to {end}"
    path = [end]
    while path[-1] != start:
        path.append(came[path[-1]])
    path.reverse()
    return [
        p
        for i, p in enumerate(path)
        if i in (0, len(path) - 1)
        or not (
            path[i - 1][0] == p[0] == path[i + 1][0] or path[i - 1][1] == p[1] == path[i + 1][1]
        )
    ]


_SHAPES = [
    pytest.param("low", False, id="host-lower-net"),
    pytest.param("up", False, id="host-upper-net"),
    pytest.param("box", False, id="one-pin-box-tail"),
    pytest.param("low", True, id="authored-bottom-up"),
    pytest.param("mcb", False, id="two-port-host-net-on-a-3p-breaker"),
]


def _host_pin(shape: str) -> str:
    """F2's pin the lamp hangs from."""
    return {"mcb": "1.out", "up": "in"}.get(shape, "out")


def _on_outline(a: Point, b: Point, box: tuple[int, int, int, int]) -> bool:
    """Whether the segment a-b lies along one of the box's four edges."""
    left, top, right, bottom = box
    flat = a[1] == b[1] and a[1] in (top, bottom) and min(a[0], b[0]) < right
    flat = flat and max(a[0], b[0]) > left
    tall = a[0] == b[0] and a[0] in (left, right) and min(a[1], b[1]) < bottom
    return flat or (tall and max(a[1], b[1]) > top)


@pytest.mark.parametrize(("shape", "bottom_up"), _SHAPES)
def test_a_beside_chain_joins_its_host_by_one_net(shape: str, *, bottom_up: bool) -> None:
    built = _build(shape, bottom_up=bottom_up)
    pin = _pin(built, "H1", "in")
    points = _join(built, pin, _pin(built, "F2", _host_pin(shape)))  # a marker pair draws none
    lamp, body = _drawn(built, "H1"), _shape(_drawn(built, "H1")).body
    box = (lamp.x + body.x, lamp.y + body.y, lamp.x + body.x + body.w, lamp.y + body.y + body.h)
    # The lamp is a box. A join meets a box pin perpendicular to the box edge: the run stays level
    # at the host's height, the box stands a grid or more lower, and a vertical drop enters its
    # top pin. A wire never runs along a symbol outline (JOIN-VERTICAL).
    walk = points
    assert walk[0] == pin, "the join ends on H1's pin 1"
    assert walk[1] == (pin[0], pin[1] - 8), "the last segment is a vertical drop of one grid"
    # a level run, then the host's pin: a 3-pole host's pin leaves by a grid, its own stub
    assert len(walk) == (4 if shape == "mcb" else 3), "a drop, a level run and the host's pin"
    assert walk[1][1] == walk[2][1], "the run is level"
    assert walk[-1][1] == walk[2][1] - (8 if shape == "mcb" else 0), "the run is at the host's pin"
    assert not any(_on_outline(p, q, box) for p, q in pairwise(points)), "no run on the outline"
    # The box's own pins turn to face the head once it stands lower, which can widen its column:
    # the host keeps its row below the page's top, and keeps its place along x whenever no box
    # stands left of it (a marker stood a grid out moves the whole page's top by that grid)
    flat = _build(shape, beside=False, bottom_up=bottom_up)
    plain, here = _at(flat, "F2"), _at(built, "F2")
    assert here[1] - _top(built) == plain[1] - _top(flat), "the host does not move"
    assert shape == "box" or here[0] == plain[0], "the host does not move"
    if shape != "box":  # a box tail stands in a column of its own
        assert _at(built, "H1")[1] < _at(built, "K1")[1], "the head stands on top"
