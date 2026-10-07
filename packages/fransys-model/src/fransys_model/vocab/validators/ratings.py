"""Validator: a function's rated voltage against the voltage across it (decision model-0079).

Codes: `RATING_VOLTAGE_BELOW_CIRCUIT`.
"""

from fractions import Fraction
from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab import voltage
from fransys_model.vocab.rail_reach import (
    RailReach,
    Stand,
    ports_by_function,
    rails_by_potential,
    reach_of,
    worst_stand,
)
from fransys_model.vocab.rating_readers import function_ratings
from fransys_model.vocab.tables import functions, items, units

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Item, Unit
    from fransys_model.vocab.rating_readers import FunctionRating

RATING_VOLTAGE_BELOW_CIRCUIT: Final[str] = "RATING_VOLTAGE_BELOW_CIRCUIT"


def _message(function: Function, item: Item, limit: Decimal, stand: Stand, source: str) -> str:
    """Name the function, its rating and its source, the rails and V, and say when IT applied."""
    first = stand.rails[0]
    kind = "AC" if first.ac else "DC"
    where = f"function {function.name!r} of item {'/'.join(item.key)}"
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
    function: Function, item: Item, limit: Decimal, stands: list[Stand], source: str
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
        message=_message(function, item, limit, worst, source),
    )


def _source_label(source: FunctionRating, unit_of: Mapping[Id[Unit], Unit]) -> str:
    if source.unit is None:
        return "part or template rating"
    return f"boundary rating of unit {key_text(unit_of[source.unit])}"


def _source_findings(
    function: Function, item: Item, source: FunctionRating, label: str, reach: RailReach
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
        finding = _finding(function, item, limit, stands, label)
        if finding is not None:
            found.append(finding)
    return found


def check_ratings(model: Model) -> tuple[Finding, ...]:
    """Check that no function is rated for less voltage than stands across it.

    `RATING_VOLTAGE_BELOW_CIRCUIT` (`ERROR`), one per function, current kind and rating source,
    when V is strictly above the rating. V: highest voltage that can stand at once, else to earth.
    """
    lookup = rails_by_potential(model)
    if not lookup:
        return ()
    ports_of = ports_by_function(model)
    item_of = items(model)
    unit_of = units(model)
    found: list[Finding] = []
    for function in functions(model).values():
        sources = function_ratings(model, function.id)
        if not sources:
            continue
        reach = reach_of(model, function.id, lookup, ports_of)
        for source in sources:
            label = _source_label(source, unit_of)
            item = item_of[function.item]
            found += _source_findings(function, item, source, label, reach)
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
