"""Wiring rows: what a wire carries and the row a supply's rail gives it (model-0260).

The one home of `rail_row`: authoring calls it with a rail's conductor mark; the
`resolve_wire_rows` pass reaches it through `supply_rail_row`, which reads the mark off the rail.
"""

from enum import StrEnum
from typing import Final

from fransys_model.kernel import register_enum

from .enums import ConductorMark


@register_enum
class WiringRow(StrEnum):
    """What a wire carries; a wiring table maps each row to a colour, or a colour and a size."""

    DC_SUPPLY = "DC_SUPPLY"
    DC_GROUND = "DC_GROUND"
    DC_CONTROL = "DC_CONTROL"
    DC_SIGNAL = "DC_SIGNAL"
    AC_L1 = "AC_L1"
    AC_L2 = "AC_L2"
    AC_L3 = "AC_L3"
    AC_N = "AC_N"
    AC_CONTROL = "AC_CONTROL"


_BY_MARK: Final = {
    ConductorMark.L1: WiringRow.AC_L1,
    ConductorMark.L2: WiringRow.AC_L2,
    ConductorMark.L3: WiringRow.AC_L3,
    ConductorMark.N: WiringRow.AC_N,
    ConductorMark.L_PLUS: WiringRow.DC_SUPPLY,
    ConductorMark.M: WiringRow.DC_GROUND,
}


def rail_row(mark: ConductorMark, *, has_mid: bool = False) -> WiringRow:
    """The row of a supply rail: `L-` is 0 V without a mid, a supply rail with one."""
    if mark is ConductorMark.L_MINUS:
        return WiringRow.DC_SUPPLY if has_mid else WiringRow.DC_GROUND
    return _BY_MARK[mark]


_AC_ROWS: Final = frozenset(
    {WiringRow.AC_L1, WiringRow.AC_L2, WiringRow.AC_L3, WiringRow.AC_N, WiringRow.AC_CONTROL}
)


def control_of(row: WiringRow) -> WiringRow:
    """The control row of the path `row` belongs to: AC_CONTROL or DC_CONTROL."""
    return WiringRow.AC_CONTROL if row in _AC_ROWS else WiringRow.DC_CONTROL


def is_control(row: WiringRow) -> bool:
    """True for DC_CONTROL and AC_CONTROL, the rows of no rail's potential."""
    return row in {WiringRow.DC_CONTROL, WiringRow.AC_CONTROL}
