"""Tests for `vocab/validators/units.py`, the unit checks.

`docs/decisions/model-0038-units.md`.
"""

from plant import Plant

from fransys_model.derive import boundary as unit_boundary
from fransys_model.kernel import Severity
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.validators.units import (
    check_units,
)

# ---- BOUNDARY_UNCONNECTED ---------------------------------------------------------------------


# ---- UNIT_BOUNDARY_BYPASSED ---------------------------------------------------------------------


# ---- UNIT_CONNECTOR_DANGLING ---------------------------------------------------------------------


# ---- MATE_PORT_MISMATCH ---------------------------------------------------------------------


# ---- MATE_NOT_CONNECTOR -----------------------------------------------------------------------


# ---- UNUSED_CONTRADICTED ---------------------------------------------------------------------


# ---- any function may be a boundary (model-0188) ---------------------------------------


def test_a_relay_coil_marked_boundary_reports_no_kind_finding() -> None:
    """A `COIL` function marked as a unit's boundary is accepted: any function may be one."""
    plant = Plant()
    unit = plant.unit("cabinet")
    item = plant.item("item", unit=unit)
    function = plant.function(item, "coil", kind=FunctionKind.COIL)
    plant.port(function, "A1")
    plant.boundary(unit, function)
    model = plant.model()
    # examined: the coil really is declared this unit's boundary
    assert unit_boundary(model, unit) == (function,)
    assert [f for f in check_units(model) if f.severity == Severity.ERROR] == []


# ---- BOUNDARY_NOT_IN_UNIT ---------------------------------------------------------------------
