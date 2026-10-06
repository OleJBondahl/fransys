"""WP16 tests: terminals, conductors and ports (design/derive-queries.md, decision 0021)."""

import pytest
from plant import Plant
from query_builders import leg_net, make_node, make_pin, make_placement, make_strip, make_terminal

from fransys_model.derive import (
    conductors_on_item,
    first_leg,
    function_is_unused,
    no_conductor_at,
    port_is_unused,
    terminal_rows,
    unconnected_ports,
    unused_terminals,
)
from fransys_model.derive.designation import (
    terminal_designation,
)
from fransys_model.kernel import SchemaError, make_id
from fransys_model.vocab.connectivity import Conductor, Net
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import (
    ConductorKind,
    PortRole,
)
from fransys_model.vocab.facets.terminal import TerminalFacet


def test_conductors_on_item_lists_only_terminals_with_conductors_and_only_roles_with_some() -> None:
    """Grouped by terminal then role, leaving out what has no conductor.

    An unused terminal, a non-terminal child and a role with no conductor are absent; the
    conductor ids are in id order.
    """
    plant = Plant()
    strip, (l2, l1, n1) = make_strip(plant)
    extra = plant.wire(make_pin(plant, "panel-b", "K2"), l1.internal, key="x1-panel-b")
    plant.wire(make_pin(plant, "field-n", "B2"), n1.external, key="x1-field-n")
    child = plant.item("x1-note", designation="N1", parent=strip)
    plant.wire(
        plant.port(plant.function(child, "f"), "1"), make_pin(plant, "elsewhere", "Z1"), key="z"
    )
    model = plant.model()
    result = conductors_on_item(model, strip)
    assert set(result) == {l1.item, l2.item, n1.item}
    assert set(result[n1.item]) == {PortRole.EXTERNAL}
    assert set(result[l1.item]) == {PortRole.INTERNAL, PortRole.EXTERNAL}
    internal = result[l1.item][PortRole.INTERNAL]
    assert internal == tuple(sorted(internal))
    assert extra in internal
    assert len(internal) == 3  # panel-a, panel-b and the jumper
    assert list(result) == sorted(result)
    assert list(result[l1.item]) == [PortRole.EXTERNAL, PortRole.INTERNAL]


def test_many_conductors_on_one_terminal_come_out_in_id_order_in_both_queries() -> None:
    """Eight conductors per role: too many for a set's iteration order to look sorted."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    terminal = make_terminal(plant, "x1", "t1", group="L", index=1)
    inside = [
        plant.wire(make_pin(plant, f"in-{n}", f"K{n}"), terminal.internal, key=f"in-{n}")
        for n in range(8)
    ]
    outside = [
        plant.wire(make_pin(plant, f"out-{n}", f"B{n}"), terminal.external, key=f"out-{n}")
        for n in range(8)
    ]
    model = plant.model()
    grouped = conductors_on_item(model, strip)[terminal.item]
    assert grouped[PortRole.INTERNAL] == tuple(sorted(inside))
    assert grouped[PortRole.EXTERNAL] == tuple(sorted(outside))
    (row,) = terminal_rows(model, strip)
    assert row.internal == tuple(sorted(inside))
    assert row.external == tuple(sorted(outside))


def test_conductors_on_item_leaves_out_a_terminal_without_any_conductor() -> None:
    """A strip whose only terminal is unused has no groups."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    make_terminal(plant, "x1", "t1", group="L", index=1)
    assert conductors_on_item(plant.model(), strip) == {}


def test_a_conductor_between_the_two_ports_of_one_terminal_is_listed_under_both_roles() -> None:
    """Both ends on one child: once per role it touches."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    terminal = make_terminal(plant, "x1", "t1", group="L", index=1)
    conductor = plant.wire(terminal.internal, terminal.external, key="loop")
    grouped = conductors_on_item(plant.model(), strip)[terminal.item]
    assert grouped[PortRole.INTERNAL] == (conductor,)
    assert grouped[PortRole.EXTERNAL] == (conductor,)


def test_conductors_on_item_of_a_childless_item_is_empty_not_a_crash() -> None:
    """An item with no children at all (no entry in the child index) still returns `{}`."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    assert conductors_on_item(plant.model(), strip) == {}


def test_conductors_on_item_refuses_an_id_that_is_not_an_item() -> None:
    """Unknown identity: `SchemaError`, not an empty answer."""
    plant = Plant()
    plant.item("x1", designation="X1")
    with pytest.raises(SchemaError):
        conductors_on_item(plant.model(), make_id(Item, ("nope",)))


def test_terminal_rows_are_sorted_by_group_then_index_then_id() -> None:
    """Not by designation, key or authoring order; equal group and index fall back to the id."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    made = [
        make_terminal(plant, "x1", "t-b1", group="B", index=1),
        make_terminal(plant, "x1", "t-a10", group="A", index=10),
        make_terminal(plant, "x1", "t-a2", group="A", index=2),
        make_terminal(plant, "x1", "t-tie-1", group="A", index=3),
        make_terminal(plant, "x1", "t-tie-2", group="A", index=3),
    ]
    rows = terminal_rows(plant.model(), strip)
    ties = sorted((made[3].item, made[4].item))
    assert [row.terminal for row in rows] == [made[2].item, *ties, made[1].item, made[0].item]
    assert [(row.group, row.index) for row in rows] == [
        ("A", 2),
        ("A", 3),
        ("A", 3),
        ("A", 10),
        ("B", 1),
    ]


def test_terminal_rows_carry_designation_and_conductors_by_role_including_jumpers() -> None:
    """Each row lists its conductors by role, sorted by id, jumpers included.

    The jumper is an internal conductor of both of its terminals; an unused terminal has empty
    tuples.
    """
    plant = Plant()
    strip, (l2, l1, n1) = make_strip(plant)
    model = plant.model()
    rows = {row.terminal: row for row in terminal_rows(model, strip)}
    row = rows[l1.item]
    assert row.designation == terminal_designation(model, l1.item)
    assert len(row.internal) == 2  # the jumper and the panel wire
    assert len(row.external) == 1
    assert row.internal == tuple(sorted(row.internal))
    assert len(rows[l2.item].internal) == 1
    assert rows[l2.item].external == ()
    assert rows[n1.item].internal == () == rows[n1.item].external


def test_jumper_groups_number_the_bridged_terminals_from_one_in_row_order() -> None:
    """Bridged terminals share a number, from 1, in row order.

    Bridges chain (a-b, b-c is one group); a terminal no jumper reaches has `None`; a wire
    between two terminals is no bridge.
    """
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    a, b, c, d, e, f = (
        make_terminal(plant, "x1", f"t{i}", group="L", index=i) for i in range(1, 7)
    )
    plant.wire(b.internal, c.internal, key="j-bc", kind=ConductorKind.JUMPER)
    plant.wire(a.internal, b.external, key="j-ab", kind=ConductorKind.JUMPER)
    plant.wire(e.internal, d.internal, key="j-de", kind=ConductorKind.JUMPER)
    plant.wire(f.internal, a.external, key="plain")
    rows = terminal_rows(plant.model(), strip)
    assert [row.jumper_group for row in rows] == [1, 1, 1, 2, 2, None]


def test_a_jumper_to_a_terminal_of_another_strip_bridges_nothing_here() -> None:
    """A group needs two terminals of this strip."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    plant.item("x2", designation="X2")
    mine = make_terminal(plant, "x1", "t1", group="L", index=1)
    theirs = make_terminal(plant, "x2", "t1", group="L", index=1)
    plant.wire(mine.internal, theirs.internal, key="cross", kind=ConductorKind.JUMPER)
    (row,) = terminal_rows(plant.model(), strip)
    assert row.jumper_group is None
    assert len(row.internal) == 1


def test_terminal_rows_hold_only_the_strips_own_terminals() -> None:
    """A terminal of another strip and a child without the facet are not rows."""
    plant = Plant()
    strip, _ = make_strip(plant)
    plant.item("x9", designation="X9")
    make_terminal(plant, "x9", "t1", group="L", index=1)
    plant.item("x1-note", designation="N1", parent=strip)
    assert len(terminal_rows(plant.model(), strip)) == 3


def test_terminal_rows_refuse_an_id_that_is_not_an_item() -> None:
    """Unknown identity: `SchemaError`, not an empty list."""
    plant = Plant()
    plant.item("x1", designation="X1")
    with pytest.raises(SchemaError):
        terminal_rows(plant.model(), make_id(Item, ("nope",)))


def test_terminal_rows_need_no_designation_field_on_a_terminal() -> None:
    """A terminal renders `group:index` from its facet, so an unnumbered one is still a row."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    plant.item("t1", parent=strip)
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("t1", "facet")),
            key=("t1", "facet"),
            subject=make_id(Item, ("t1",)),
            group="L",
            index=1,
        )
    )
    (row,) = terminal_rows(plant.model(), strip)
    assert row.designation == "-X1:L:1"


def test_first_leg_prefers_the_candidate_a_conductor_joins_to_from_item() -> None:
    """The larger-id candidate is wired, so plain `min` of the candidates would be wrong."""
    plant = Plant()
    net, src, candidates = leg_net(plant, wired_to=1)
    assert first_leg(plant.model(), net, from_item=src) == candidates[1]


def test_first_leg_without_a_direct_conductor_is_the_smallest_candidate() -> None:
    """Nothing joins `from_item` directly: the smallest id of the other ports."""
    plant = Plant()
    net, src, candidates = leg_net(plant, wired_to=None)
    assert first_leg(plant.model(), net, from_item=src) == candidates[0]


def test_first_leg_ignores_a_conductor_to_a_port_off_the_net() -> None:
    """A conductor to a port the declared net does not list makes nobody the direct leg."""
    plant = Plant()
    net, src, candidates = leg_net(plant, wired_to=None)
    stray = make_pin(plant, "stray", "Z1")
    plant.wire(make_id(Port, ("src", "f", "1")), stray, key="stray-wire")
    assert first_leg(plant.model(), net, from_item=src) == candidates[0]


def test_first_leg_is_none_when_from_item_is_not_on_the_net_or_nothing_else_is() -> None:
    """No own port, or no candidate: `None`."""
    plant = Plant()
    net, src, _ = leg_net(plant, wired_to=None)
    lonely = plant.net("lonely", (make_id(Port, ("src", "f", "1")),))
    outsider = plant.item("outsider", designation="O1")
    model = plant.model()
    assert first_leg(model, net, from_item=outsider) is None
    assert first_leg(model, lonely, from_item=src) is None


def test_first_leg_refuses_an_unknown_net_and_an_unknown_item() -> None:
    """Both identities are checked."""
    plant = Plant()
    net, src, _ = leg_net(plant, wired_to=None)
    model = plant.model()
    with pytest.raises(SchemaError):
        first_leg(model, make_id(Net, ("nope",)), from_item=src)
    with pytest.raises(SchemaError):
        first_leg(model, net, from_item=make_id(Item, ("nope",)))


def test_a_declared_net_does_not_connect_a_port_but_a_conductor_a_jumper_and_a_mate_do() -> None:
    """Physical singletons only, in id order, whatever `Net.ports` says."""
    plant = Plant()
    alone = plant.pin("alone", "f", "1")
    on_a, on_b = plant.pin("on-a", "f", "1"), plant.pin("on-b", "f", "1")
    plant.net("declared", (on_a, on_b))
    w1, w2 = plant.pin("w1", "f", "1"), plant.pin("w2", "f", "1")
    plant.wire(w1, w2, key="w")
    j1, j2 = plant.pin("j1", "f", "1"), plant.pin("j2", "f", "1")
    plant.wire(j1, j2, key="j", kind=ConductorKind.JUMPER)
    m1, m2 = plant.pin("m1", "c", "1"), plant.pin("m2", "c", "1")
    plant.mate(plant.function_id("m1", "c"), plant.function_id("m2", "c"))
    assert unconnected_ports(plant.model()) == tuple(sorted((alone, on_a, on_b)))
    assert m1 != m2


def test_unused_terminals_are_the_strips_own_terminals_with_no_conductor_sorted_by_id() -> None:
    """Used, foreign and non-terminal children are not listed; a wire on either port uses one."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    plant.item("x2", designation="X2")
    made = [make_terminal(plant, "x1", f"t{i}", group="L", index=i) for i in range(1, 7)]
    plant.wire(make_pin(plant, "a", "B1"), made[0].internal, key="wa")
    plant.wire(make_pin(plant, "b", "B2"), made[1].external, key="wb")
    make_terminal(plant, "x2", "t1", group="L", index=1)
    plant.item("x1-note", designation="N1", parent=strip)
    unused = unused_terminals(plant.model(), strip)
    assert unused == tuple(sorted(t.item for t in made[2:]))


def test_unused_terminals_of_a_childless_strip_is_empty_not_a_crash() -> None:
    """A strip with no children at all (no entry in the child index) still returns `()`."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    assert unused_terminals(plant.model(), strip) == ()


def test_unused_terminals_refuse_an_unknown_strip() -> None:
    """Unknown identity: `SchemaError`."""
    plant = Plant()
    plant.item("x1", designation="X1")
    with pytest.raises(SchemaError):
        unused_terminals(plant.model(), make_id(Item, ("nope",)))


@pytest.mark.parametrize(
    "label", ["conductors_on_item", "unused_terminals", "terminal_rows", "first_leg"]
)
def test_wiring_queries_refuse_an_unknown_locator_id(label) -> None:
    """Each locator's `require` names the missing record's own kind and id, not an empty one."""
    plant = Plant()
    plant.item("x1", designation="X1")
    model = plant.model()
    unknown_item = make_id(Item, ("nope",))
    unknown_net = make_id(Net, ("nope",))
    calls = {
        "conductors_on_item": (
            "item",
            unknown_item,
            lambda: conductors_on_item(model, unknown_item),
        ),
        "unused_terminals": (
            "item",
            unknown_item,
            lambda: unused_terminals(model, unknown_item),
        ),
        "terminal_rows": (
            "item",
            unknown_item,
            lambda: terminal_rows(model, unknown_item),
        ),
        "first_leg": (
            "net",
            unknown_net,
            lambda: first_leg(model, unknown_net, from_item=unknown_item),
        ),
    }
    kind, record_id, call = calls[label]
    with pytest.raises(SchemaError) as excinfo:
        call()
    assert excinfo.value.kind == kind
    assert excinfo.value.record_id == record_id


def test_terminal_rows_use_the_units_own_location_over_a_distracting_context() -> None:
    """Once a real `unit` is given, `context` is ignored (`unit_list_context`, model-0056).

    The strip is the unit's own root, placed at `c1`; a far pin outside the unit, also at `c1`,
    prints its whole path `+C1-F1:1` (FAR-END-ONE-HOME A2), whatever `ext` context is passed.
    A far end inside the unit would print short against `c1`.
    """
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    bu = plant.unit("bu", name="bu")
    strip = plant.item("x1", designation="X1", unit=bu)
    plant.add(make_placement("x1-loc", strip, c1.id))
    l1 = make_terminal(plant, "x1", "t-l1", group="L", index=1)
    far = make_pin(plant, "far", "F1")
    plant.add(make_placement("far-loc", make_id(Item, ("far",)), c1.id))
    plant.wire(far, l1.external, key="w1")
    model = plant.model()
    (row,) = terminal_rows(model, strip, unit=bu, context=ext.id)
    assert row.external_ends == ("+C1-F1:1",)


def test_a_jumper_gives_both_bridged_terminals_the_same_jumper_group_number() -> None:
    """Both terminals a jumper bridges get `jumper_group=1`; the third, unbridged, gets `None`."""
    plant = Plant()
    strip, (l2, l1, n1) = make_strip(plant)
    model = plant.model()
    rows = {row.terminal: row for row in terminal_rows(model, strip)}
    assert rows[l1.item].jumper_group == 1
    assert rows[l2.item].jumper_group == 1
    assert rows[n1.item].jumper_group is None


def test_far_ends_are_as_long_as_the_row_and_a_jumper_resolves_to_the_other_terminal() -> None:
    """`internal_ends`/`external_ends` match `internal`/`external` in length.

    The jumper's far end is `L2`'s own terminal text, never `L1`'s own and never blank.
    """
    plant = Plant()
    strip, (l2, l1, _n1) = make_strip(plant)
    model = plant.model()
    (row,) = [row for row in terminal_rows(model, strip) if row.terminal == l1.item]
    assert len(row.internal_ends) == len(row.internal)
    assert len(row.external_ends) == len(row.external)
    jumper = make_id(Conductor, ("x1-jumper",))
    far_end = row.internal_ends[row.internal.index(jumper)]
    assert far_end == terminal_designation(model, l2.item)
    assert far_end not in ("", terminal_designation(model, l1.item))


def test_terminal_rows_blank_a_far_end_outside_a_nested_unit() -> None:
    """A nested `unit`'s own list blanks an end whose item's own unit is not in its subtree.

    `end_outside_nested_unit` is `""`, not `None` and not the far end's full path.
    """
    plant = Plant()
    outer = plant.unit("outer", name="outer")
    inner = plant.unit("inner", name="inner", parent=outer)
    strip = plant.item("x1", designation="X1", unit=inner)
    l1 = make_terminal(plant, "x1", "t-l1", group="L", index=1)
    outside_pin = make_pin(plant, "outside", "F1")
    plant.wire(outside_pin, l1.external, key="w1")
    model = plant.model()
    (row,) = terminal_rows(model, strip, unit=inner)
    assert row.external_ends == ("",)


def test_no_conductor_at_is_false_for_any_conductor_kind_and_true_for_mate_net_or_bare() -> None:
    """A conductor of any kind ends at a port; a mate or a declared net does not."""
    plant = Plant()
    w1, w2 = plant.pin("w1", "f", "1"), plant.pin("w2", "f", "1")
    plant.wire(w1, w2, key="w")
    j1, j2 = plant.pin("j1", "f", "1"), plant.pin("j2", "f", "1")
    plant.wire(j1, j2, key="j", kind=ConductorKind.JUMPER)
    c1, c2 = plant.pin("c1", "f", "1"), plant.pin("c2", "f", "1")
    plant.wire(c1, c2, key="c", kind=ConductorKind.CORE)
    b1, b2 = plant.pin("b1", "f", "1"), plant.pin("b2", "f", "1")
    plant.wire(b1, b2, key="b", kind=ConductorKind.BUSBAR)
    m1, m2 = plant.pin("m1", "c", "1"), plant.pin("m2", "c", "1")
    plant.mate(plant.function_id("m1", "c"), plant.function_id("m2", "c"))
    n1, n2 = plant.pin("n1", "f", "1"), plant.pin("n2", "f", "1")
    plant.net("declared", (n1, n2))
    bare = plant.pin("bare", "f", "1")
    model = plant.model()
    assert [no_conductor_at(model, p) for p in (w1, w2, j1, j2, c1, c2, b1, b2)] == [False] * 8
    assert [no_conductor_at(model, p) for p in (m1, m2, n1, n2, bare)] == [True] * 5


def test_port_and_function_are_unused_only_with_no_conductor_and_no_net() -> None:
    """A conductor or a declared net makes a port used; a mate does not; a function needs all."""
    plant = Plant()
    w1, w2 = plant.pin("w1", "f", "1"), plant.pin("w2", "f", "1")
    plant.wire(w1, w2, key="w")
    n1, n2 = plant.pin("n1", "f", "1"), plant.pin("n2", "f", "1")
    plant.net("declared", (n1, n2))
    m1, m2 = plant.pin("m1", "c", "1"), plant.pin("m2", "c", "1")
    plant.mate(plant.function_id("m1", "c"), plant.function_id("m2", "c"))
    bare = plant.pin("bare", "f", "1")
    mixed_bare, mixed_net = plant.pin("mix", "f", "1"), plant.pin("mix", "f", "2")
    plant.net("half", (mixed_net, w1))
    model = plant.model()
    assert [port_is_unused(model, p) for p in (w1, w2, n1, n2, mixed_net)] == [False] * 5
    assert [port_is_unused(model, p) for p in (m1, m2, bare, mixed_bare)] == [True] * 4
    assert function_is_unused(model, plant.function_id("m1", "c"))
    assert function_is_unused(model, plant.function_id("bare", "f"))
    assert not function_is_unused(model, plant.function_id("mix", "f"))
    assert not function_is_unused(model, plant.function_id("n1", "f"))
