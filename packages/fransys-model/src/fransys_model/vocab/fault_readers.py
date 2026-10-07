"""The RATINGS-3 per-function readers: breaking points, fault current, draw and conductive ports."""

from typing import TYPE_CHECKING
lazy from decimal import Decimal

from .enums import Current, PortRole
from .rating_readers import fitted_link_rating, function_operatings, function_rating
from .tables import ports

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Id, Model

    from .core import Function, Port
    from .ratings import BreakingPoint, Operating


def breaking_points(
    model: Model, function: Id[Function], kind: Current
) -> tuple[BreakingPoint, ...]:
    """The points `function` breaks at for `kind` of current (RATINGS-3 R5).

    A fitted link's points replace the holder's whole, even when the link states none.
    """
    link = fitted_link_rating(model, function)
    rating = function_rating(model, function) if link is None else link
    if rating is None:
        return ()
    return rating.breaking_ac if kind is Current.AC else rating.breaking_dc


def _largest(
    model: Model, function: Id[Function], read: Callable[[Operating], Decimal | None]
) -> Decimal | None:
    """The largest `read` value over `function`'s envelopes; `None` when none states it."""
    values = [read(source.operating) for source in function_operatings(model, function)]
    return max((value for value in values if value is not None), default=None)


def fault_current(model: Model, function: Id[Function], kind: Current) -> Decimal | None:
    """The largest fault current `function` states for `kind` of current (RATINGS-3 R2)."""
    if kind is Current.AC:
        return _largest(model, function, lambda o: o.fault_current_ac_a)
    return _largest(model, function, lambda o: o.fault_current_dc_a)


def fault_time_constant(model: Model, function: Id[Function]) -> Decimal | None:
    """The largest DC fault time constant, in ms, `function` states (RATINGS-3 R2)."""
    return _largest(model, function, lambda o: o.fault_time_constant_ms)


def draw(model: Model, function: Id[Function]) -> Decimal | None:
    """The largest nominal current `function` states, what a load draws (RATINGS-3 R4)."""
    return _largest(model, function, lambda o: o.nominal_current_a)


def conductive_ports(model: Model, function: Id[Function]) -> tuple[Id[Port], ...]:
    """The ports of `function` that carry current, in id order: all but its PE ports (R14)."""
    found = (
        port.id
        for port in ports(model).values()
        if port.function == function and port.role is not PortRole.PE
    )
    return tuple(sorted(found))
