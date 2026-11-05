"""NET_ACROSS_UNIT_BOUNDARY: one finding per declared net across a unit boundary, no cascade."""

from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.checks.connectivity import check_connectivity
from fransys_model.checks.units import check_units
from fransys_model.vocab.enums import NetClass
lazy from fransys_model.vocab.connectivity import Net
lazy from fransys_model.vocab.core import Port

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id


def _plant(*, net_inside: bool = False, net_class: NetClass = NetClass.GENERIC) -> tuple[Plant, Id[Net], Id[Port]]:
    """Unit `inner` in `outer`; a boundary pin `j` and a pin `x`, joined by the net EXT_A."""
    plant = Plant()
    outer = plant.unit("outer", name="outer")
    inner = plant.unit("inner", name="inner", parent=outer)
    plant.item("z", unit=outer)  # keeps `inner` from being standalone
    plant.item("j", unit=inner)
    plant.item("x", unit=inner if net_inside else outer)
    j, x = plant.pin("j", "f", "1"), plant.pin("x", "f", "1")
    plant.boundary(inner, plant.function_id("j", "f"))
    return plant, plant.net("n", (j, x), name="EXT_A", net_class=net_class), j


def _found(plant: Plant) -> list[Finding]:
    model = plant.model()
    return [*check_connectivity(model), *check_units(model)]


def _codes(plant: Plant) -> list[str]:
    return [f.code for f in _found(plant)]


def test_a_net_across_a_boundary_gives_one_error_naming_net_and_pin() -> None:
    plant, net, j = _plant()
    (found,) = [f for f in _found(plant) if f.code == "NET_ACROSS_UNIT_BOUNDARY_OPEN"]
    assert found.subjects == (net, j)
    assert "EXT_A" in found.message
    assert "d.series" in found.fix


def test_the_cascade_is_not_reported_for_that_net() -> None:
    codes = _codes(_plant()[0])
    assert "NET_UNREALISED" not in codes
    assert "BOUNDARY_UNCONNECTED" not in codes


def test_a_net_inside_one_unit_gives_no_crossing_finding() -> None:
    assert not {c for c in _codes(_plant(net_inside=True)[0]) if c.startswith("NET_ACROSS_UNIT_BOUNDARY")}


def test_a_net_inside_one_unit_in_two_pieces_is_still_unrealised() -> None:
    """Can-fail partner of the NET_UNREALISED suppression."""
    assert "NET_UNREALISED" in _codes(_plant(net_inside=True)[0])


def test_the_boundary_is_unconnected_when_no_crossing_net_carries_it() -> None:
    """Can-fail partner of the BOUNDARY_UNCONNECTED suppression."""
    assert "BOUNDARY_UNCONNECTED" in _codes(_plant(net_inside=True)[0])


def _shorted_plant(*, crossing: bool) -> Plant:
    """A wire joins the pin `j` of net EXT_A to the pin `k` of a net OTHER."""
    plant, _, j = _plant(net_inside=not crossing)
    k = plant.pin("k", "f", "1")
    plant.net("m", (k,), name="OTHER")
    plant.wire(j, k, key="w")
    return plant


def test_a_crossing_net_wired_to_a_differently_named_net_is_still_shorted() -> None:
    """A real short is never hidden by the crossing finding (layout-0322)."""
    assert "NET_SHORTED" in _codes(_shorted_plant(crossing=True))


def test_a_crossing_net_wired_to_an_unnamed_net_is_not_shorted() -> None:
    """Can-fail partner of the narrowed suppression: the cascade of an unnamed neighbour."""
    plant, _, j = _plant()
    k = plant.pin("k", "f", "1")
    plant.net("m", (k,))
    plant.wire(j, k, key="w")
    assert "NET_SHORTED" not in _codes(plant)


def test_a_physical_net_without_a_crossing_net_is_shorted() -> None:
    """Can-fail partner of the NET_SHORTED suppression."""
    assert "NET_SHORTED" in _codes(_shorted_plant(crossing=False))


def test_a_joined_boundary_pin_makes_the_crossing_a_warning() -> None:
    """A wire carries `j` across, so only the net is unrealised: WARNING, not ERROR."""
    plant = Plant()
    outer = plant.unit("outer", name="outer")
    inner = plant.unit("inner", name="inner", parent=outer)
    for key, unit in (("z", outer), ("j", inner), ("x", outer), ("w", outer)):
        plant.item(key, unit=unit)
    j, x, w = (plant.pin(key, "f", "1") for key in ("j", "x", "w"))
    plant.boundary(inner, plant.function_id("j", "f"))
    plant.net("n", (j, x), name="EXT_A")
    plant.wire(j, w, key="wire")
    (found,) = [f for f in _found(plant) if f.code == "NET_ACROSS_UNIT_BOUNDARY_JOINED"]
    assert found.severity.value == "warning"
    assert "BOUNDARY_UNCONNECTED" not in _codes(plant)


def test_an_earth_boundary_pin_on_a_pe_net_across_units_is_connected_by_declaration() -> None:
    """G08-POWER: earth is by declaration; the PE net across the boundary is no BOUNDARY_UNCONNECTED."""
    codes = _codes(_plant(net_class=NetClass.PE)[0])
    assert "BOUNDARY_UNCONNECTED" not in codes
    assert "NET_ACROSS_UNIT_BOUNDARY_OPEN" not in codes


def test_an_earth_net_inside_one_unit_does_not_connect_the_boundary() -> None:
    """Can-fail partner: a PE net that never leaves the unit declares nothing across it."""
    assert "BOUNDARY_UNCONNECTED" in _codes(_plant(net_inside=True, net_class=NetClass.PE)[0])


def test_a_boundary_function_with_an_open_signal_pin_and_a_carried_earth_pin_is_still_unconnected() -> None:
    """model-0403: earth carries its own PE port only, never the whole function."""
    plant, _, _ = _plant(net_class=NetClass.PE)
    plant.pin("j", "f", "2")
    (found,) = [f for f in _found(plant) if f.code == "BOUNDARY_UNCONNECTED"]
    assert plant.function_id("j", "f") in found.subjects
