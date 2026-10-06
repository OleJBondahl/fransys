"""CUT-END rules 2 and 3 (designer ruling 2026-09-25): which pages a severed wire's cut uses.

Rule 2: when no one unit holds both ends' own pages but some unit holds a page of each end
(two units' boundary functions wired to each other, meeting in their parent's drawing set, or
in the top-level set), the cut stands between each end's earliest page in that unit's set. The
old rule took each end's earliest page anywhere. `stages._ordering.buckets` numbers the top
level (`None`) first and then the units by `Id` order, which is a hash order and not the tree:
a nested parent's set can come after its children's. Then the boundary function's earliest
page is its home page in its own unit's set, the two ends look like two units' pages, `links`
classifies the cut CROSS_UNIT and nothing is drawn in the parent, where the wire stands.

Rule 3: a wire between two functions of two units where no unit holds a page of each end (a
connection that bypasses a boundary, `UNIT_BOUNDARY_BYPASSED`) keeps its CROSS_UNIT decision
and gets no marker.

The two boundary functions are 2-pin connectors wired pin 1 to pin 1, a net of two ports. With
the units nested in a parent, the wire is drawn in the parent's set at the black boxes, each
unit's own set ends at its pin with nothing (layout-0080 rule 5), and no error is reported.
With two top-level units the wire ends in a D10 stub on each pin, and no error is reported.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records
and, for the decisions, from `run_stages`.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import system_document

from fransys_layout.engines.schematic import lay_out_schematic, run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages import LinkCase
from fransys_model.derive import unit_release
from fransys_model.derive.drawing_text import off_stub_text
from fransys_model.kernel import Severity
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Page,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports
from fransys_model.vocab.validators.units import UNIT_BOUNDARY_BYPASSED

_PROJECT: dict[str, Any] = {
    "title": "Cut end rules",
    "number": "P-1011",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build_boundary_pair(*, parent: str | None):
    """Units `ua` and `ub`, each holding a boundary connector (`ja`, `jb`, group GA and GB),
    wired `ja.1` to `jb.1` in the scope that holds both units, with a page break before GB so the
    two black-box replicas stand on two pages of that scope's drawing set. Both units sit
    in the unit named `parent`, or at the top level with `parent` `None`. Returns the result."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    if parent is None:
        scope, at = d, d.location("C1", "Cabinet")
        ua = d.scope("ua").unit("ua", revision=1, interface="1")
        ua.revision(1, date="2026-01-01", text="First release", created="XX")
        ub = d.scope("ub").unit("ub", revision=1, interface="1")
        ub.revision(1, date="2026-01-01", text="First release", created="XX")
    else:
        scope = d.scope(parent).unit(parent, revision=1, interface="1")
        scope.revision(1, date="2026-01-01", text="First release", created="XX")
        at = scope.location("BOX", "Box")
        ua = scope.scope("ua", at=at).unit("ua", revision=1, interface="1")
        ua.revision(1, date="2026-01-01", text="First release", created="XX")
        ub = scope.scope("ub", at=at).unit("ub", revision=1, interface="1")
        ub.revision(1, date="2026-01-01", text="First release", created="XX")
    group_a, group_b = ua.group("GA", "Group A"), ub.group("GB", "Group B")
    ja = ua.item("DEMO-CONN-2P", name="ja", tag="X1", at=at, group=group_a)
    jb = ub.item("DEMO-CONN-2P", name="jb", tag="X2", at=at, group=group_b)
    ua.boundary(ja)
    ub.boundary(jb)
    scope.wiring(colour="BU", gauge="0.5")(ja["1"], jb["1"])
    scope.break_before(group_b)
    return fr.build(parts, d.draft(), system_document())


def _pin_one(model, name: str):
    """The id of pin 1 of the connector function `name` (the one `x1` function of that item)."""
    (function,) = (f.id for f in functions(model).values() if f.key[-3:] == (name, "fn", "x1"))
    (port,) = (p.id for p in ports(model).values() if p.function == function and p.name == "1")
    return port


def _stands(model, port) -> list[tuple[int, int]]:
    """`(drawing set number, page number)` of every placement of `port`'s function."""
    function = ports(model)[port].function
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    return sorted(
        (sets[pages[p.page].drawing_set].number, pages[p.page].number)
        for p in layout_of(model, SymbolPlacement).values()
        if p.function == function
    )


def _set_number(model, unit_name: str | None) -> int:
    """The number of the one drawing set of the unit named `unit_name` (`None`: the top level)."""
    (found,) = (
        s.number
        for s in layout_of(model, DrawingSet).values()
        if (None if s.unit is None else unit_release(model, s.unit).name) == unit_name
    )
    return found


def _wire_markers(model, *wire_ports) -> list[LinkMarker]:
    return [m for m in layout_of(model, LinkMarker).values() if m.port in wire_ports]


def _errors(result) -> list[tuple[str, tuple]]:
    """`(code, subjects)` of every ERROR finding of the build, sorted."""
    return sorted((f.code, f.subjects) for f in result.findings if f.severity is Severity.ERROR)


@pytest.mark.parametrize(
    ("parent", "parent_set_is_late"),
    [
        pytest.param("p5", True, id="nested-parent-set-after-its-units-sets"),
        pytest.param("outer", False, id="nested-parent-set-before-its-units-sets"),
    ],
)
def test_two_units_boundary_functions_wired_in_their_parent_get_a_marker_pair_there(
    parent, parent_set_is_late
) -> None:
    """Rules 1 and 2 (base: passes for the last, a control; fails for the first).

    The wire stands in the parent's drawing set, where the replicas of `ja` and `jb` are on two
    pages (the cut). With the parent's set numbered after both units' own sets, each end's
    earliest page is its home page in its own unit's set: two ends in two units, no marker
    on the base, and the wire silently undrawn in the parent. The rule takes the parent's pages.
    """
    # UNDO: fransys_layout/stages/references/cuts.py `_cuts` and
    #   lint/_cuts.py `conductor_cut`: the cut of a conductor goes back to
    #   each end's `min` page (`min(pages_a)`, `min(pages_b)`;
    #   `pages_a[0]`, `pages_b[0]`). Only the first parameter set fails.
    result = _build_boundary_pair(parent=parent)
    model = result.model
    ja, jb = _pin_one(model, "ja"), _pin_one(model, "jb")
    parent_set = _set_number(model, parent)
    own_sets = {_set_number(model, "ua"), _set_number(model, "ub")}
    # the shape needs the cut: the replicas are on two pages of the parent's set
    (ja_replica,) = {place for place in _stands(model, ja) if place[0] == parent_set}
    (jb_replica,) = {place for place in _stands(model, jb) if place[0] == parent_set}
    assert ja_replica[1] != jb_replica[1]
    # and it discriminates only when the homes' sets come before the parent's set
    assert (parent_set > max(own_sets)) is parent_set_is_late
    # rule 5 (layout-0080): each pin's own set ends at the pin, the wire is the parent's
    assert _errors(result) == []
    pair = _wire_markers(model, ja, jb)
    assert len(pair) == 2
    owner, user = sorted(pair, key=lambda m: m.side is MarkerSide.USER)
    assert (owner.port, user.port) == (ja, jb)
    assert (owner.partner, user.partner) == (user.id, owner.id)
    assert {_page_place(model, m.page) for m in (owner, user)} == {ja_replica, jb_replica}


def test_two_top_level_units_boundary_functions_wired_get_a_stub_each() -> None:
    """Rules 1 and 2 of BOUNDARY-DRAW (layout-0080, units spec U2). Two top-level units' boundary
    functions wired to each other at the top level: the wire leaves each unit's set, so each
    pin gets an OFF stub in its own unit's set naming the far pin, and no error, no owner/user
    marker pair stands anywhere."""
    # UNDO: fransys_layout/stages/offstubs.py: `ends_in_stubs` returns only
    #   `crosses_location(a, b)` (both pins are at C1: no stub, `CONNECTION_NOT_DRAWN` on each)
    result = _build_boundary_pair(parent=None)
    model = result.model
    ja, jb = _pin_one(model, "ja"), _pin_one(model, "jb")
    assert _errors(result) == []
    markers = _wire_markers(model, ja, jb)
    assert {m.star for m in markers} == {StarKind.OFF}
    found = {}
    for marker in markers:
        one = layout_of(model, DrawingSet)[layout_of(model, Page)[marker.page].drawing_set]
        assert one.unit is not None  # a unit's own set, not the top-level one
        found[marker.port] = (unit_release(model, one.unit).name, off_stub_text(model, marker))
    assert found == {ja: ("ua", "← +C1-X2:1"), jb: ("ub", "← +C1-X1:1")}


def _page_place(model, page) -> tuple[int, int]:
    """`(drawing set number, page number)` of `page`."""
    one = layout_of(model, Page)[page]
    return layout_of(model, DrawingSet)[one.drawing_set].number, one.number


def _build_bypass():
    """Units `ua` and `ub` at one top-level location, each holding one plain connector (no
    boundary), `fa.1` wired to `fb.1` at the top level: no set holds a page of both."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    at = d.location("C1", "Cabinet")
    ua = d.scope("ua").unit("ua", revision=1, interface="1")
    ua.revision(1, date="2026-01-01", text="First release", created="XX")
    ub = d.scope("ub").unit("ub", revision=1, interface="1")
    ub.revision(1, date="2026-01-01", text="First release", created="XX")
    fa = ua.item("DEMO-CONN-2P", name="fa", tag="X1", at=at, group=ua.group("GA", "Group A"))
    fb = ub.item("DEMO-CONN-2P", name="fb", tag="X2", at=at, group=ub.group("GB", "Group B"))
    d.wiring(colour="BU", gauge="0.5")(fa["1"], fb["1"])
    return fr.build(parts, d.draft(), system_document())


def test_a_wire_that_bypasses_the_boundaries_keeps_its_cross_unit_decision_and_no_marker() -> None:
    """Rule 3 (base: passes, a guard). No unit holds a page of each end, so the cut is between
    the earliest pages as before: `CROSS_UNIT`, and no marker on either end."""
    # UNDO: fransys_layout/stages/references/cuts.py `_case`: drop the
    #   `CROSS_UNIT` return (the two ends' units differ, and the cut comes
    #   out SEVERED with a marker pair)
    result = _build_bypass()
    # The bypass is the scenario: `UNIT_BOUNDARY_BYPASSED` is an ERROR, so `fr.build` runs no
    # layout (decision 0028); lay the numbered model out directly.
    assert UNIT_BOUNDARY_BYPASSED in {f.code for f in result.findings}
    assert {code for code, _subjects in _errors(result)} == {UNIT_BOUNDARY_BYPASSED}
    model, _layout_findings = lay_out_schematic(result.model)
    fa, fb = _pin_one(model, "fa"), _pin_one(model, "fb")
    (fa_set,), (fb_set,) = ({s for s, _ in _stands(model, p)} for p in (fa, fb))
    assert fa_set != fb_set  # no drawing set holds a page of each end
    layout, _drawn, _findings = run_stages(model, read_inputs(model))
    (decision,) = [d for d in layout.decisions if {d.a, d.b} == {fa, fb}]
    assert decision.case is LinkCase.CROSS_UNIT
    assert _wire_markers(model, fa, fb) == []
