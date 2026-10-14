"""The unit matrix on the units worked example (OVERVIEW O7, model-0197)."""

import sys
from pathlib import Path

import fransys as fr
import fransys_parts
from _model_build_cover import system_document

# `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design

from fransys_model.derive import field_devices, printed_designation, unit_matrix


def test_each_cell_counts_the_cables_between_two_boxes_row_before_column() -> None:
    """Each motor lands in one cabinet, a field device off the axis; the shared sensor stays."""
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    model = fr.build(parts, design.draft(), system_document()).model
    matrix = unit_matrix(model)
    assert all(cell.row < cell.col for cell in matrix.cells)
    found = {
        (matrix.axis[c.row].lines[0], matrix.axis[c.col].lines[0]): (
            c.count,
            tuple(printed_designation(model, cable) for cable in c.cables),
        )
        for c in matrix.cells
    }
    assert found == {
        ("+ER+C1", "+FLD-K1"): (1, ("-WM1S",)),
        ("+ER+C2", "+FLD-K1"): (1, ("-WM2S",)),
    }


def test_the_axis_holds_no_field_device() -> None:
    """Breaks if a box `field_devices` folds into a unit stays on the axis (O7)."""
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    model = fr.build(parts, design.draft(), system_document()).model
    axis = {box.box for box in unit_matrix(model).axis}
    assert field_devices(model)
    assert not axis & set(field_devices(model))
    assert axis
