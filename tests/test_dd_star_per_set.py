"""Across drawing sets: a branch is decided where a port stands, not once for the whole net.

A unit's boundary terminals stand twice: as pins in the top-level set and where their group
puts them in the unit's own set. The PE net here is three terminals, `-X1:1` (the hub) wired to
`-X3:1` and to `-X3:2`. In the top-level set the three pins stand in one row, so `-X1:1` and
`-X3:1` are side by side; in the unit's own set each terminal stands beside its group's relay,
so no two of them are. The wire counts as drawn between neighbours and the neighbour
takes no marker; but the pair is neighbours in one set only, and in the other `-X3:1` must
still show its branch. Where the terminals share a page (`fill` 1) same-side pins are joined
by wires at any column distance, so the unit's set draws wires and no marker. Built
through the `fransys` facade from `examples/demo-parts`, read from the core path's Drawings
(a terminal by the TAG text it prints, see `_dd_core_c`).

`_build` asserts no ERROR finding. The control (`-X1:2` beside the hub in both sets): a marker
is never added where a wire is drawn.
"""

from itertools import pairwise
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _dd_core_c import beside, in_own_set, markers_of, stands
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity

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
    Returns the model and the terminals' printed tags, in `spec` order."""
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
            # layout-0112: an unwired contact is not drawn, and the relays must fill the page;
            # layout-0175: on one page (`fill` 1) the contacts would push the ink past the box
            if fill > 1:
                blue(relay.fn("co_1")["11"], relay.fn("co_1")["14"])
                blue(relay.fn("co_2")["21"], relay.fn("co_2")["24"])
            if k == 0:
                blue(terminal.outer, relay.fn("coil")["A1"])
    result = fr.build(parts, d.draft(), layout_trigger_document())
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    seen: dict[str, int] = {}
    tags = []
    for name, _ in spec:
        seen[name] = seen.get(name, 0) + 1
        tags.append(f"-{name}:{seen[name]}")
    return result.model, tags


def _stands(model, tag: str) -> dict:
    """`tag`'s terminal by set: True is the unit's own set, False the top-level one."""
    found = {own: [spot] for own, spots in stands(model, tag).items() for spot in spots}
    assert set(found) == {True, False}  # one placement in each of the two sets
    return {own: spot[0] for own, spot in found.items()}


def _beside(model, a: str, b: str, *, own: bool) -> bool:
    """Whether `a` and `b` stand on one page of the set at one y with nothing between them."""
    return beside(model, _stands(model, a)[own], _stands(model, b)[own])


def _own_page(model, tag: str):
    return _stands(model, tag)[True][0]


def _star_markers(model, tag: str, kind: str, page=None) -> list:
    """The markers of library key `kind` printing `tag`, on `page` when given."""
    return markers_of(model, tag, kind, page)


def _on(point, a, b) -> bool:
    """Whether `point` lies on the straight segment a-b."""
    (x, y), (x0, y0), (x1, y1) = point, a, b
    return min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1)


def _joined(model, page, a, b) -> bool:
    """Whether the pin (8 G above its terminal symbol) of `a` and of `b` lie on one run of wires
    of `page`: wires that touch share a run."""
    wires = [w.points for w in drawn_pages(model)[page].wires]
    runs: list[set[int]] = []
    for i, points in enumerate(wires):
        touching = [
            run
            for run in runs
            if any(
                _on(p, q0, q1) or _on(q0, *pair) or _on(q1, *pair)
                for j in run
                for pair in pairwise(points)
                for p in wires[j]
                for q0, q1 in zip(wires[j], wires[j][1:], strict=False)
            )
        ]
        merged = {i}.union(*touching)
        runs = [run for run in runs if run not in touching] + [merged]
    pins = [(s.x, s.y - 8) for s in (a, b)]
    return any(
        all(
            any(_on(pin, *seg) for j in run for seg in zip(wires[j], wires[j][1:], strict=False))
            for pin in pins
        )
        for run in runs
    )


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_a_port_apart_from_the_reference_in_the_unit_set_gets_a_branch_there(fill: int) -> None:
    """-X3:1 is beside the hub -X1:1 in the top-level set and apart in the unit's own set. On a
    page of its own (`fill` 3) it carries a branch marker there whose partner is the hub's
    reference marker. On the hub's page (`fill` 1) it stands in the same row, and same-side pins
    are joined by wires at any column distance: wires, no branch."""
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
    branches = _star_markers(model, near, "branch", _own_page(model, near))
    assert len(branches) == 1, "-X3:1 stands apart from -X1:1 in the unit's set and shows no branch"
    assert _star_markers(model, hub, "ref", _own_page(model, hub))


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_the_reference_in_the_unit_set_lists_the_branch_of_the_port_apart_from_it(
    fill: int,
) -> None:
    """The hub's reference marker in the unit's own set lists -X3:1 and -X3:2, one line for each
    branch marker that names them (the box may share lines of other nets at that pin, so
    only the lines of this net's own number are counted). On one page (`fill` 1) same-side pins are
    joined by wires and the net has no reference to list."""
    # UNDO: `branch_pages` returns `[]` (other-page); same-page as in the first test
    model, (hub, near, far) = _build(_APART, fill=fill)
    if fill == 1:
        _joined_by_wires(model, hub, near, far)
        return
    own = _own_page(model, hub)
    refs = [
        (p, m) for p, m in _star_markers(model, hub, "ref") if p in {own, _own_page(model, far)}
    ]
    assert refs
    branches = [(p, m) for tag in (near, far) for p, m in _star_markers(model, tag, "branch")]
    assert {tag for tag in (near, far) if _star_markers(model, tag, "branch")} == {near, far}, (
        "the reference does not list -X3:1"
    )
    own_lines = [
        line
        for _, r in refs
        for _, value in r.texts
        for line in value.split("\n")
        if line.startswith("#")
    ]
    assert len(own_lines) == len(branches) == 2


def _joined_by_wires(model, hub: str, near: str, far: str) -> None:
    """Terminals standing on one page of the unit's set, apart as they are, are joined by
    wires at any column distance (the pins face the same side), so the net takes no marker."""
    own = _own_page(model, hub)
    assert _own_page(model, near) == _own_page(model, far) == own
    symbols = {tag: _stands(model, tag)[True][1] for tag in (hub, near, far)}
    assert _joined(model, own, symbols[hub], symbols[near])
    assert _joined(model, own, symbols[hub], symbols[far])
    assert not [m for tag in (hub, near, far) for m in _star_markers(model, tag, "")]


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_in_the_top_level_set_the_pair_stands_beside_and_takes_no_branch(fill: int) -> None:
    """In the top-level set the hub, `near` and `far` stand in one row and the hub is beside
    `near`, so a wire joins them and `near` takes no branch marker there; its branch stands in
    the unit's own set and names the hub's reference marker on the hub's own page (an own-set
    placement of the reference, never the top-level pin). On one page (`fill` 1) the
    three are joined by wires in the unit's set, so there is no branch anywhere."""
    # UNDO: stages/references/nets.py, `branch_pages`: the return
    #     statement to `return []`: FAILED on `(branch,) = ...` (other-page); same-page as in
    #     the first test
    model, (hub, near, far) = _build(_APART, fill=fill)
    row = {_stands(model, tag)[False] for tag in (hub, near, far)}
    assert len({(page, symbol.y) for page, symbol in row}) == 1  # one row of one top-level page
    assert _beside(model, hub, near, own=False)
    assert not [p for p, _ in _star_markers(model, near, "branch") if not in_own_set(model, p)]
    if fill == 1:
        _joined_by_wires(model, hub, near, far)
        assert not _star_markers(model, near, "branch")
        return
    (branch,) = _star_markers(model, near, "branch")
    ref_page = next(p for p, _ in _star_markers(model, hub, "ref"))
    assert ref_page == _own_page(model, hub)
    assert in_own_set(model, ref_page)
    assert branch


def test_control_a_pair_beside_each_other_in_both_sets_gets_no_marker_pair() -> None:
    """-X1:2 is beside the hub in both sets and joined to it by a wire: it takes no marker,
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
    assert not _star_markers(model, beside, "branch")
    assert not _star_markers(model, beside, "ref")
    page, a = _stands(model, hub)[True]
    assert _joined(model, page, a, _stands(model, beside)[True][1])
    assert len(_star_markers(model, apart, "branch")) == 1
    refs = _star_markers(model, hub, "ref")
    assert [len(value.split()) for _, r in refs for _, value in r.texts] == [1]
