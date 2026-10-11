"""Tests: terminals, conductors and ports (decision 0021)."""

from plant import Plant
from query_builders import leg_net, make_pin, make_strip, make_terminal

from fransys_model.derive import (
    conductors_on_item,
    first_leg,
    terminal_rows,
    unused_terminals,
)
from fransys_model.vocab.enums import (
    PortRole,
)


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


def test_many_conductors_on_one_terminal_come_out_in_id_order_then_far_end_order() -> None:
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
    assert set(row.internal) == set(inside)
    assert set(row.external) == set(outside)
    assert row.internal_ends == tuple(
        f"-K{n}:1" for n in range(8)
    )  # `terminal_rows` follows the far end
    assert row.external_ends == tuple(f"-B{n}:1" for n in range(8))


def test_conductors_on_item_of_a_childless_item_is_empty_not_a_crash() -> None:
    """An item with no children at all (no entry in the child index) still returns `{}`."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    assert conductors_on_item(plant.model(), strip) == {}


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
