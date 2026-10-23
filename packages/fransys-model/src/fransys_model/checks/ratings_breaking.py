"""Validator: a protective device's breaking point against the prospective fault.

Codes: `RATING_BREAKING_BELOW_FAULT`, `RATING_BREAKING_NO_DATA`.
"""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.fault.breaking import chosen_point
from fransys_model.derive.facts.fault.prospective import ProspectiveFault, prospective_fault
from fransys_model.derive.facts.fault.readers import breaking_points
from fransys_model.derive.facts.rail_reach import function_reach, voltage_across
from fransys_model.derive.facts.roles import function_role
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import voltage
from fransys_model.vocab.enums import Current
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import supply_systems

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function
    from fransys_model.vocab.ratings import BreakingPoint
    from fransys_model.vocab.voltage import Volt

RATING_BREAKING_BELOW_FAULT: Final[str] = "RATING_BREAKING_BELOW_FAULT"
RATING_BREAKING_NO_DATA: Final[str] = "RATING_BREAKING_NO_DATA"


def _point_text(point: BreakingPoint, kind: Current) -> str:
    tau = "" if point.time_constant_ms is None else f" at {point.time_constant_ms:f} ms"
    return f"{point.current_a:f} A {kind.name} at {point.voltage_v:f} V{tau}"


def _sources(model: Model, fault: ProspectiveFault) -> str:
    """The sources counted: source functions by name, declared supplies by supply name."""
    named = [f"function {ref(f)}" for f in fault.functions]
    named += [f"supply {supply_systems(model)[s].name!r}" for s in fault.supplies]
    return ", ".join(named) or "none"


def _below(
    model: Model, function: Id[Function], fault: ProspectiveFault, point: BreakingPoint
) -> str:
    return (
        f"function {ref(function)} breaks {_point_text(point, fault.kind)}, "
        f"below the prospective {fault.current_a:f} A {fault.kind.name} "
        f"from {_sources(model, fault)}"
    )


def _no_data(function: Id[Function], fault: ProspectiveFault, volts: str, short: str) -> str:
    tau = fault.time_constant_ms
    if short == "voltage":
        why = f"no point is rated for the circuit voltage of {volts} V"
    else:
        known = "unknown" if tau is None else f"{tau:f} ms"
        why = f"no point covers the time constant of the sources, {known}"
    return f"function {ref(function)} states breaking points for {fault.kind.name}, but {why}"


def _finding(
    model: Model, function: Id[Function], fault: ProspectiveFault, current: Decimal, volt: Volt
) -> Finding | None:
    """The finding for `function` at `fault`, or `None` when its point holds."""
    points = breaking_points(model, function, fault.kind)
    if not points:
        return None
    choice = chosen_point(points, voltage.magnitude(volt), fault.time_constant_ms)
    if isinstance(choice, str):
        message = _no_data(function, fault, voltage.show(volt), choice)
        return finding(RATING_BREAKING_NO_DATA, Severity.WARNING, (function,), message)
    if choice.current_a < current:
        message = _below(model, function, fault, choice)
        return finding(RATING_BREAKING_BELOW_FAULT, Severity.ERROR, (function,), message)
    return None


def check_breaking(model: Model) -> tuple[Finding, ...]:
    """Check each protective device's breaking point against the prospective fault current.

    `BELOW_FAULT` (`ERROR`): the chosen point is below it. `NO_DATA` (`WARNING`): none fits.
    An unknown current, no source counted (0 A), no points or no voltage is silent.
    """
    found: dict[tuple[Id[Function], Current, str], Finding] = {}
    for fault in prospective_fault(model):
        if fault.current_a is None or not (fault.functions or fault.supplies):
            continue  # unknown, or no source counted (0 A): silent here, the other rule's matter
        for function in fault.position.functions:
            if not function_role(model, function).protects:
                continue
            stand = voltage_across(function_reach(model, function), ac=fault.kind is Current.AC)
            if stand is None:  # no rail of this kind: no voltage to choose a point by
                continue
            one = _finding(model, function, fault, fault.current_a, stand.volt)
            if one is not None:
                found.setdefault((function, fault.kind, one.message), one)
    return ordered(found.values())
