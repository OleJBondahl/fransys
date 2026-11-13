"""Helpers that several field cases and tests share: units, line crossings, wire ends, drawn joins."""

import re
from functools import cache
from itertools import combinations, pairwise
from typing import TYPE_CHECKING, Any
lazy from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from board_cab import Open

from electrical_symbols import LIBRARY
from fransys_layout import DiagramLine, lay_out_diagrams
from fransys_layout.symbols import library_symbol, symbol_shape
from fransys_model import derive
from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from _drawn_facts import Placed

type Point = tuple[int, int]


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def relay_cab(u: Any) -> Open:
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    k2 = u.device("K2", "DEMO-RLY-2CO-24")
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, k1.coil["A1"], k2.coil["A1"])
    cable.core(2, k1.coil["A2"], k2.coil["A2"])
    return Open()


@cache
def relay_cab_with_cable_list() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.location("CAB", "Cabinet")
    d.add(relay_cab, "U1", place="CAB")
    return fr.build(d, unit_document("demo-cab"))


def unit_texts(model: Any, root: Path, name: str) -> list[str]:
    """Every text of the pages drawn for the unit released as `name`, read from the intermediates under `root`."""
    names = {derive.unit_release(model, u).name: u for u in derive.units(model)}
    sets = layout_of(model, DrawingSet)
    found: list[str] = []
    for page in layout_of(model, Page).values():
        if sets[page.drawing_set].unit == names[name]:
            svg = (root / "inter" / f"layout.page-{page.id.value}.svg").read_text("utf-8")
            found += re.findall(r">([^<>]+)</text>", svg)
    return found


def crossed(p: Point, q: Point, r: Point, s: Point) -> bool:
    """Whether segments pq and rs cross at a point inside both."""

    def side(a: Point, b: Point, c: Point) -> int:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    return side(p, q, r) * side(p, q, s) < 0 and side(r, s, p) * side(r, s, q) < 0


def diagram_lines(result: fr.BuildResult) -> tuple[DiagramLine, ...]:
    diagrams, _ = lay_out_diagrams(result.model, LIBRARY)
    return tuple(line for d in diagrams.diagrams for sheet in d.sheets for line in sheet.lines)


def crossings(result: fr.BuildResult) -> int:
    runs = [[((a.x, a.y), (b.x, b.y)) for a, b in zip(line.points, line.points[1:], strict=False)] for line in diagram_lines(result)]
    return sum(crossed(*one, *other) for first, second in combinations(runs, 2) for one in first for other in second)


def wire_ends(d: Any) -> set[frozenset[str]]:
    return {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(fr.build(d).model)}


def shape(one: Placed):  # the symbol's pins and body at R0, from symdef's data
    return symbol_shape(library_symbol(LIBRARY, one.key, one.poles), LIBRARY)


def pin_at(one: Placed, pin: str) -> Point:
    turn = shape(one).pins[pin]
    return int(one.x + turn.dx), int(one.y + turn.dy)


def join(result: fr.BuildResult, start: Point, end: Point) -> list[Point]:
    """The corners of the drawn wires from `start` to `end`: wires meet end to end or at a dot."""
    wires = [list(w.points) for d in drawn_pages(result.model).values() for w in d.wires]
    dots = {p for w in wires for p in w}
    edges: dict[Point, set[Point]] = {}
    for wire in wires:
        for a, b in pairwise(wire):
            on = sorted(p for p in dots if min(a, b) <= p <= max(a, b) and (p[0] == a[0] == b[0] or p[1] == a[1] == b[1]))
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
        if i in (0, len(path) - 1) or not (path[i - 1][0] == p[0] == path[i + 1][0] or path[i - 1][1] == p[1] == path[i + 1][1])
    ]
