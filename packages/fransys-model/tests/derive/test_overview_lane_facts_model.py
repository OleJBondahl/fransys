"""The facts the lanes order reads: a stub's side (LO1), a power line (LO2), the strips (LO4)."""

import dataclasses

from plant import Plant
from query_builders import make_pin, make_terminal
from rating_plant import rail, supply

from fransys_model.derive import (
    overview_lane_strips,
    overview_power_lines,
    overview_strip_joins,
    overview_stub_west,
    overview_view_rows,
)
from fransys_model.kernel import make_id
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef, OverviewRefKind
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Current


def _ref(key: str) -> OverviewRef:
    return OverviewRef(kind=OverviewRefKind.ITEM, item=make_id(Item, (key,)))


def _homed(plant: Plant, homes: dict) -> None:
    plant.records = [
        dataclasses.replace(r, unit=homes[r.key[0]])
        if isinstance(r, Item) and r.key[0] in homes
        else r
        for r in plant.records
    ]


def _sides_plant():
    """`z1` in nested `n`; `k1` in the enclosing `u`, `b1` in no unit, strip `x9` in no unit."""
    plant = Plant()
    outer = plant.unit("u", name="cab", tag="U1")
    nested = plant.unit("n", name="brd", parent=outer, tag="U2")
    plant.item("x9", designation="X9")
    t9 = make_terminal(plant, "x9", "t9", group="L", index=9)
    z1, k1, b1 = (make_pin(plant, key, key.upper()) for key in ("z1", "k1", "b1"))
    z1b = plant.port(plant.function_id("z1", "f"), "2")
    z1c = plant.port(plant.function_id("z1", "f"), "3")
    plant.wire(z1, k1, key="w1")
    plant.wire(z1b, b1, key="w2")
    plant.wire(z1c, t9.external, key="w3")
    _homed(plant, {"z1": nested, "k1": outer})
    return plant.model(), nested


def test_a_stub_is_west_for_an_enclosing_unit_or_a_strip_and_east_for_any_other() -> None:
    """LO1: breaks if a side comes from anything but the far end's strip kind and unit chain."""
    model, nested = _sides_plant()
    view = next(
        v
        for v in overview_view_rows(model, nested)
        if v.mode is OverviewMode.LANES and v.open is None
    )
    side = {
        b.key.ref.item: overview_stub_west(model, nested, b.key.ref)
        for b in view.boxes
        if b.key.at is not None
    }
    assert side == {
        make_id(Item, ("k1",)): True,
        make_id(Item, ("x9",)): True,
        make_id(Item, ("b1",)): False,
    }


def test_a_place_or_unit_end_stands_east() -> None:
    """LO1: breaks if a reference that is no item is west."""
    model, nested = _sides_plant()
    unit_ref = OverviewRef(kind=OverviewRefKind.UNIT, unit=nested)
    assert not overview_stub_west(model, nested, unit_ref)
    assert not overview_stub_west(model, nested, OverviewRef(kind=OverviewRefKind.PLACE))


def _power_plant():
    """In `u`: `a`-`b` joined by a wire on an AC rail, `c`-`d` by one on a DC rail, strip `x1`."""
    plant = Plant()
    outer = plant.unit("u", name="cab", tag="U1")
    supply(plant, "mains", {"L": rail("230", 0)}, current=Current.AC)
    supply(plant, "ctrl", {"P": rail("24")}, current=Current.DC)
    plant.item("x1", designation="X1")
    t1 = make_terminal(plant, "x1", "t1", group="L", index=1)
    for first, second, potential in (("a", "b", "L"), ("c", "d", "P")):
        ends = [make_pin(plant, key, key.upper()) for key in (first, second)]
        for n, end in enumerate(ends):
            plant.net(f"net-{first}-{n}", (end,), potential=potential)
        plant.wire(*ends, key=f"w-{first}{second}")
        if first == "c":
            plant.wire(ends[0], t1.external, key="w-ct")
    _homed(plant, dict.fromkeys(("a", "b", "c", "d", "x1"), outer))
    return plant.model(), outer


def test_a_line_on_an_ac_potential_is_a_power_line_and_a_dc_line_is_not() -> None:
    """LO2: breaks if any wire is a power line, or the current of the potential is ignored."""
    model, unit = _power_plant()
    ends = {(a.ref.item, b.ref.item) for a, b in overview_power_lines(model, unit)}
    key = lambda k: make_id(Item, (k,))  # noqa: E731 -- a one-line key helper
    assert ends == {(key("a"), key("b"))} or ends == {(key("b"), key("a"))}


def test_the_strips_of_a_level_are_the_boxes_of_strip_kind() -> None:
    """LO4: breaks if a device is a strip, or a strip is left out."""
    model, unit = _power_plant()
    assert overview_lane_strips(model, unit) == {BoxKey(ref=_ref("x1"))}


def test_a_stub_joined_to_an_earlier_terminal_of_a_strip_has_an_earlier_place() -> None:
    """LO5: breaks if the place comes from the stub's name or the line order, not the terminal."""
    plant = Plant()
    unit = plant.unit("u", name="cab", tag="U1")
    plant.item("x1", designation="X1", unit=unit)
    t0, t1 = (make_terminal(plant, "x1", f"t{n}", group="L", index=n) for n in range(2))
    fa, fb = (make_pin(plant, key, key.upper()) for key in ("fa", "fb"))
    plant.wire(fa, t1.external, key="wa")
    plant.wire(fb, t0.external, key="wb")
    _homed(plant, {"x1": unit})
    model = plant.model()
    place = overview_strip_joins(model, unit)
    host = _ref("x1")
    assert place[BoxKey(ref=_ref("fb"), at=host)] == 0
    assert place[BoxKey(ref=_ref("fa"), at=host)] == 1
    assert BoxKey(ref=host) not in place
