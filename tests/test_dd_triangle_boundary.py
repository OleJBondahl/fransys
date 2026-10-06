"""DD-TRIANGLE (layout-0075): three boundary terminals wired pairwise, one star net of three, must
build ("the records put name one id twice, with different content" before the fix).

A unit's strip `X1` holds three terminals `t1`, `t2`, `t3`, each declared `boundary`, wired
t1-t2, t1-t3, t2-t3: one net of three ports (spec D9). Each terminal is drawn in the unit's own
drawing set and, as a boundary replica, in the top-level set. The engine re-keys the hub columns of
the triangle, so the unit's home columns were counted as replicas too and one placement key stood
twice. The chain (wired 1-2 and 2-3 only) and the same triangle with no unit are the controls.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from collections import defaultdict
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.kernel import Id, Severity
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    LinkMarker,
    Page,
    Route,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Triangle of boundary terminals",
    "number": "P-1007",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}

_TRIANGLE = ((0, 1), (0, 2), (1, 2))
_CHAIN = ((0, 1), (1, 2))


def _build(wired: tuple[tuple[int, int], ...], *, unit: bool = True):
    """A strip `X1` of three DEMO-TB-2.5 terminals wired pairwise `inner`-`inner` per `wired`
    (indexes into the three terminals), in a unit with every terminal a boundary (`unit`) or at
    the top level with no unit and no boundary. Returns the build result."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    if unit:
        scope = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
        scope.revision(1, date="2026-01-01", text="First release", created="XX")
    else:
        scope = d
    strip = scope.strip("X1", at=scope.location("C1", "Cabinet"))
    group = d.group("PLC", "PLC")
    terminals = [strip.terminal("DEMO-TB-2.5", group=group) for _ in range(3)]
    if unit:
        for terminal in terminals:
            scope.boundary(terminal)
    wire = d.wiring(colour="BU", gauge="0.5")
    for one, other in wired:
        wire(terminals[one].inner, terminals[other].inner)
    return fr.build(parts, d.draft(), system_document())


def _terminals(model) -> list[Id]:
    """The ids of the three terminal functions of `X1`, in terminal order."""
    found = sorted(
        (f.key, f.id)
        for f in functions(model).values()
        if "X1" in f.key[:2] and f.key[-2:] == ("fn", "terminal")
    )
    assert len(found) == 3
    return [fid for _, fid in found]


def _unit_of_page(model, page: Id[Page]) -> Id | None:
    """The unit whose drawing set `page` belongs to, `None` for the top-level set."""
    sets = layout_of(model, DrawingSet)
    return sets[layout_of(model, Page)[page].drawing_set].unit


def _by_set(model, records, subject) -> dict:
    """`records` (with `.page`) grouped by `subject(record)`, then by the unit of their drawing
    set (`None`: the top-level set)."""
    grouped: dict = defaultdict(lambda: defaultdict(list))
    for record in records:
        grouped[subject(record)][_unit_of_page(model, record.page)].append(record)
    return grouped


def _assert_once_per_set(model, *, in_unit: bool) -> None:
    """Every terminal's placement, and each of its tag labels (a label's `slot` names which one:
    `tag`, `tag.point`, `tag.strip`; the outline title is no terminal's), stands once in each
    drawing set that draws it, each record under an id and a key of its own. With `in_unit` those
    are two sets: the unit's own and the top-level one; without, the top-level one only."""
    terminals = set(_terminals(model))
    placed = _by_set(
        model,
        [p for p in layout_of(model, SymbolPlacement).values() if p.function in terminals],
        lambda p: p.function,
    )
    tagged = _by_set(
        model,
        [
            label
            for label in layout_of(model, Label).values()
            if label.kind is LabelKind.TAG
            and label.slot != "outline_title"
            and label.function in terminals
        ],
        lambda label: (label.function, label.slot),
    )
    assert len(placed) == 3
    assert {function for function, _ in tagged} == terminals
    for by_unit in (*placed.values(), *tagged.values()):
        assert (len(by_unit) == 2 and None in by_unit) if in_unit else set(by_unit) == {None}
        assert all(len(records) == 1 for records in by_unit.values())
        records = [record for group in by_unit.values() for record in group]
        assert len({r.id for r in records}) == len({r.key for r in records}) == len(records)


def test_triangle_of_boundary_terminals_builds() -> None:
    """The triangle builds through the facade: no exception, no ERROR finding."""
    # UNDO: engines/schematic/engine.py: stage_results, after `... = _arranged(...)` insert
    #     `replicas = frozenset(c.key for c in columns) - frozenset(c.key for c in all_columns)`
    #     (the base's inline set difference, which the hub re-key defeats; the tuple returns stay)
    result = _build(_TRIANGLE)
    assert not [f for f in result.findings if f.severity is Severity.ERROR]


def test_each_terminal_is_drawn_once_per_drawing_set() -> None:
    """t1, t2 and t3 each stand once in the unit's drawing set and once in the top-level one,
    the second the replica with an id and a key of its own; the same for their TAG labels."""
    # UNDO: as in test_triangle_of_boundary_terminals_builds
    model = _build(_TRIANGLE).model
    _assert_once_per_set(model, in_unit=True)


def test_markers_of_the_star_net_follow_d9_in_each_set() -> None:
    """D9: the net of three is drawn as wires where it is wired, so it has no marker anywhere.
    In the unit's set: three conductor routes and no marker on a terminal port. In the top-level
    set: no route and no marker (the conductors are the unit's; a black box's pin has no star
    marker)."""
    # UNDO: as in test_triangle_of_boundary_terminals_builds
    model = _build(_TRIANGLE).model
    terminals = set(_terminals(model))
    routes = defaultdict(list)
    for route in layout_of(model, Route).values():
        assert route.conductor is not None
        assert {ports(model)[p].function for p in (route.a, route.b)} <= terminals
        routes[_unit_of_page(model, route.page)].append(route)
    markers = [
        m
        for m in layout_of(model, LinkMarker).values()
        if ports(model)[m.port].function in terminals
    ]
    assert markers == []
    assert None not in routes
    assert [len(unit_routes) for unit_routes in routes.values()] == [3]


def test_chain_of_boundary_terminals_still_builds() -> None:
    """Control: wired 1-2 and 2-3 only, it builds and each terminal stands once per set."""
    # No UNDO: a control. A chain has no hub column: it passes on the base and under the undo.
    result = _build(_CHAIN)
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    _assert_once_per_set(result.model, in_unit=True)


def test_triangle_without_a_unit_still_builds() -> None:
    """Control: the same terminals and wires with no unit and no boundary: one drawing set, one
    placement per terminal."""
    # No UNDO: a control. With no unit there is no replica column: it passes on the base and
    #     under the undo.
    result = _build(_TRIANGLE, unit=False)
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    _assert_once_per_set(result.model, in_unit=False)
