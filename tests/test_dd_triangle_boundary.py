"""DD-TRIANGLE (layout-0075): three boundary terminals wired pairwise, one star net of three, must
build ("the records put name one id twice, with different content" before the fix).

A unit's strip `X1` holds three terminals `t1`, `t2`, `t3`, each declared `boundary`, wired
t1-t2, t1-t3, t2-t3: one net of three ports. Each terminal is drawn in the unit's own
drawing set and, as a boundary replica, in the top-level set. The engine re-keys the hub columns of
the triangle, so the unit's home columns were counted as replicas too and one placement key stood
twice. The chain (wired 1-2 and 2-3 only) and the same triangle with no unit are the controls.

Built through the `fransys` facade from `examples/demo-parts`; read from the core path's Drawings.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _dd_core_c import in_own_set, stands, tags_by_set
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity

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
    return fr.build(parts, d.draft(), layout_trigger_document())


_TAGS = ("-X1:1", "-X1:2", "-X1:3")  # the three terminals of `X1`, in terminal order


def _assert_once_per_set(model, *, in_unit: bool) -> None:
    """Every terminal's symbol and its tag text stand once in each drawing set that draws it, the
    symbols under an id of their own. With `in_unit` those are two sets: the unit's own and the
    top-level one; without, the top-level one only."""
    want = {True, False} if in_unit else {False}
    for tag in _TAGS:
        spots = stands(model, tag)
        assert set(spots) == want
        assert tags_by_set(model, tag) == dict.fromkeys(want, 1)
        assert all(len(found) == 1 for found in spots.values())
        ids = [symbol.id for found in spots.values() for _, symbol in found]
        assert len(set(ids)) == len(ids)


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
    wires = {True: 0, False: 0}
    for page, drawing in drawn_pages(model).items():
        wires[in_own_set(model, page)] += len(drawing.wires)
        assert drawing.markers == ()
    assert wires[False] == 0
    assert wires[True] == 3


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
