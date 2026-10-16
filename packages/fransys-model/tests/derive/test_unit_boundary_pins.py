"""`unit_boundary_pins`: a unit's boundary ports in pin order, a pass-through one included."""

import pytest
from plant import Plant

from fransys_model.derive.facts.boundary_pins import unit_boundary_pins
from fransys_model.derive.facts.units import boundary
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Function, Port, Unit


def _plant() -> tuple[Plant, Id[Unit], Id[Unit]]:
    """A cabinet holding a board; the board offers X1 (pins 10, 2, 1), the cabinet passes it up."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    board = plant.unit("board", name="board", parent=cabinet)
    x1 = plant.item("x1", unit=board)
    x1_fn = plant.function(x1, "X1")
    for name in ("10", "2", "1"):
        plant.port(x1_fn, name)
    x2 = plant.item("x2", unit=board)
    plant.function(x2, "X2")
    plant.boundary(board, x1_fn, key="board-x1")
    plant.boundary(cabinet, x1_fn, key="cabinet-x1")
    return plant, cabinet, board


def _port(name: str) -> Id[Port]:
    return make_id(Port, ("x1", "X1", name))


def test_a_nested_unit_lists_its_boundary_pins_in_pin_order() -> None:
    """Pin 2 sorts before pin 10 by digit run; the unoffered function X2 is absent."""
    plant, _, board = _plant()
    model = plant.model()
    pins = unit_boundary_pins(model, board)
    assert len(pins) == 3
    assert pins == (_port("1"), _port("2"), _port("10"))


def test_the_enclosing_unit_lists_the_same_pass_through_pins() -> None:
    """The cabinet offers the board's X1 up, so it lists the same three pins."""
    plant, cabinet, _ = _plant()
    model = plant.model()
    assert len(boundary(model, cabinet)) == 1
    assert boundary(model, cabinet) == (make_id(Function, ("x1", "X1")),)
    assert unit_boundary_pins(model, cabinet) == (_port("1"), _port("2"), _port("10"))


def test_a_unit_without_boundary_and_no_unit_have_no_pins() -> None:
    """A unit that offers nothing, and `None`, list no pins though the model has some."""
    plant, _, _ = _plant()
    loose = plant.unit("loose", name="loose")
    model = plant.model()
    assert len(unit_boundary_pins(model, make_id(Unit, ("board",)))) == 3
    assert unit_boundary_pins(model, loose) == ()
    assert unit_boundary_pins(model, None) == ()


def test_the_boundary_has_one_reader_and_the_none_guard_is_the_callers() -> None:
    """`unit_boundary_functions` is gone; the strict `boundary` raises on no unit (S9)."""
    from fransys_model import derive
    from fransys_model.kernel import SchemaError

    plant, _, _ = _plant()
    assert "unit_boundary_functions" not in derive.__all__
    with pytest.raises(SchemaError):
        boundary(plant.model(), None)  # ty: ignore[invalid-argument-type] a non-unit must raise
