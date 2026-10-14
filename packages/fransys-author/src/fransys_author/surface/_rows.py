"""Wire rows: what a series wire carries, the IEC 60204-1 default table and a scope's table."""

from enum import StrEnum
from typing import TYPE_CHECKING, Final
lazy from decimal import Decimal

from fransys_author.errors import AuthorError
from fransys_author.surface._wire import _colour, _gauge
from fransys_model.vocab import ConductorMark

if TYPE_CHECKING:
    from collections.abc import Mapping

_TUPLE_LEN = 2


class WiringRow(StrEnum):
    """What a series wire carries; a wiring table maps each to a colour, or a colour and a size."""

    DC_SUPPLY = "DC_SUPPLY"
    DC_GROUND = "DC_GROUND"
    DC_CONTROL = "DC_CONTROL"
    AC_L1 = "AC_L1"
    AC_L2 = "AC_L2"
    AC_L3 = "AC_L3"
    AC_N = "AC_N"
    AC_CONTROL = "AC_CONTROL"


DC_SUPPLY: Final = WiringRow.DC_SUPPLY
DC_GROUND: Final = WiringRow.DC_GROUND
DC_CONTROL: Final = WiringRow.DC_CONTROL
AC_L1: Final = WiringRow.AC_L1
AC_L2: Final = WiringRow.AC_L2
AC_L3: Final = WiringRow.AC_L3
AC_N: Final = WiringRow.AC_N
AC_CONTROL: Final = WiringRow.AC_CONTROL

type RowValue = str | tuple[str, float | str | Decimal]
type Spec = tuple[str, Decimal | None]

_AC_ROWS = frozenset({AC_L1, AC_L2, AC_L3, AC_N, AC_CONTROL})
IEC: Final[Mapping[WiringRow, Spec]] = {
    **dict.fromkeys((AC_L1, AC_L2, AC_L3), ("BK", None)),
    AC_N: ("BU", None),
    AC_CONTROL: ("RD", None),
    **dict.fromkeys((DC_SUPPLY, DC_CONTROL, DC_GROUND), ("BU", None)),
}
_BY_MARK = {
    ConductorMark.L1: AC_L1,
    ConductorMark.L2: AC_L2,
    ConductorMark.L3: AC_L3,
    ConductorMark.N: AC_N,
    ConductorMark.L_PLUS: DC_SUPPLY,
    ConductorMark.M: DC_GROUND,
}


def rail_row(mark: ConductorMark, *, has_mid: bool = False) -> WiringRow:
    """The row of a supply rail: `minus` is 0 V without a mid, a supply rail with one."""
    if mark is ConductorMark.L_MINUS:
        return DC_SUPPLY if has_mid else DC_GROUND
    return _BY_MARK[mark]


def control_of(row: WiringRow) -> WiringRow:
    """The control row of the path `row` belongs to: AC_CONTROL or DC_CONTROL."""
    return AC_CONTROL if row in _AC_ROWS else DC_CONTROL


def is_control(row: WiringRow) -> bool:
    """True for DC_CONTROL and AC_CONTROL, the rows of no rail's potential."""
    return row in {DC_CONTROL, AC_CONTROL}


def _spec(row: object, value: object) -> Spec:
    if not isinstance(row, WiringRow):
        msg = f"a wiring row is fr.DC_SUPPLY, fr.AC_L1 or another row name, not {row!r}"
        raise AuthorError(msg)
    if isinstance(value, tuple) and len(value) == _TUPLE_LEN:
        return _colour(value[0]), _gauge(value[1])
    return _colour(value), None


def table(
    rows: Mapping[WiringRow, RowValue] | None, under: Mapping[WiringRow, Spec]
) -> dict[WiringRow, Spec]:
    """`rows` read and laid over `under`: a row's value is a colour, or a colour and a size."""
    found = dict(under)
    found.update({row: _spec(row, value) for row, value in (rows or {}).items()})
    return found
