"""Validator: a function's rated voltage against the voltage across it (decision model-0079).

Codes: `RATING_VOLTAGE_BELOW_CIRCUIT`, and `RATING_CURRENT_KIND_UNSTATED` (`WARNING`): a rating that
states a voltage for one current kind only, on a function that stands on rails of the other kind.
"""

from fractions import Fraction
from typing import TYPE_CHECKING, Final

from fransys_model.derive.facts.rail_reach import (
    RailReach,
    Stand,
    ports_by_function,
    rails_by_potential,
    reach_of,
    voltage_across,
    worst_stand,
)
from fransys_model.derive.facts.stated_ratings import function_ratings, rating_source_label
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import voltage
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_model.derive.facts.stated_ratings import FunctionRating
    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Function

RATING_VOLTAGE_BELOW_CIRCUIT: Final[str] = "RATING_VOLTAGE_BELOW_CIRCUIT"
RATING_CURRENT_KIND_UNSTATED: Final[str] = "RATING_CURRENT_KIND_UNSTATED"


def _message(function: Function, limit: Decimal, stand: Stand, source: str) -> str:
    """Name the function, its rating and its source, the rails and V, and say when IT applied."""
    first = stand.rails[0]
    kind = "AC" if first.ac else "DC"
    where = f"function {ref(function)}"
    text = f"{where} is rated {limit:f} V {kind} ({source}), but "
    volt = voltage.show(stand.volt)
    if len(stand.rails) == 1:
        text += f"rail {first.name!r} is at {volt} V to earth"
        return text + (f" (IT supply {first.supply!r})" if first.it else "")
    second = stand.rails[1]
    text += f"rails {first.name!r} and {second.name!r} stand across it at {volt} V"
    if voltage.common_reference(first, second):
        return text
    if first.it or second.it:
        return text + " (IT: no common reference, the sum of their voltages to earth)"
    return text + " (two AC supplies, no fixed phase: the sum of their voltages to earth)"


def _finding(
    function: Function, limit: Decimal, stands: list[Stand], source: str
) -> Finding | None:
    rating = Fraction(limit)
    firing = [s for s in stands if voltage.exceeds(s.volt, rating)]
    if not firing:
        return None
    worst = worst_stand(firing)
    return Finding(
        code=RATING_VOLTAGE_BELOW_CIRCUIT,
        severity=Severity.ERROR,
        subjects=(function.id,),
        message=_message(function, limit, worst, source),
    )


def _source_findings(
    function: Function, source: FunctionRating, label: str, reach: RailReach
) -> list[Finding]:
    found: list[Finding] = []
    for ac, limit in (
        (True, source.rating.voltage_ac_v),
        (False, source.rating.voltage_dc_v),
    ):
        if limit is None:
            continue
        stands = reach.stands(ac=ac)
        if stands is None:
            continue
        finding = _finding(function, limit, stands, label)
        if finding is not None:
            found.append(finding)
    return found


def _kind_finding(
    function: Function, source: FunctionRating, label: str, reach: RailReach
) -> Finding | None:
    """A WARNING when the rating states one voltage kind and the function stands on the other."""
    rating = source.rating
    stated_ac = rating.voltage_ac_v is not None
    if stated_ac == (rating.voltage_dc_v is not None):
        return None
    stand = voltage_across(reach, ac=not stated_ac)
    if stand is None or voltage.magnitude(stand.volt) == 0:
        return None
    have, other = ("AC", "DC") if stated_ac else ("DC", "AC")
    names = ", ".join(rail.name for rail in stand.rails)
    where = f"{other} rail{'s' if len(stand.rails) > 1 else ''} {names}"
    return Finding(
        code=RATING_CURRENT_KIND_UNSTATED,
        severity=Severity.WARNING,
        subjects=(function.id,),
        message=(
            f"{ref(function)} states a {have} rating only ({label}) and stands on {where} at "
            f"{voltage.show(stand.volt)} V: state voltage_{other.lower()}_v in its part, "
            f"or use a part rated for {other}"
        ),
    )


def check_ratings(model: Model) -> tuple[Finding, ...]:
    """Check that no function is rated for less voltage than stands across it.

    `RATING_VOLTAGE_BELOW_CIRCUIT` (`ERROR`), one per function, current kind and rating source,
    when V is strictly above the rating. V: highest voltage that can stand at once, else to earth.
    """
    lookup = rails_by_potential(model)
    if not lookup:
        return ()
    ports_of = ports_by_function(model)
    found: list[Finding] = []
    for function in functions(model).values():
        sources = function_ratings(model, function.id)
        if not sources:
            continue
        reach = reach_of(model, function.id, lookup, ports_of)
        for source in sources:
            label = rating_source_label(model, source)
            found += _source_findings(function, source, label, reach)
            kind = _kind_finding(function, source, label, reach)
            if kind is not None:
                found.append(kind)
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
