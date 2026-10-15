"""Wire rows: the IEC 60204-1 default table and a scope's table; the rows are `fransys_model`'s."""

from typing import TYPE_CHECKING, Final
lazy from decimal import Decimal

from fransys_author.errors import AuthorError
from fransys_author.surface._wire import _colour, _gauge
from fransys_model.vocab import WiringRow

if TYPE_CHECKING:
    from collections.abc import Mapping

_TUPLE_LEN = 2


DC_SUPPLY: Final = WiringRow.DC_SUPPLY
DC_GROUND: Final = WiringRow.DC_GROUND
DC_CONTROL: Final = WiringRow.DC_CONTROL
DC_SIGNAL: Final = WiringRow.DC_SIGNAL
AC_L1: Final = WiringRow.AC_L1
AC_L2: Final = WiringRow.AC_L2
AC_L3: Final = WiringRow.AC_L3
AC_N: Final = WiringRow.AC_N
AC_CONTROL: Final = WiringRow.AC_CONTROL

type RowValue = str | tuple[str, float | str | Decimal]
type Spec = tuple[str, Decimal | None]

IEC: Final[Mapping[WiringRow, Spec]] = {
    **dict.fromkeys((AC_L1, AC_L2, AC_L3), ("BK", None)),
    AC_N: ("BU", None),
    AC_CONTROL: ("RD", None),
    **dict.fromkeys((DC_SUPPLY, DC_CONTROL, DC_GROUND, DC_SIGNAL), ("BU", None)),
}


def _spec(row: object, value: object) -> Spec:
    if not isinstance(row, WiringRow):
        msg = f"a wiring row is fr.DC_SUPPLY, fr.AC_L1 or another row name, not {row!r}"
        raise AuthorError(msg)
    if isinstance(value, int | float | Decimal) and not isinstance(value, bool):
        msg = (
            f"row {row} value {value} is a bare number, a size; "
            f'give (colour, size) such as ("BK", {value})'
        )
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
