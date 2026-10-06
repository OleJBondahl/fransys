"""BOUNDARY-DRAW (layout-0080, designer ruling 2026-09-25): how a unit's boundary pin is drawn.

Rule 1: a top-level unit's boundary pin wired out of the unit (to the top level or to another
top-level unit) gets a D10 stub label (an OFF `LinkMarker`) on the unit's own page, whatever the
location. Rule 2: the other end gets the mirror stub, an item at the top level in the top-level
drawing set, the far unit's pin in that unit's drawing set. Rule 5: a NESTED unit (parent is
another unit) is unchanged: the wire is drawn in the parent's set at the black box's replica
pin, and the nested unit's own set ends at the pin with no stub and no finding. Rule 6: a star
net of three or more ports joining boundary pins of two nested units in their parent's set is
drawn there: the black-box pins are ordinary members, wires where adjacent, star markers
otherwise.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import system_document

from fransys_model.derive import unit_release
from fransys_model.derive.drawing_text import off_stub_text
from fransys_model.kernel import Severity
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    Route,
    StarKind,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Boundary draw",
    "number": "P-1012",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _pin_one(model, name: str):
    """The id of pin 1 of the connector function `name` (the one `x1` function of that item)."""
    (function,) = (f.id for f in functions(model).values() if f.key[-3:] == (name, "fn", "x1"))
    (port,) = (p.id for p in ports(model).values() if p.function == function and p.name == "1")
    return port


def _set_name(model, page) -> str | None:
    """The unit name of the drawing set `page` is in (`None`: the top-level set)."""
    one = layout_of(model, DrawingSet)[layout_of(model, Page)[page].drawing_set]
    return None if one.unit is None else unit_release(model, one.unit).name


def _errors(result) -> list[tuple[str, tuple]]:
    """`(code, subjects)` of every ERROR finding of the build, sorted."""
    return sorted((f.code, f.subjects) for f in result.findings if f.severity is Severity.ERROR)


def _off_stubs(model) -> dict[str | None, list[str]]:
    """The text of every OFF marker, by the unit name of the drawing set it stands in."""
    found: dict[str | None, list[str]] = {}
    for marker in layout_of(model, LinkMarker).values():
        if marker.star is StarKind.OFF:
            found.setdefault(_set_name(model, marker.page), []).append(off_stub_text(model, marker))
    return {name: sorted(texts) for name, texts in found.items()}


def _covered_in(model, unit_name: str | None, port) -> bool:
    """Whether a route ends at `port`, or a marker names it, on a page of that unit's set."""
    routes = (r for r in layout_of(model, Route).values() if port in (r.a, r.b))
    markers = (m for m in layout_of(model, LinkMarker).values() if m.port == port)
    return any(_set_name(model, one.page) == unit_name for one in (*routes, *markers))


def _build_top_level_units(*, second_unit: bool, same: bool):
    """Unit `ua` with a boundary connector `f` (X1, at C1), wired `f.1` at the top level to
    either a top-level item `h` (X2) or, with `second_unit`, to the boundary connector `g`
    (X3) of a second top-level unit `ub`. The far end sits at C1 (`same`) or at C2."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    c1, c2 = d.location("C1", "Cabinet"), d.location("C2", "Cabinet two")
    where = c1 if same else c2
    ua = d.scope("ua").unit("ua", revision=1, interface="1")
    ua.revision(1, date="2026-01-01", text="First release", created="XX")
    f = ua.item("DEMO-CONN-2P", name="f", tag="X1", at=c1, group=ua.group("GA", "Group A"))
    ua.boundary(f)
    if second_unit:
        ub = d.scope("ub").unit("ub", revision=1, interface="1")
        ub.revision(1, date="2026-01-01", text="First release", created="XX")
        far = ub.item("DEMO-CONN-2P", name="g", tag="X3", at=where, group=ub.group("GB", "Group B"))
        ub.boundary(far)
    else:
        far = d.item("DEMO-CONN-2P", name="h", tag="X2", at=where)
    d.wiring(colour="BU", gauge="0.5")(f["1"], far["1"])
    return fr.build(parts, d.draft(), system_document())


@pytest.mark.parametrize(
    ("same", "expected"),
    [
        pytest.param(
            True, {None: ["← -X1:1"], "ua": ["← +C1-X2:1"]}, id="same-location-fails-on-base"
        ),
        pytest.param(
            False, {None: ["← +C1-X1:1"], "ua": ["← +C2-X2:1"]}, id="other-location-control"
        ),
    ],
)
def test_a_unit_boundary_pin_wired_to_the_top_level_gets_a_stub_pair(same, expected) -> None:
    """Rules 1 and 2, G-A. The item `h` at the same location (C1) or another (C2).

    Exactly one OFF marker stands in ua's set and one in the top-level set, whatever the
    location. Base: the other-location case passes (a control); the same-location case
    reports `CONNECTION_NOT_DRAWN` and draws no stub.
    """
    # UNDO: stages/offstubs.py `ends_in_stubs`: return only `crosses_location(a, b)` (drop the
    #   boundary-pin clause)
    result = _build_top_level_units(second_unit=False, same=same)
    assert _errors(result) == []
    assert _off_stubs(result.model) == expected


@pytest.mark.parametrize(
    ("same", "expected"),
    [
        pytest.param(True, {"ua": ["← +C1-X3:1"], "ub": ["← +C1-X1:1"]}, id="same-location"),
        pytest.param(False, {"ua": ["← +C2-X3:1"], "ub": ["← +C1-X1:1"]}, id="other-location"),
    ],
)
def test_two_top_level_units_boundary_pins_wired_together_get_a_stub_each(same, expected) -> None:
    """Rules 1 and 2, G-A. `f.1` of `ua` wired to `g.1` of `ub` at the top level, `g` at the
    same location (C1) or another (C2): one OFF marker in ua's set, one in ub's, none
    anywhere else. Base: the other-location case passes (a control); the same-location case
    reports `CONNECTION_NOT_DRAWN` on both pins and draws no stub."""
    # UNDO: stages/offstubs.py `ends_in_stubs`: return only `crosses_location(a, b)` (drop the
    #   boundary-pin clause)
    result = _build_top_level_units(second_unit=True, same=same)
    assert _errors(result) == []
    assert _off_stubs(result.model) == expected


def _build_mated_units():
    """Top-level units `ua` and `ub`, each with a boundary connector (`fa` X1, `fb` X3, both at
    C1) mated to each other, and a wire inside the unit from the connector's pin 1 to an inside
    item (`ia` X2, `ib` X4)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    c1 = d.location("C1", "Cabinet")
    made = {}
    for name, boundary_tag, inside_tag in (("a", "X1", "X2"), ("b", "X3", "X4")):
        u = d.scope(f"u{name}").unit(f"u{name}", revision=1, interface="1")
        u.revision(1, date="2026-01-01", text="First release", created="XX")
        group = u.group("G", "Group")
        made[name] = u.item("DEMO-CONN-2P", name=f"f{name}", tag=boundary_tag, at=c1, group=group)
        inside = u.item("DEMO-CONN-2P", name=f"i{name}", tag=inside_tag, at=c1, group=group)
        u.boundary(made[name])
        u.wiring(colour="BU", gauge="0.5")(made[name]["1"], inside["1"])
    d.mate(made["a"], made["b"])
    return fr.build(parts, d.draft(), system_document())


def test_two_top_level_units_boundary_connectors_mated_get_a_stub_each_through_the_mate() -> None:
    """Rule 1 through a mate (`mate_stub`). Both connectors at C1: no location is crossed, yet
    each is a top-level unit's boundary pin mated outside the unit. 0 ERROR; one OFF marker in
    each unit's set, naming the item the mated connector's inside wire ends at (`ib` X4 for
    `ua`'s pin, `ia` X2 for `ub`'s), none in the top-level set."""
    # UNDO: stages/offstubs.py `ends_in_stubs`: return only `crosses_location(a, b)` (drop the
    #   boundary-pin clause)
    result = _build_mated_units()
    assert _errors(result) == []
    assert _off_stubs(result.model) == {"ua": ["← +C1-X4:1"], "ub": ["← +C1-X2:1"]}


def _build_pass_through():
    """Top-level unit `a` holding nested unit `n`, whose connector `x1` (X1, at C1) is the
    boundary of `n` and of `a` (the pass-through the validator asks for), wired `x1.1` to the
    top-level item `h` (X2) at the same location."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    c1 = d.location("C1", "Cabinet")
    a = d.scope("a").unit("a", revision=1, interface="1")
    a.revision(1, date="2026-01-01", text="First release", created="XX")
    n = a.scope("n", at=c1).unit("n", revision=1, interface="1")
    n.revision(1, date="2026-01-01", text="First release", created="XX")
    x1 = n.item("DEMO-CONN-2P", name="x1", tag="X1", at=c1, group=n.group("GN", "Group N"))
    n.boundary(x1)
    a.boundary(x1)
    h = d.item("DEMO-CONN-2P", name="h", tag="X2", at=c1)
    d.wiring(colour="BU", gauge="0.5")(x1["1"], h["1"])
    return fr.build(parts, d.draft(), system_document())


def test_a_pass_through_boundary_pin_wired_to_the_top_level_gets_a_stub_pair() -> None:
    """Rules 1 and 2. `x1` of nested unit `n` is also the boundary of the top-level unit `a`:
    it is a top-level unit's boundary pin, wired out of `a`, so it gets a stub on `a`'s set and
    `h` the mirror stub in the top-level set, at the same location. Base: `CONNECTION_NOT_DRAWN`
    on `x1.1`, no OFF marker at all (the pin's own unit `n` has a parent)."""
    # UNDO: read/units.py `top_boundary_edges`: skip the functions that are also the boundary
    #   of a nested unit (the pass-through pin is then not a top-level unit's boundary pin)
    result = _build_pass_through()
    assert _errors(result) == []
    assert _off_stubs(result.model) == {None: ["← -X1:1"], "a": ["← +C1-X2:1"]}


def _build_nested_wire():
    """Unit `p` at the top level holding nested unit `ua` (boundary connector `f`, X1) and an
    item `h` (X2) in `p`, wired `f.1` to `h.1` in `p`'s scope."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    p = d.scope("p").unit("p", revision=1, interface="1")
    p.revision(1, date="2026-01-01", text="First release", created="XX")
    box = p.location("BOX", "Box")
    ua = p.scope("ua", at=box).unit("ua", revision=1, interface="1")
    ua.revision(1, date="2026-01-01", text="First release", created="XX")
    f = ua.item("DEMO-CONN-2P", name="f", tag="X1", at=box, group=ua.group("GA", "Group A"))
    ua.boundary(f)
    h = p.item("DEMO-CONN-2P", name="h", tag="X2", at=box, group=p.group("GP", "Group P"))
    p.wiring(colour="BU", gauge="0.5")(f["1"], h["1"])
    return fr.build(parts, d.draft(), system_document())


def test_a_nested_units_boundary_wire_is_drawn_in_the_parent_set_with_no_stub() -> None:
    """Rule 5. The wire `f.1` to `h.1` is drawn in `p`'s set at the black box's replica pin
    (a route or a marker covers both ports there); no OFF marker exists and there is no
    error. Base: `CONNECTION_NOT_DRAWN` once (the pin of `f`, or of `h`, in `p`'s set)."""
    # UNDO: stages/exempt.py `boundary_exempt`, the own-set branch: `nested` ->
    #   `False` (the nested pin is covered and reported in its own set again)
    result = _build_nested_wire()
    model = result.model
    f, h = _pin_one(model, "f"), _pin_one(model, "h")
    assert _errors(result) == []
    assert _off_stubs(model) == {}
    assert [m for m in layout_of(model, LinkMarker).values() if m.star is StarKind.OFF] == []
    assert _covered_in(model, "p", f)
    assert _covered_in(model, "p", h)


def _build_nested_chain(units_count: int):
    """Unit `p` holding nested units `u0`..`u<N-1>` (N = `units_count`), each with a boundary
    connector `c<i>` (X<i+1>), and an item `k` (X9) in `p`, all wired in `p`'s scope as a
    chain `c0.1-c1.1-...-k.1`: one net of N+1 ports."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    p = d.scope("p").unit("p", revision=1, interface="1")
    p.revision(1, date="2026-01-01", text="First release", created="XX")
    box = p.location("BOX", "Box")
    pins = []
    for i in range(units_count):
        u = p.scope(f"u{i}", at=box).unit(f"u{i}", revision=1, interface="1")
        u.revision(1, date="2026-01-01", text="First release", created="XX")
        c = u.item(
            "DEMO-CONN-2P", name=f"c{i}", tag=f"X{i + 1}", at=box, group=u.group(f"G{i}", "G")
        )
        u.boundary(c)
        pins.append(c["1"])
    k = p.item("DEMO-CONN-2P", name="k", tag="X9", at=box, group=p.group("GP", "Group P"))
    pins.append(k["1"])
    wire = p.wiring(colour="BU", gauge="0.5")
    for i in range(len(pins) - 1):
        wire(pins[i], pins[i + 1])
    return fr.build(parts, d.draft(), system_document())


@pytest.mark.parametrize("units_count", [2, 4])
def test_a_net_through_nested_units_boundary_pins_is_drawn_in_the_parent_set_only(
    units_count,
) -> None:
    """Rules 5 and 6 together. A net of N+1 ports (N nested units' boundary pins and an item
    `k`, a star from three ports) is drawn in `p`'s set: every port of it, the replica pins
    included, is covered there by a route end or a marker. The nested units' own sets hold no
    star marker (REF or BRANCH) for the pins: the net leaves each unit, so its set ends at the
    pin. Base: the replicas are exempt in `p`'s set and the markers (a REF in `u1`'s set, a
    BRANCH in each of the other units' sets and one in `p`'s) stand inside the units' own
    sets, page references joining two units' documents."""
    # UNDO: stages/exempt.py `boundary_exempt`, the black-box branch:
    #   `exempt = not nested or not any(leaves(mate, unit) for mate in net[port])` -> `True`
    #   (every black-box pin exempt in the parent's set again; the markers land in the own sets)
    result = _build_nested_chain(units_count)
    model = result.model
    names = [f"c{i}" for i in range(units_count)] + ["k"]
    own_sets = {f"u{i}" for i in range(units_count)}
    assert _errors(result) == []
    inside = [
        (_set_name(model, m.page), m.star)
        for m in layout_of(model, LinkMarker).values()
        if m.star in (StarKind.REF, StarKind.BRANCH) and _set_name(model, m.page) in own_sets
    ]
    assert inside == []
    assert all(_covered_in(model, "p", _pin_one(model, name)) for name in names)


def test_wiring_inside_one_unit_is_untouched() -> None:
    """Control (base: passes). A unit holding two connectors wired to each other inside the
    unit, one of them its boundary: no error, no OFF marker, the wire drawn in the unit's set."""
    # UNDO: fransys_layout/stages/references/cuts.py `_case`: treat a
    #   boundary pin's wire inside the unit as leaving it (an OFF stub or a
    #   cut where both ends are in the unit)
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    at = d.location("C1", "Cabinet")
    ua = d.scope("ua").unit("ua", revision=1, interface="1")
    ua.revision(1, date="2026-01-01", text="First release", created="XX")
    group = ua.group("GA", "Group A")
    f = ua.item("DEMO-CONN-2P", name="f", tag="X1", at=at, group=group)
    g = ua.item("DEMO-CONN-2P", name="g", tag="X2", at=at, group=group)
    ua.boundary(f)
    ua.wiring(colour="BU", gauge="0.5")(f["1"], g["1"])
    result = fr.build(parts, d.draft(), system_document())
    model = result.model
    assert _errors(result) == []
    assert _off_stubs(model) == {}
    assert _covered_in(model, "ua", _pin_one(model, "f"))
    assert _covered_in(model, "ua", _pin_one(model, "g"))
