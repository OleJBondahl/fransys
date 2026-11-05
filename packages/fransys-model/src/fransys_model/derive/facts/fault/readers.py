"""The RATINGS-3 per-function readers: breaking points, fault current, draw and conductive ports."""

from typing import TYPE_CHECKING
lazy from decimal import Decimal

from fransys_model.derive.facts import figures
from fransys_model.derive.facts.figures import figure
from fransys_model.derive.facts.function_ratings import fitted_link_block, fitted_link_rating, function_operatings
from fransys_model.derive.facts.rating_index import function_block
from fransys_model.derive.facts.roles import is_pe_port
from fransys_model.derive.indexes import build_indexes
from fransys_model.elecdef import Current, Unit

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.elecdef import Quantity, Range
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port
    from fransys_model.vocab.operating import Operating


def breaking_points(model: Model, function: Id[Function], kind: Current) -> tuple[Range, ...]:
    """The breaking figures `function` states at a voltage for `kind` of current.

    A fitted link's points replace the holder's whole, even when the link states none.
    """
    if fitted_link_rating(model, function) is not None:
        return figures.breaking_points(fitted_link_block(model, function), kind)
    return figures.breaking_points(function_block(model, function), kind)


def _largest(model: Model, function: Id[Function], read: Callable[[Operating], Decimal | None]) -> Decimal | None:
    """The largest `read` value over `function`'s envelopes; `None` when none states it."""
    values = [read(source.operating) for source in function_operatings(model, function)]
    return max((value for value in values if value is not None), default=None)


def _in(quantity: Quantity | None, unit: Unit) -> Decimal | None:
    return None if quantity is None else quantity.to(unit).value


def fault_current(model: Model, function: Id[Function], kind: Current) -> Decimal | None:
    """The largest fault current `function` states for `kind` of current."""
    return _largest(model, function, lambda o: figure(o.fault_current, kind, Unit.A))


def fault_time_constant(model: Model, function: Id[Function]) -> Decimal | None:
    """The largest DC fault time constant, in ms, `function` states."""
    return _largest(model, function, lambda o: _in(o.fault_time_constant, Unit.MS))


def draw(model: Model, function: Id[Function]) -> Decimal | None:
    """The largest nominal current `function` states, what a load draws."""
    return _largest(model, function, lambda o: _in(o.nominal_current, Unit.A))


def conductive_ports(model: Model, function: Id[Function]) -> tuple[Id[Port], ...]:
    """The ports of `function` that carry current, in id order: all but its PE ports."""
    found = (port for port in build_indexes(model).ports_by_function.get(function, ()) if not is_pe_port(model, port))
    return tuple(found)
