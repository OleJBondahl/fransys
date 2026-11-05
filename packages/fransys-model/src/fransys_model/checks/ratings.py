"""Validator: a function's rated voltage against the voltage across it (decision model-0079).

Codes: `RATING_VOLTAGE_BELOW_CIRCUIT`, and `RATING_CURRENT_KIND_UNSTATED` (`WARNING`): a rating that
states a voltage for one current kind only, on a function that stands on rails of the other kind.
"""

from fractions import Fraction
from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.figures import figure
from fransys_model.derive.facts.function_ratings import RATING_SOURCE_LABEL, function_ratings
from fransys_model.derive.facts.rail_reach import (
    RailReach,
    Stand,
    function_reach,
    rails_by_potential,
    voltage_across,
    worst_stand,
)
from fransys_model.elecdef import Current, Unit
from fransys_model.vocab import voltage
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_model.derive.facts.function_ratings import FunctionRating
    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Function

RATING_VOLTAGE_BELOW_CIRCUIT: Final[str] = "RATING_VOLTAGE_BELOW_CIRCUIT"
RATING_CURRENT_KIND_UNSTATED: Final[str] = "RATING_CURRENT_KIND_UNSTATED"


def _message(function: Function, limit: Decimal, stand: Stand, source: str) -> str:
    """Name the function, its rating and its source, the rails and V."""
    first = stand.rails[0]
    kind = "AC" if first.ac else "DC"
    where = f"function {ref(function)}"
    text = f"{where} is rated {limit:f} V {kind} ({source}), but "
    volt = voltage.show(stand.volt)
    if len(stand.rails) == 1:
        return text + f"rail {first.name!r} is at {volt} V to earth"
    second = stand.rails[1]
    text += f"rails {first.name!r} and {second.name!r} stand across it at {volt} V"
    if voltage.common_reference(first, second):
        return text
    return text + " (two AC supplies, no fixed phase: the sum of their voltages to earth)"


def _voltage_finding(function: Function, limit: Decimal, stands: list[Stand], source: str) -> Finding | None:
    rating = Fraction(limit)
    firing = [s for s in stands if voltage.exceeds(s.volt, rating)]
    if not firing:
        return None
    worst = worst_stand(firing)
    message = _message(function, limit, worst, source)
    return finding(RATING_VOLTAGE_BELOW_CIRCUIT, (function.id,), message)


def _source_findings(function: Function, source: FunctionRating, label: str, reach: RailReach) -> list[Finding]:
    found: list[Finding] = []
    for ac, limit in (
        (True, figure(source.rating.voltage, Current.AC, Unit.V)),
        (False, figure(source.rating.voltage, Current.DC, Unit.V)),
    ):
        if limit is None:
            continue
        stands = reach.stands(ac=ac)
        if stands is None:
            continue
        found_one = _voltage_finding(function, limit, stands, label)
        if found_one is not None:
            found.append(found_one)
    return found


def _kind_finding(function: Function, source: FunctionRating, label: str, reach: RailReach) -> Finding | None:
    """A WARNING when the rating states one voltage kind and the function stands on the other."""
    rating = source.rating
    stated_ac = figure(rating.voltage, Current.AC, Unit.V) is not None
    if stated_ac == (figure(rating.voltage, Current.DC, Unit.V) is not None):
        return None
    stand = voltage_across(reach, ac=not stated_ac)
    if stand is None or voltage.magnitude(stand.volt) == 0:
        return None
    have, other = ("AC", "DC") if stated_ac else ("DC", "AC")
    names = ", ".join(rail.name for rail in stand.rails)
    where = f"{other} rail{'s' if len(stand.rails) > 1 else ''} {names}"
    message = (
        f"{ref(function)} states a {have} rating only ({label}) and stands on {where} at "
        f'{voltage.show(stand.volt)} V: state voltage = [{{ nom = "<n> V", at = ["{other}"] }}] in its [rating], '
        f"or use a part rated for {other}"
    )
    return finding(RATING_CURRENT_KIND_UNSTATED, (function.id,), message)


def check_ratings(model: Model) -> tuple[Finding, ...]:
    """Check that no function is rated for less voltage than stands across it.

    `RATING_VOLTAGE_BELOW_CIRCUIT` (`ERROR`), one per function, current kind and rating source,
    when V is strictly above the rating. V: highest voltage that can stand at once, else to earth.
    """
    if not rails_by_potential(model):
        return ()
    found: list[Finding] = []
    for function in functions(model).values():
        sources = function_ratings(model, function.id)
        if not sources:
            continue
        reach = function_reach(model, function.id)
        for source in sources:
            label = RATING_SOURCE_LABEL
            found += _source_findings(function, source, label, reach)
            kind = _kind_finding(function, source, label, reach)
            if kind is not None:
                found.append(kind)
    return ordered(found)
