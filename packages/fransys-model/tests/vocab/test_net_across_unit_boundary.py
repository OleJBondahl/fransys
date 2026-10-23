"""NET_ACROSS_UNIT_BOUNDARY: one finding per declared net across a unit boundary, no cascade."""

from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.checks.connectivity import check_connectivity
from fransys_model.checks.units import check_units
lazy from fransys_model.vocab.connectivity import Net
lazy from fransys_model.vocab.core import Port

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id


def _plant(*, net_inside: bool = False) -> tuple[Plant, Id[Net], Id[Port]]:
    """Unit `inner` in `outer`; a boundary pin `j` and a pin `x`, joined by the net EXT_A."""
    plant = Plant()
    outer = plant.unit("outer", name="outer")
    inner = plant.unit("inner", name="inner", parent=outer)
    plant.item("z", unit=outer)  # keeps `inner` from being standalone
    plant.item("j", unit=inner)
    plant.item("x", unit=inner if net_inside else outer)
    j, x = plant.pin("j", "f", "1"), plant.pin("x", "f", "1")
    plant.boundary(inner, plant.function_id("j", "f"))
    return plant, plant.net("n", (j, x), name="EXT_A"), j


def _found(plant: Plant) -> list[Finding]:
    model = plant.model()
    return [*check_connectivity(model), *check_units(model)]


def _codes(plant: Plant) -> list[str]:
    return [f.code for f in _found(plant)]


def test_a_net_across_a_boundary_gives_one_error_naming_net_and_pin() -> None:
    plant, net, j = _plant()
    (found,) = [f for f in _found(plant) if f.code == "NET_ACROSS_UNIT_BOUNDARY"]
    assert found.subjects == (net, j)
    assert "EXT_A" in found.message
    assert "d.detail.wire" in found.fix


def test_the_cascade_is_not_reported_for_that_net() -> None:
    codes = _codes(_plant()[0])
    assert "NET_UNREALISED" not in codes
    assert "BOUNDARY_UNCONNECTED" not in codes


def test_a_net_inside_one_unit_gives_no_crossing_finding() -> None:
    assert "NET_ACROSS_UNIT_BOUNDARY" not in _codes(_plant(net_inside=True)[0])


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
    (found,) = [f for f in _found(plant) if f.code == "NET_ACROSS_UNIT_BOUNDARY"]
    assert found.severity.value == "warning"
    assert "BOUNDARY_UNCONNECTED" not in _codes(plant)
