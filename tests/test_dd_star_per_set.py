# CONNECTION_NOT_DRAWN 9 per build (KI-306): an anchored finding, not asserted here.
"""Across drawing sets: a branch is decided where a port stands, not once for the whole net.

A unit's boundary terminals stand twice: as pins in the top-level set and where their group
puts them in the unit's own set. The PE net here is three terminals, `-X1:1` (the hub) wired to
"""

from typing import Any

import fransys as fr
import fransys_parts
import pytest
from _dd_core_c import beside, in_own_set, markers_of, stands
from _model_build_cover import layout_trigger_document, unit_document
from fransys_author.design import Design

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


def _build(spec: tuple[tuple[str, int], ...], *, fill: int):
    """A cabinet unit `+C1` with one boundary terminal per `spec` entry, the first wired to each
    other on the inner side (one PE net). Each terminal's outer side is wired to a relay coil of
    its group; `fill` relays stand in each group in all, so a group of 3 fills a page of its own.
    Returns the model and the terminals' printed tags, in `spec` order."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    groups = {n: cab.group(f"G{n}", f"Group {n}") for _, n in spec}
    strips = {name: cab.strip(name, at=c1) for name in dict.fromkeys(n for n, _ in spec)}
    terminals = [strips[name].terminal("DEMO-TB-2.5-TWIN", group=groups[n]) for name, n in spec]
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
            # layout-0112: an unwired contact is not drawn, and the relays must fill the page.
            if fill > 1:
                blue(relay.fn("co_1")["11"], relay.fn("co_1")["14"])
                blue(relay.fn("co_2")["21"], relay.fn("co_2")["24"])
            if k == 0:
                blue(terminal.outer, relay.fn("coil")["A1"])
    result = fr.build(parts, d.draft(), layout_trigger_document(), unit_document(cab))
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    seen: dict[str, int] = {}
    tags = []
    for name, _ in spec:
        seen[name] = seen.get(name, 0) + 1
        tags.append(f"-{name}:{seen[name]}")
    return result.model, tags


def _stands(model, tag: str) -> dict[Any, Any]:
    """`tag`'s terminal by set: True is the unit's own set, False the top-level one."""
    found = {own: [spot] for own, spots in stands(model, tag).items() for spot in spots}
    assert set(found) == {True, False}  # one placement in each of the two sets
    return {own: spot[0] for own, spot in found.items()}


def _beside(model, a: str, b: str, *, own: bool) -> bool:
    """Whether `a` and `b` stand on one page of the set at one y with nothing between them."""
    return beside(model, _stands(model, a)[own], _stands(model, b)[own])


def _own_page(model, tag: str):
    return _stands(model, tag)[True][0]


def _star_markers(model, tag: str, kind: str, page=None) -> list[Any]:
    """The markers of library key `kind` printing `tag`, on `page` when given."""
    return markers_of(model, tag, kind, page)


@pytest.mark.parametrize("fill", [3], ids=["other-page"])
def test_a_port_apart_from_the_reference_in_the_unit_set_gets_a_branch_there(fill: int) -> None:
    """-X3:1 is beside the hub -X1:1 in the top-level set and apart in the unit's own set. On a
    page of its own it carries a branch marker there whose partner is the hub's
    reference marker."""
    # UNDO: stages/references/nets.py, `branch_pages`: the return statement to
    #     `return []` (no set takes a branch): FAILED on `len(branches)` (other-page)
    model, (hub, near, _far) = _build(_APART, fill=fill)
    assert _beside(model, hub, near, own=False)  # side by side in the top-level set
    assert not _beside(model, hub, near, own=True)  # and apart in the unit's own set
    assert _own_page(model, hub) != _own_page(model, near)
    branches = _star_markers(model, near, "branch", _own_page(model, near))
    assert len(branches) == 1, "-X3:1 stands apart from -X1:1 in the unit's set and shows no branch"
    assert _star_markers(model, hub, "ref", _own_page(model, hub))


@pytest.mark.parametrize("fill", [3], ids=["other-page"])
def test_the_reference_in_the_unit_set_lists_the_branch_of_the_port_apart_from_it(
    fill: int,
) -> None:
    """The hub's reference marker in the unit's own set lists -X3:1 and -X3:2, one line for each
    branch marker that names them (the box may share lines of other nets at that pin, so
    only the lines of this net's own number are counted)."""
    # UNDO: `branch_pages` returns `[]` (other-page)
    model, (hub, near, far) = _build(_APART, fill=fill)
    own = _own_page(model, hub)
    refs = [(p, m) for p, m in _star_markers(model, hub, "ref") if p in {own, _own_page(model, far)}]
    assert refs
    branches = [(p, m) for tag in (near, far) for p, m in _star_markers(model, tag, "branch")]
    assert {tag for tag in (near, far) if _star_markers(model, tag, "branch")} == {near, far}, "the reference does not list -X3:1"
    own_lines = [line for _, r in refs for _, value in r.texts for line in value.split("\n") if line.startswith("#")]
    assert len(own_lines) == len(branches) == 2


@pytest.mark.parametrize("fill", [3], ids=["other-page"])
def test_in_the_top_level_set_the_pair_stands_beside_and_takes_no_branch(fill: int) -> None:
    """In the top-level set the hub, `near` and `far` stand in one row and the hub is beside
    `near`, so a wire joins them and `near` takes no branch marker there; its branch stands in
    the unit's own set and names the hub's reference marker on the hub's own page (an own-set
    placement of the reference, never the top-level pin)."""
    # UNDO: stages/references/nets.py, `branch_pages`: the return
    #     statement to `return []`: FAILED on `(branch,) = ...` (other-page)
    model, (hub, near, far) = _build(_APART, fill=fill)
    row = {_stands(model, tag)[False] for tag in (hub, near, far)}
    assert len({(page, symbol.y) for page, symbol in row}) == 1  # one row of one top-level page
    assert _beside(model, hub, near, own=False)
    assert not [p for p, _ in _star_markers(model, near, "branch") if not in_own_set(model, p)]
    (branch,) = _star_markers(model, near, "branch")
    ref_page = next(p for p, _ in _star_markers(model, hub, "ref"))
    assert ref_page == _own_page(model, hub)
    assert in_own_set(model, ref_page)
    assert branch


def _codes(monkeypatch: pytest.MonkeyPatch, build, *args, **kwargs) -> list[Any]:
    """The finding codes of every `fr.build` that `build(*args, **kwargs)` runs."""
    found: list[Any] = []
    real = fr.build

    def spy(*a, **k):
        result = real(*a, **k)
        found.extend(f.code for f in result.findings)
        return result

    with monkeypatch.context() as m:
        m.setattr(fr, "build", spy)
        build(*args, **kwargs)
    return found


def test_a_coil_wired_to_itself_keeps_a_wire_to_both_pins(monkeypatch: pytest.MonkeyPatch) -> None:
    """R1574, R1580: each pin of an unlinked pole is its own net end, so -K1:A2 (and -K4:A2, -K7:A2 of the
    star builds, whose A1 takes the fan tap) is joined; the coils' own pairs (K2, K3...) stay joined."""
    # UNDO: core/topology_elements.py _folds: drop `and (elem.form == "free" or pair in joined)` so every pole folds: FAILED on CND (3 and 1)
    from test_dd_boundary_terminal_crash import _build as crash_build

    star = _codes(monkeypatch, _build, _APART, fill=3)
    crash = _codes(monkeypatch, crash_build, (("K1", "A1"), ("K1", "A2")))
    for codes in (star, crash):
        assert "CONNECTION_NOT_DRAWN" not in codes
        assert "DRAWING_SHORTS_NETS" not in codes
