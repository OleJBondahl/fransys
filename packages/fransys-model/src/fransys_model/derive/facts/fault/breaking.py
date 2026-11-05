"""Which breaking point a protective device is checked at."""

from typing import TYPE_CHECKING, Literal

from fransys_model.derive.facts.figures import condition, value
from fransys_model.elecdef import Unit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from decimal import Decimal

    from fransys_model.elecdef import Range

type Short = Literal["voltage", "time constant"]


def _fits_tau(point: Range, tau: Decimal | None) -> bool:
    """A point with a time constant applies only at or above D's; an unknown D's, never."""
    stated = condition(point, Unit.MS)
    return stated is None or (tau is not None and stated >= tau)


def _rank(point: Range) -> tuple[Decimal | int, Decimal | int]:
    return (condition(point, Unit.V) or 0, value(point, Unit.A) or 0)


def chosen_point(points: Sequence[Range], volts: Decimal, tau: Decimal | None) -> Range | Short:
    """The point D is checked at, or what no point covers: the voltage or the time constant.

    Of the points at or above `volts` whose time constant covers `tau`, the lowest voltage wins,
    then the lowest current, so a tie errs low.
    """
    high = [point for point in points if (condition(point, Unit.V) or 0) >= volts]
    if not high:
        return "voltage"
    fits = [point for point in high if _fits_tau(point, tau)]
    if not fits:
        return "time constant"
    return min(fits, key=_rank)
