"""Tests for `connector_box_lines`: a connector box's text lines (HL5, HL7)."""

from typing import TYPE_CHECKING

from connector_builders import make_connector
from plant import Plant
from query_builders import make_part

from fransys_model.derive import connector_box_lines
from fransys_model.kernel import make_id
from fransys_model.vocab import Boundary
from fransys_model.vocab.enums import FunctionKind

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function


def _box(*, name: str | None, extra_kind: FunctionKind | None = None) -> tuple[Plant, Id[Function]]:
    """Item `-X1` of part `MPN-X1` with one connector function, a boundary named `name`."""
    plant = Plant()
    unit = plant.unit("u")
    part = make_part(plant, "p", "MPN-X1")
    item = plant.item("x1", designation="X1", part=part, unit=unit)
    function, _ = make_connector(plant, ("x1", "c"), ("1",))
    if extra_kind is not None:
        plant.function(item, "e", kind=extra_kind)
    if name is not None:
        key = ("boundary",)
        record = Boundary(
            id=make_id(Boundary, key), key=key, unit=unit, function=function, name=name
        )
        plant.add(record)
    return plant, function


def test_a_named_boundary_prints_designation_part_and_name() -> None:
    """A field `pwr_estop` differs from `-X1`, so the box has three lines."""
    plant, function = _box(name="pwr_estop")
    assert connector_box_lines(plant.model(), function) == ("-X1", "MPN-X1", "pwr_estop")


def test_a_name_equal_to_the_designation_ignoring_case_prints_no_name_line() -> None:
    """The usual `X1` field, and `x1`, say nothing the designation does not."""
    for name in ("X1", "x1"):
        plant, function = _box(name=name)
        assert connector_box_lines(plant.model(), function) == ("-X1", "MPN-X1")


def test_a_connector_that_is_no_unit_boundary_has_no_name_line() -> None:
    """Without a boundary there is no name to print."""
    plant, function = _box(name=None)
    assert connector_box_lines(plant.model(), function) == ("-X1", "MPN-X1")


def test_a_sensors_built_in_connector_prints_no_part_line() -> None:
    """An item that also has a non-connector function carries the sensor's MPN, not the plug's."""
    plant, function = _box(name=None, extra_kind=FunctionKind.GENERIC)
    assert connector_box_lines(plant.model(), function) == ("-X1",)
