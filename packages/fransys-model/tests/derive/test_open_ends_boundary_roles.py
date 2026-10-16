"""Pins `open_ends`: a standalone unit's boundary ports are open, but not an `INTERNAL` one."""

from dataclasses import replace

from plant import Plant

from fransys_model.derive.facts.current.ties import open_ends
from fransys_model.vocab.enums import PortRole


def test_a_boundary_port_is_open_unless_internal() -> None:
    plant = Plant()
    unit = plant.unit("U")
    item = plant.item("a", unit=unit)
    function = plant.function(item, "f")
    plant.boundary(unit, function)
    outer = plant.port(function, "out")
    inner = plant.port(function, "in")
    plant.records = [
        replace(r, role=PortRole.INTERNAL) if getattr(r, "id", None) == inner else r
        for r in plant.records
    ]
    assert open_ends(plant.model()) == frozenset({outer})
