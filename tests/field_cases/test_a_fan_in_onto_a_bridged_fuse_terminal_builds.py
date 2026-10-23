"""Field case: two terminals of one strip wired to the outer side of a bridged fuse terminal.

The engineering shape: a cabinet unit with an interface strip X1 of fused terminals (the fuse
sits between the two connections, a `protective` link), a run of 6 on it bridged and made outside
every block, a declared DC supply in block V wired to run terminal 2, and in block G two terminals
of another interface strip X2 wired to the outer side of run terminal 6.

The bug: `fr.build` raised `KeyError` in `fransys_layout` `host_offsets._attach_at_host`. The
fused terminal's own cell was on no page of the set, but the X2 cells hung on it named it as their
host, and layout looked the host up on the page and did not find it. Dropping any one of the
fused link, `bridged`, the supply, `interface`, or the second X2 terminal made it build.

A second bug, in the same case: the wire from a flipped (turned 180 degrees) fuse terminal to the
terminals hung on it left upward and U-turned down, because the attachment read the host port's
facing from the unflipped geometry. The fix, FAN-IN-UTURN, has the attachment read the port
as drawn.

Reported by a consumer, reproduced 2026-10-14. Fixing decision: model-0215 -- a terminal with a
protective link is not a rail terminal, so it draws as a terminal and keeps its home cell.
"""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.layout import DrawingSet, Page, layout_of

Pt = tuple[int, int]

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_layout.drawing import Drawing, DrawnSymbol


class _Cab(NamedTuple):
    """A unit with no boundary device to hand back."""


@fr.unit(
    "cab",
    revision=1,
    interface_version=1,
    date="2026-10-14",
    text="First issue",
    by="XX",
    title="Cabinet",
    number="C-1",
)
def _cab(c):
    x2 = c.terminal_strip("X2", "DEMO-TB-2.5", 4, interface=True)
    run = c.terminal_strip("X1", "DEMO-TB-FUSE-2.5", interface=True).run("24V", 6, bridged=True)
    with c.function("V", "Supply"):
        psu = c.device("G1", "DEMO-PSU-24")
        c.detail.wire(psu.output["+"], run[2], wire=(BU, 0.75))
        c.dc_supply("24VDC", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    with c.function("G", "Group"):
        for k in (1, 2):
            c.detail.wire(x2[k], run[6].outer, wire=(BU, 0.75))
    return _Cab()


def test_a_fan_in_onto_a_bridged_fuse_terminal_builds(tmp_path: Path) -> None:
    (tmp_path / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    result = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=tmp_path / "cover.md")
    )
    assert result.model is not None


def _turns_back(points: list[tuple[int, int]]) -> bool:
    """True when two segments one apart run opposite ways on one axis (a U, up then down)."""
    steps = [(bx - ax, by - ay) for (ax, ay), (bx, by) in pairwise(points)]
    for first, third in zip(steps, steps[2:], strict=False):
        opposite = (first[0] * third[0] < 0 and first[1] == third[1] == 0) or (
            first[1] * third[1] < 0 and first[0] == third[0] == 0
        )
        if opposite:
            return True
    return False


def _paths(drawing: Drawing, start: DrawnSymbol, ends: list[DrawnSymbol]) -> list[list[Pt]]:
    """The vertex path of drawn wires from `start`'s pin to each of `ends`' pins.

    Wire vertices are the nodes; a junction dot on a segment splits it, so wires that join there
    join in the graph.
    """
    dots = {(s.x, s.y) for s in drawing.symbols if s.key == "junction-dot"}
    graph: dict[Pt, set[Pt]] = defaultdict(set)
    for wire in drawing.wires:
        for a, b in pairwise(wire.points):
            cut = sorted(
                [a, b, *(d for d in dots if _between(d, a, b))],
                key=lambda p: abs(p[0] - a[0]) + abs(p[1] - a[1]),
            )
            for u, v in pairwise(cut):
                graph[u].add(v)
                graph[v].add(u)

    def pin(s: DrawnSymbol) -> Pt:
        return min((p for p in graph if p[0] == s.x), key=lambda p: abs(p[1] - s.y))

    def walk(here: Pt, goal: Pt, seen: tuple[Pt, ...]) -> list[Pt] | None:
        if here == goal:
            return [*seen, here]
        for nxt in sorted(graph[here] - set(seen)):
            found = walk(nxt, goal, (*seen, here))
            if found:
                return found
        return None

    return [p for end in ends if (p := walk(pin(start), pin(end), ()))]


def _between(p: Pt, a: Pt, b: Pt) -> bool:
    """Whether `p` lies strictly inside the straight segment a-b."""
    on_line = (p[0] - a[0]) * (b[1] - a[1]) == (p[1] - a[1]) * (b[0] - a[0])
    return (
        on_line
        and p not in (a, b)
        and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    )


def _terminal(drawing: Drawing, tag: str) -> DrawnSymbol:
    """The terminal whose own tag text `-tag` stands nearest to it."""
    (text,) = (t for t in drawing.texts if t.text.endswith(tag))
    return min(
        (s for s in drawing.symbols if s.key == "terminal"),
        key=lambda s: abs(s.x - text.box.x) + abs(s.y - text.box.y),
    )


def test_the_wire_from_the_fuse_terminal_reaches_the_fan_in_without_a_u_turn(
    tmp_path: Path,
) -> None:
    (tmp_path / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=tmp_path / "cover.md")
    ).model
    (page,) = (
        p for p in drawn_pages(model).values() if any(t.text.endswith("X1:24V:6") for t in p.texts)
    )
    ends = [_terminal(page, "X2:1"), _terminal(page, "X2:2")]
    routes = _paths(page, _terminal(page, "X1:24V:6"), ends)
    assert len(routes) == 2  # one per X2 terminal
    assert not any(_turns_back(r) for r in routes)


def test_the_top_level_set_draws_no_terminal_that_no_wire_meets(tmp_path: Path) -> None:
    """Decision layout-0216: no terminal stands as a box cell on a top-level page with no route,
    marker or power symbol of that page at its ports (today U1/X1:24V:6, U1/X2:1 and U1/X2:2)."""
    (tmp_path / "cover.md").write_text("# Cabinet\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=tmp_path / "cover.md")
    ).model
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    loose = []
    for pid, drawing in drawn_pages(model).items():
        if sets[pages[pid].drawing_set].unit is not None:
            continue
        met = {x for w in drawing.wires for x, _ in w.points}
        met |= {s.x for s in drawing.symbols if s.key != "terminal"}
        loose += [(s.x, s.y) for s in drawing.symbols if s.key == "terminal" and s.x not in met]
    assert loose == []
