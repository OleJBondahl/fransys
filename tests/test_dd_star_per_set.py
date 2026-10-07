"""D9 across drawing sets: a branch is decided where a port stands, not once for the whole net.

A unit's boundary terminals stand twice: as pins in the top-level set and where their group
puts them in the unit's own set. The PE net here is three terminals, `-X1:1` (the hub) wired to
`-X3:1` and to `-X3:2`. In the top-level set the three pins stand in one row, so `-X1:1` and
`-X3:1` are side by side; in the unit's own set each terminal stands beside its group's relay,
so no two of them are. The wire counts as drawn between neighbours (C3) and the neighbour
takes no marker; but the pair is neighbours in one set only, and in the other `-X3:1` must
still show its branch. Where the terminals share a page (`fill` 1) M12 joins the same-side
pins by wires at any column distance, so the unit's set draws wires and no marker. Built
through the `fransys` facade from `examples/demo-parts`, read from `layout.*` records and
`marker_text`.

`_build` asserts no ERROR finding. The control (`-X1:2` beside the hub in both sets): a marker
is never added where a wire is drawn.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document

from fransys_model.derive.drawing_text import marker_text, reference_number
from fransys_model.kernel import Id, Severity
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    Route,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import ports

_PROJECT: dict[str, Any] = {
    "title": "Star per set",
    "number": "P-1008",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
# (strip, group) of each terminal, in author order; the first is the hub, wired to the others
_APART = (("X1", 1), ("X3", 2), ("X3", 3))  # the hub is beside -X3:1 in the top-level set only
_BESIDE = (("X1", 1), ("X1", 1), ("X3", 2))  # the hub is beside -X1:2 in both sets


def _build(spec: tuple[tuple[str, int], ...], *, fill: int):
    """A cabinet unit `+C1` with one boundary terminal per `spec` entry, the first wired to each
    other on the inner side (one PE net). Each terminal's outer side is wired to a relay coil of
    its group; `fill` relays stand in each group in all, so a group of 3 fills a page of its own.
    Returns the model and the terminals' inner ports, in `spec` order."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    groups = {n: cab.group(f"G{n}", f"Group {n}") for _, n in spec}
    strips = {name: cab.strip(name, at=c1) for name, _ in spec}
    terminals = [strips[name].terminal("DEMO-TB-2.5", group=groups[n]) for name, n in spec]
    earth, blue = cab.wiring(colour="GNYE", gauge="2.5"), cab.wiring(colour="BU", gauge="0.5")
    for other in terminals[1:]:
        earth(terminals[0].inner, other.inner)
    for terminal in terminals:
        cab.boundary(terminal)
    tag = 0
    for terminal, (_, n) in zip(terminals, spec, strict=True):
        for k in range(fill):
            tag += 1
            relay = cab.item("DEMO-RLY-2CO-24", tag=f"K{tag}", at=c1, group=groups[n])
            blue(relay.fn("coil")["A1"], relay.fn("coil")["A2"])
            # layout-0112: an unwired contact is not drawn, and the relays must fill the page
            blue(relay.fn("co_1")["11"], relay.fn("co_1")["14"])
            blue(relay.fn("co_2")["21"], relay.fn("co_2")["24"])
            if k == 0:
                blue(terminal.outer, relay.fn("coil")["A1"])
    result = fr.build(parts, d.draft(), layout_trigger_document())
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    return result.model, [terminal.inner.id for terminal in terminals]


def _stands(model, port: Id) -> dict[bool, SymbolPlacement]:
    """`port`'s function's placement by set: True is the unit's own set, False the top-level one."""
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    function = ports(model)[port].function
    found = {
        sets[pages[p.page].drawing_set].unit is not None: p
        for p in layout_of(model, SymbolPlacement).values()
        if p.function == function
    }
    assert set(found) == {True, False}  # one placement in each of the two sets
    return found


def _beside(model, a: Id, b: Id, *, own: bool) -> bool:
    """Whether `a` and `b` stand on one page of the set at one y with nothing between them."""
    pa, pb = _stands(model, a)[own], _stands(model, b)[own]
    if (pa.page, pa.y) != (pb.page, pb.y):
        return False
    low, high = sorted((pa.x, pb.x))
    return not [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.page == pa.page and low < p.x < high and p.function not in (pa.function, pb.function)
    ]


def _own_page(model, port: Id):
    return _stands(model, port)[True].page


def _star_markers(model, port: Id, kind: StarKind, page=None) -> list[LinkMarker]:
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.port == port and m.star is kind and (page is None or m.page == page)
    ]


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_a_port_apart_from_the_reference_in_the_unit_set_gets_a_branch_there(fill: int) -> None:
    """-X3:1 is beside the hub -X1:1 in the top-level set and apart in the unit's own set. On a
    page of its own (`fill` 3) it carries a branch marker there whose partner is the hub's
    reference marker. On the hub's page (`fill` 1) it stands in the same row, and M12 joins
    same-side pins by wires at any column distance: wires, no branch."""
    # UNDO: stages/references/nets.py, `branch_pages`: the return statement to
    #     `return []` (no set takes a branch): FAILED on `len(branches)` (other-page)
    # UNDO (same-page): stages/references/joins.py `joined_runs`: join only ports of adjacent
    #     columns (the PE net is a star again: markers, no routes)
    model, (hub, near, far) = _build(_APART, fill=fill)
    assert _beside(model, hub, near, own=False)  # side by side in the top-level set
    assert not _beside(model, hub, near, own=True)  # and apart in the unit's own set
    if fill == 1:
        _joined_by_wires(model, hub, near, far)
        return
    assert _own_page(model, hub) != _own_page(model, near)
    markers = layout_of(model, LinkMarker)
    branches = _star_markers(model, near, StarKind.BRANCH, _own_page(model, near))
    assert len(branches) == 1, "-X3:1 stands apart from -X1:1 in the unit's set and shows no branch"
    ref = markers[branches[0].partner]
    assert ref.port == hub
    assert ref.star is StarKind.REF


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_the_reference_in_the_unit_set_lists_the_branch_of_the_port_apart_from_it(
    fill: int,
) -> None:
    """The hub's reference marker in the unit's own set lists -X3:1 and -X3:2, one line for each
    branch marker that names them (M3: the box may share lines of other nets at that pin, so
    only the lines of this net's own number are counted). On one page (`fill` 1) M12 draws
    wires and the net has no reference to list."""
    # UNDO: `branch_pages` returns `[]` (other-page); same-page as in the first test
    model, (hub, near, far) = _build(_APART, fill=fill)
    if fill == 1:
        _joined_by_wires(model, hub, near, far)
        return
    markers = layout_of(model, LinkMarker)
    own = _own_page(model, hub)
    refs = [
        m for m in _star_markers(model, hub, StarKind.REF) if m.page in {own, _own_page(model, far)}
    ]
    assert refs
    branches = [
        m
        for m in markers.values()
        if m.star is StarKind.BRANCH and m.partner in {r.id for r in refs}
    ]
    assert {m.port for m in branches} == {near, far}, "the reference does not list -X3:1"
    own_lines = [
        line
        for r in refs
        for line in marker_text(model, r).split("\n")
        if line.startswith(f"#{reference_number(model, r)}-")
    ]
    assert len(own_lines) == len(branches) == 2


def _on_top_set(model, marker: LinkMarker) -> bool:
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    return sets[pages[marker.page].drawing_set].unit is None


def _joined_by_wires(model, hub: Id, near: Id, far: Id) -> None:
    """S20 M12: terminals standing on one page of the unit's set, apart as they are, are joined by
    wires at any column distance (the pins face the same side), so the net takes no marker."""
    own = _own_page(model, hub)
    assert _own_page(model, near) == _own_page(model, far) == own
    routes = {frozenset((r.a, r.b)) for r in layout_of(model, Route).values() if r.page == own}
    assert {frozenset((hub, near)), frozenset((hub, far))} <= routes
    assert not [m for m in layout_of(model, LinkMarker).values() if m.port in {hub, near, far}]


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_in_the_top_level_set_the_pair_stands_beside_and_takes_no_branch(fill: int) -> None:
    """In the top-level set the hub, `near` and `far` stand in one row and the hub is beside
    `near`, so a wire joins them and `near` takes no branch marker there; its branch stands in
    the unit's own set and names the hub's reference marker on the hub's own page (an own-set
    placement of the reference, never the top-level pin). On one page (`fill` 1) M12 joins the
    three by wires in the unit's set, so there is no branch anywhere."""
    # UNDO: stages/references/nets.py, `branch_pages`: the return
    #     statement to `return []`: FAILED on `(branch,) = ...` (other-page); same-page as in
    #     the first test
    model, (hub, near, far) = _build(_APART, fill=fill)
    row = {_stands(model, port)[False] for port in (hub, near, far)}
    assert len({(p.page, p.y) for p in row}) == 1  # one row of one top-level page
    assert _beside(model, hub, near, own=False)
    markers = layout_of(model, LinkMarker)
    assert not [m for m in _star_markers(model, near, StarKind.BRANCH) if _on_top_set(model, m)]
    if fill == 1:
        _joined_by_wires(model, hub, near, far)
        assert not _star_markers(model, near, StarKind.BRANCH)
        return
    (branch,) = _star_markers(model, near, StarKind.BRANCH)
    ref = markers[branch.partner]
    assert ref.star is StarKind.REF
    assert ref.page == _own_page(model, hub)
    assert not _on_top_set(model, ref)


def test_control_a_pair_beside_each_other_in_both_sets_gets_no_marker_pair() -> None:
    """C3: -X1:2 is beside the hub in both sets and joined to it by a wire: it takes no marker,
    and the reference lists -X3:1 alone, the one port that stands apart from the hub in both
    sets (its marker stands in the unit's own set: the top-level set shows the unit's pins only,
    no star marker). Must pass on the base and after the fix."""
    # UNDO: stages/references/nets.py, `_net_star`: `kept = []` (no wire
    #     counts as drawn): -X1:2 then takes a branch marker and its wire is
    #     dropped
    model, (hub, beside, apart) = _build(_BESIDE, fill=1)
    assert _beside(model, hub, beside, own=True)
    assert _beside(model, hub, beside, own=False)
    assert not _beside(model, hub, apart, own=True)
    assert not _beside(model, hub, apart, own=False)
    assert not _star_markers(model, beside, StarKind.BRANCH)
    assert not _star_markers(model, beside, StarKind.REF)
    assert any({r.a, r.b} == {hub, beside} for r in layout_of(model, Route).values())
    assert len(_star_markers(model, apart, StarKind.BRANCH)) == 1
    refs = _star_markers(model, hub, StarKind.REF)
    assert [len(marker_text(model, r).split()) for r in refs] == [1]
