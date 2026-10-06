"""Validator: a function's rated current against its branch's bound (RATINGS-2 C4, model-0088).

Codes: `RATING_CURRENT_BELOW_BRANCH`.
"""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.closure import port_rails
from fransys_model.vocab.current_bounds import CurrentBound, LimitRole, highest
from fransys_model.vocab.current_chains import chains_unordered
from fransys_model.vocab.enums import Current
from fransys_model.vocab.rating_readers import function_ratings
from fransys_model.vocab.tables import functions, items, ports, units

from .ratings import _rails_by_potential

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function

RATING_CURRENT_BELOW_BRANCH: Final[str] = "RATING_CURRENT_BELOW_BRANCH"


def _worst_bounds(model: Model) -> dict[tuple[Id[Function], Current], CurrentBound]:
    """Per function and kind, the largest bound of any position the function sits in.

    A function in several positions (a relay pole with two links, a mate with several pins) is
    compared with the loosest bound, the worst gap; the choice is `current_bounds.highest`.
    """
    found: dict[tuple[Id[Function], Current], list[CurrentBound]] = {}
    for chain in chains_unordered(model):
        for position in chain.positions:
            for function in position.functions:
                for bound in position.bounds:
                    found.setdefault((function, bound.kind), []).append(bound)
    return {key: highest(bounds) for key, bounds in found.items()}


def _reached_kinds(model: Model) -> dict[Id[Function], set[Current]]:
    """The current kinds of the rails the ports of each function carry."""
    lookup = _rails_by_potential(model)
    reached: dict[Id[Function], set[Current]] = {}
    for port in ports(model).values():
        kinds = reached.setdefault(port.function, set())
        for name in port_rails(model, port.id):
            if name in lookup:
                kinds.add(Current.AC if lookup[name].ac else Current.DC)
    return reached


def _setter(model: Model, bound: CurrentBound) -> str:
    """Name what set `bound`: the source, or the protective device, with its function and item."""
    what = "the source" if bound.role is LimitRole.SOURCE else "the protective device"
    return f"{what} of {_named(model, bound.by)}"


def _states(model: Model, bound: CurrentBound) -> str:
    """`, with item K at rest`: the item states that give `bound`; nothing when none is involved."""
    named = [
        f"item {'/'.join(items(model)[item].key)} {'at rest' if state == 'rest' else 'operated'}"
        for item, state in bound.states
    ]
    return f", with {' and '.join(named)}" if named else ""


def _named(model: Model, function: Id[Function]) -> str:
    record = functions(model)[function]
    return f"function {record.name!r} of item {'/'.join(items(model)[record.item].key)}"


def check_ratings_current(model: Model) -> tuple[Finding, ...]:
    """Check that no function is rated for less current than its branch can carry.

    `RATING_CURRENT_BELOW_BRANCH` (`ERROR`), one per function, current kind and source, when the
    rating is strictly below the bound; sorted by `(code, subjects, message)`.
    """
    if not _rails_by_potential(model):
        return ()
    bounds = _worst_bounds(model)
    reached = _reached_kinds(model)
    unit_of = units(model)
    found: list[Finding] = []
    for (function, kind), bound in bounds.items():
        if kind not in reached.get(function, ()):
            continue
        for source in function_ratings(model, function):
            rated = source.rating.current_ac_a if kind is Current.AC else source.rating.current_dc_a
            if rated is None or rated >= bound.value:
                continue
            label = (
                "part or template rating"
                if source.unit is None
                else f"boundary rating of unit {key_text(unit_of[source.unit])}"
            )
            found.append(
                Finding(
                    code=RATING_CURRENT_BELOW_BRANCH,
                    severity=Severity.ERROR,
                    subjects=(function,),
                    message=(
                        f"{_named(model, function)} is rated {rated:f} A {kind.name} ({label}), "
                        f"below its branch's {bound.value:f} A {kind.name} "
                        f"set by {_setter(model, bound)}{_states(model, bound)}"
                    ),
                )
            )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
