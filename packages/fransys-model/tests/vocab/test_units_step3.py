"""Tests for `vocab/validators/units.py`, the unit checks.

`docs/decisions/model-0038-units.md`.
"""

import dataclasses

from plant import Plant

from fransys_model.checks.units import (
    check_units,
)
from fransys_model.derive import boundary as unit_boundary
from fransys_model.kernel import Severity
from fransys_model.vocab.enums import FunctionKind

# ---- BOUNDARY_UNCONNECTED ---------------------------------------------------------------------


# ---- UNIT_BOUNDARY_BYPASSED ---------------------------------------------------------------------


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


# ---- DRAWN_WITH_UNIT_UNWIRED (BY-OTHERS-DRAWN-WITH) ---------------------------------------------


def _drawn_with_plant(*, wired: bool) -> list[str]:
    """The DRAWN_WITH_UNIT_UNWIRED findings: by-others root `x` drawn with unit `skid`, its child `m` wired to `skid`'s `inside` only when `wired`."""
    plant = Plant()
    skid = plant.unit("skid")
    plant.item("inside", unit=skid)
    root = plant.item("x")
    plant.records[-1] = dataclasses.replace(plant.records[-1], external=True, drawn_with=skid)
    plant.item("m", parent=root)
    inside, far, other = plant.pin("inside", "f", "1"), plant.pin("m", "f", "1"), plant.pin("y", "f", "1")
    plant.wire(inside if wired else other, far, key="w")
    return [f.code for f in check_units(plant.model()) if f.code == "DRAWN_WITH_UNIT_UNWIRED"]


def test_a_drawn_with_item_with_no_wire_to_its_unit_is_an_error_and_a_wired_twin_is_not() -> None:
    assert _drawn_with_plant(wired=False) == ["DRAWN_WITH_UNIT_UNWIRED"]
    assert _drawn_with_plant(wired=True) == []
