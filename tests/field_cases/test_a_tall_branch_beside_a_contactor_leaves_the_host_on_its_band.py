"""Field case: a branch taller than its host leaves the host where it stands.

The engineering shape: a unit holds a two-rail DC path (strip, 2-pole switch, fuse, contactor
pole, strip per rail), an interface switch beside it, and on the first rail a precharge branch
(resistor, contactor pole, fuse) that leaves the first fuse's output and rejoins at the first
contactor's output, stood beside it (`beside=`, decision layout-0174). The branch has three
elements against the contactor's one.

The bug: the branch's lower end stood deeper than the host's pin, so the alignment lowered the
host to it. The first contactor left the second rail's contactor band, and the page overflowed
(PAGE_OVERFULL on the foot strip). Fixed by layout-0174's amendment of 2026-10-11: the host
stays on its band, the first join is level, and the join the branch is too tall for runs as an L.
The interface switch is declared `unused=True`, so its spare pins draw nothing and the DC function
fits one sheet.
"""

import re
import tempfile
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr

from electrical_symbols import LIBRARY
from fransys_layout.symbols import library_symbol, symbol_shape
from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnSymbol

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}
_RED, _BLACK = ("RD", 50), ("BK", 50)


class _Strips(NamedTuple):
    X1: Any


@fr.unit("demo-dc", **_UNIT)
def _dc(d: Any) -> _Strips:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 2, interface=True)
    d.device("SW1", "DEMO-SW-8P", interface=True, unused=True)
    with d.function("DC", "DC path"):
        s1 = d.device("S1", "DEMO-MCB-2P")
        f1, f2, f3 = (d.device(n, "DEMO-FUSE-DC-160") for n in ("F1", "F2", "F3"))
        k1, k2, k3 = (d.device(n, "DEMO-CTR-3P-24") for n in ("K1", "K2", "K3"))
        r1 = d.device("R1", "DEMO-LAMP-24")
        for a, b, wire in (
            (x1[1], s1.pole_1["1"], _RED),
            (s1.pole_1["2"], f1.element["1"], _RED),
            (f1.element["2"], k1.main["1"], _RED),
            (k1.main["2"], x2[1], _RED),
            (x1[2], s1.pole_2["3"], _BLACK),
            (s1.pole_2["4"], f2.element["1"], _BLACK),
            (f2.element["2"], k2.main["1"], _BLACK),
            (k2.main["2"], x2[2], _BLACK),
            (k1.main["2"], r1["1"], _RED),
            (r1["2"], k3.main["1"], _RED),
            (k3.main["2"], f3.element["1"], _RED),
            (f3.element["2"], f1.element["2"], _RED),
        ):
            d.detail.wire(a, b, wire=wire)
    d.layout.chain(x1[1], s1.pole_1, f1.element, k1.main, x2[1])
    d.layout.chain(x1[2], s1.pole_2, f2.element, k2.main, x2[2])
    d.layout.chain(r1.lamp, k3.main, f3.element, beside=k1.main)
    return _Strips(x1)


def _build() -> tuple[fr.BuildResult, str]:
    d = fr.design("demo_parts")
    d.add(_dc, "U1")
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-dc", cover=root / "c.md")
    result = fr.build(d, cover)
    fr.write(result, root / "out", intermediates=root / "inter")
    pages = [svg.read_text("utf-8") for svg in sorted((root / "inter").glob("layout.page-*.svg"))]
    (dc_page,) = (page for page in pages if "-R1" in page and "-K1" in page)
    return result, dc_page


_RESULT, _DC_PAGE = _build()

type Point = tuple[int, int]


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def _drawn(tag: str) -> DrawnSymbol:
    """The one drawn symbol of the item `tag` (the owner text starts with it)."""
    (one,) = (r for r in _gap(_RESULT.model, "symbol subject") if (r.owner or "").startswith(tag))
    return one


def _shape(one: DrawnSymbol):  # the symbol's pins and body at R0, from symdef's data
    return symbol_shape(library_symbol(LIBRARY, one.key, one.poles), LIBRARY)


def _pin(tag: str, pin: str) -> Point:
    one = _drawn(tag)
    turn = _shape(one).pins[pin]
    return one.x + turn.dx, one.y + turn.dy


def _join(start: Point, end: Point) -> list[Point]:
    """The corners of the drawn wires from `start` to `end`: wires meet end to end or at a dot."""
    wires = [list(w.points) for d in _RESULT.drawings.values() for w in d.wires]
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


def test_the_page_is_not_overfull_and_draws_no_marker() -> None:
    assert "PAGE_OVERFULL" not in {f.code for f in _RESULT.findings}
    assert re.findall(r">(#\d+-[0-9A-Z]+)</text>", _DC_PAGE) == []


def test_the_host_contactor_stays_on_the_band_of_the_other_contactors() -> None:
    rows = {name: _drawn(f"U1-{name}").y for name in ("K1", "K2", "K3")}
    assert rows["K1"] == rows["K2"] == rows["K3"], rows


def test_the_first_join_is_level() -> None:
    points = _join(_pin("U1-F3", "out"), _pin("U1-F1", "out"))
    assert len(points) == 2
    assert points[0][1] == points[1][1]


def test_the_taller_branchs_other_join_runs_as_an_l_clear_of_the_host() -> None:
    points = _join(_pin("U1-K1", "1.out"), _pin("U1-R1", "in"))
    assert len(points) >= 3
    host = _drawn("U1-K1")
    body = _shape(host).body  # the keep-out: the body, which reaches the pin ends
    left, top = host.x + body.x, host.y + body.y
    right, bottom = left + body.w, top + body.h
    pin = points[0]
    for (ax, ay), (bx, by) in pairwise(points):
        x0, x1 = max(min(ax, bx), left), min(max(ax, bx), right)
        y0, y1 = max(min(ay, by), top), min(max(ay, by), bottom)
        meets = x0 <= x1 and y0 <= y1
        assert not meets or (x0, y0, x1, y1) == (*pin, *pin)


def test_the_dc_function_fits_one_sheet_of_the_unit() -> None:
    """Everything of the unit stands on one page, the first."""
    pages = {p for p, d in _RESULT.drawings.items() if d.symbols}
    assert [layout_of(_RESULT.model, Page)[p].number for p in pages] == [1]
