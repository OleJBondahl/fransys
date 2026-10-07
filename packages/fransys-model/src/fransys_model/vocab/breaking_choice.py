"""Which breaking point a protective device is checked at (RATINGS-3 R10, R11)."""

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence
    from decimal import Decimal

    from .ratings import BreakingPoint

type Short = Literal["voltage", "time constant"]


def _fits_tau(point: BreakingPoint, tau: Decimal | None) -> bool:
    """A point with a time constant applies only at or above D's; an unknown D's, never."""
    if point.time_constant_ms is None:
        return True
    return tau is not None and point.time_constant_ms >= tau


def chosen_point(
    points: Sequence[BreakingPoint], volts: Decimal, tau: Decimal | None
) -> BreakingPoint | Short:
    """The point D is checked at, or what no point covers: the voltage or the time constant.

    Of the points at or above `volts` whose time constant covers `tau`, the lowest voltage wins,
    then the lowest current, so a tie errs low.
    """
    high = [point for point in points if point.voltage_v >= volts]
    if not high:
        return "voltage"
    fits = [point for point in high if _fits_tau(point, tau)]
    if not fits:
        return "time constant"
    return min(fits, key=lambda point: (point.voltage_v, point.current_a))
