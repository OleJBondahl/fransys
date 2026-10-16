"""Validator: a function's rated current against its branch's bound (model-0088).

Codes: `RATING_CURRENT_BELOW_BRANCH`, `LOAD_ABOVE_LIMIT`, `LOADS_ABOVE_LIMIT`.
"""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._natural_join import natural_join
from fransys_model.derive.facts.current.bounds import CurrentBound, LimitRole, highest
from fransys_model.derive.facts.current.chains import chains_unordered
from fransys_model.derive.facts.current.load_limits import LoadLimit, load_limits
from fransys_model.derive.facts.rail_reach import rails_by_potential, reached_kinds
from fransys_model.derive.facts.stated_ratings import function_ratings, rating_source_label
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.enums import Current
from fransys_model.vocab.finding_ref import ref

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port

type _Key = tuple[Id[Function], tuple[Id[Port], ...], Current]

RATING_CURRENT_BELOW_BRANCH: Final[str] = "RATING_CURRENT_BELOW_BRANCH"
LOAD_ABOVE_LIMIT: Final[str] = "LOAD_ABOVE_LIMIT"
LOADS_ABOVE_LIMIT: Final[str] = "LOADS_ABOVE_LIMIT"


def _worst_bounds(model: Model) -> dict[tuple[Id[Function], Current], CurrentBound]:
    """Per function and kind, the largest bound of any position the function sits in.

    A function in several positions (a relay pole with two links, a mate with several pins) is
    compared with the loosest bound, the worst gap; the choice is `bounds.highest`.
    """
    found: dict[tuple[Id[Function], Current], list[CurrentBound]] = {}
    for chain in chains_unordered(model):
        for position in chain.positions:
            for function in position.functions:
                for bound in position.bounds:
                    found.setdefault((function, bound.kind), []).append(bound)
    return {key: highest(bounds) for key, bounds in found.items()}


def _setter(bound: CurrentBound) -> str:
    """Name what set `bound`: the source, or the protective device, with its function and item."""
    what = "the source" if bound.role is LimitRole.SOURCE else "the protective device"
    return f"{what} of {_named(bound.by)}"


def _states(bound: CurrentBound) -> str:
    """`, with item K at rest`: the item states that give `bound`; nothing when none is involved."""
    named = [
        f"item {ref(item)} {'at rest' if state == 'rest' else 'operated'}"
        for item, state in bound.states
    ]
    return f", with {' and '.join(named)}" if named else ""


def _named(function: Id[Function]) -> str:
    return f"function {ref(function)}"


def check_ratings_current(model: Model) -> tuple[Finding, ...]:
    """Check that no function is rated for less current than its branch can carry.

    `RATING_CURRENT_BELOW_BRANCH` (`ERROR`), one per function, current kind and source, when the
    rating is strictly below the bound; sorted by `(code, subjects, message)`.
    """
    if not rails_by_potential(model):
        return ()
    bounds = _worst_bounds(model)
    reached = reached_kinds(model)
    found: list[Finding] = []
    for (function, kind), bound in bounds.items():
        if kind not in reached.get(function, ()):
            continue
        for source in function_ratings(model, function):
            rated = source.rating.current_ac_a if kind is Current.AC else source.rating.current_dc_a
            if rated is None or rated >= bound.value:
                continue
            label = rating_source_label(model, source)
            found.append(
                Finding(
                    code=RATING_CURRENT_BELOW_BRANCH,
                    severity=Severity.ERROR,
                    subjects=(function,),
                    message=(
                        f"{_named(function)} is rated {rated:f} A {kind.name} ({label}), "
                        f"below its branch's {bound.value:f} A {kind.name} "
                        f"set by {_setter(bound)}{_states(bound)}"
                    ),
                )
            )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))


def _bounded(model: Model) -> list[tuple[LoadLimit, CurrentBound]]:
    """The load entries that have a limit, each paired with it."""
    return [(entry, entry.bound) for entry in load_limits(model) if entry.bound is not None]


def _above_alone(entries: list[tuple[LoadLimit, CurrentBound]]) -> list[Finding]:
    """`LOAD_ABOVE_LIMIT`, one per function, current kind and setter, for a draw above its limit."""
    seen: dict[tuple[Id[Function], Current, Id[Function]], Finding] = {}
    for load, bound in entries:
        if load.draw_a > bound.value:
            message = (
                f"{_named(load.function)} draws {load.draw_a:f} A {load.kind.name}, "
                f"above its limit of {bound.value:f} A {load.kind.name} "
                f"set by {_setter(bound)}{_states(bound)}"
            )
            seen.setdefault(
                (load.function, load.kind, bound.by),
                Finding(
                    code=LOAD_ABOVE_LIMIT,
                    severity=Severity.ERROR,
                    subjects=(load.function,),
                    message=message,
                ),
            )
    return list(seen.values())


def _together(entries: list[tuple[LoadLimit, CurrentBound]]) -> list[Finding]:
    """`LOADS_ABOVE_LIMIT`: per limit (setter, pole ports, kind), loads above it only together."""
    groups: dict[_Key, dict[Id[Function], LoadLimit]] = {}
    firsts: dict[_Key, CurrentBound] = {}
    for load, bound in entries:
        key = (bound.by, bound.ports, bound.kind)
        groups.setdefault(key, {}).setdefault(load.function, load)
        firsts.setdefault(key, bound)
    found: list[Finding] = []
    for key, members in groups.items():
        bound, total = firsts[key], sum(load.draw_a for load in members.values())
        if total <= bound.value or any(load.draw_a > bound.value for load in members.values()):
            continue
        named = natural_join(f"{_named(f)} {members[f].draw_a:f} A" for f in members)
        message = (
            f"loads {named} draw {total:f} A {bound.kind.name} together, above the limit of "
            f"{bound.value:f} A {bound.kind.name} set by {_setter(bound)}"
            f"{_states(bound)}"
        )
        found.append(
            Finding(
                code=LOADS_ABOVE_LIMIT,
                severity=Severity.WARNING,
                subjects=tuple(sorted(members)),
                message=message,
            )
        )
    return found


def check_load_draw(model: Model) -> tuple[Finding, ...]:
    """Check each load's stated draw against the limit that bounds it.

    `LOAD_ABOVE_LIMIT` (`ERROR`) for a draw above its limit; `LOADS_ABOVE_LIMIT` (`WARNING`) when
    the loads of one limit sum above it and none is above it alone.
    """
    entries = _bounded(model)
    found = [*_above_alone(entries), *_together(entries)]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
