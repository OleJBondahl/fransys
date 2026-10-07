"""The limits a current path states and the law that says which position they bound (RATINGS-2).

The law (spec C3): a limit bounds a device when every loop through the device that holds a source
also passes through the limit. The positions and the edges to the outside form a multigraph; a
loop is a simple cycle, and every cycle lies in one block (`current_blocks`). In a block of two
or more edges any two edges lie on a common simple cycle, so `block_bounds` answers exactly, with
no cycle enumeration: a cycle through `D` that holds a source exists iff the block holds a source
edge, and a limit `L` is avoided by such a cycle iff the block of `D` in the block minus `L`
still holds two edges and a source edge.
"""

import dataclasses
from enum import Enum
from typing import TYPE_CHECKING
lazy from decimal import Decimal

from fransys_model.vocab.energy_flow import gives_energy
from fransys_model.vocab.enums import Current, FunctionKind
from fransys_model.vocab.rating_readers import function_operatings, function_ratings
from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.contacts import LinkState
lazy from fransys_model.vocab.core import Function, Item, Port

from .current_blocks import blocks

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterable, Sequence

    from fransys_model.kernel import Model


class LimitRole(Enum):
    """What set a bound: a source's continuous limit, or a full-range protective device."""

    PROTECTION = "protection"
    SOURCE = "source"


@dataclasses.dataclass(frozen=True, slots=True)
class CurrentBound:
    """The most continuous current of `kind` that reaches a position: `value`, set by `by`.

    `states` names the items the bound depends on: among the item assignments that give this
    same bound (value, setter and role), the (item, `rest` or `operated`) of each enumerated
    item that is in the same state in ALL of them (`current_states`), sorted by item id. An item
    that varies between such assignments does not matter and is not named; empty when none does.
    `ports` are the two end ports of the position whose limit set the bound.
    """

    kind: Current
    value: Decimal
    by: Id[Function]
    role: LimitRole
    states: tuple[tuple[Id[Item], LinkState], ...] = ()
    ports: tuple[Id[Port], ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Tie:
    """One position: the functions it passes through, the limits they state, a source or not."""

    functions: tuple[Id[Function], ...]
    limits: tuple[CurrentBound, ...]
    source: bool


def _limits_of(
    model: Model, function: Id[Function], ports: tuple[Id[Port], ...] = ()
) -> list[CurrentBound]:
    """The limits `function` states: a source's `max_current_*`, a full-range fuse's rating."""
    found: list[CurrentBound] = []
    for envelope in function_operatings(model, function):
        found += _bounds(
            function,
            LimitRole.SOURCE,
            envelope.operating.max_current_ac_a,
            envelope.operating.max_current_dc_a,
            ports,
        )
    ratings = [stated.rating for stated in function_ratings(model, function)]
    # Partial-range is a fact of the function: one rating with a minimum breaking current
    # (part, template or a unit's boundary) makes all of its rating currents bound nothing.
    partial = any(rating.min_breaking_current_a is not None for rating in ratings)
    if functions(model)[function].kind is FunctionKind.PROTECTION and not partial:
        for rating in ratings:
            found += _bounds(
                function, LimitRole.PROTECTION, rating.current_ac_a, rating.current_dc_a, ports
            )
    return found


def _bounds(
    function: Id[Function],
    role: LimitRole,
    ac: Decimal | None,
    dc: Decimal | None,
    ports: tuple[Id[Port], ...],
) -> list[CurrentBound]:
    return [
        CurrentBound(kind=kind, value=value, by=function, role=role, ports=ports)
        for kind, value in ((Current.AC, ac), (Current.DC, dc))
        if value is not None
    ]


def tie_of(model: Model, stated: Sequence[Id[Function]], ports: tuple[Id[Port], ...] = ()) -> Tie:
    """The position through `stated`; it holds a source when one gives energy or has a limit."""
    limits = [limit for function in stated for limit in _limits_of(model, function, ports)]
    gives = any(gives_energy(model, function) for function in stated)
    return Tie(
        functions=tuple(stated),
        limits=tuple(limits),
        source=gives or any(limit.role is LimitRole.SOURCE for limit in limits),
    )


def _holds_source(members: Sequence[int], ties: Sequence[Tie | None]) -> bool:
    """Whether the block `members` (two edges or more) holds a source; `None` is the outside."""
    return len(members) >= 2 and any(  # noqa: PLR2004 -- the docstring's own "two edges or more", not an arbitrary constant
        tie is None or tie.source for tie in (ties[at] for at in members)
    )


def block_bounds[V: Hashable](
    block: frozenset[int], ends: Sequence[tuple[V, V]], ties: Sequence[Tie | None]
) -> dict[int, tuple[CurrentBound, ...]]:
    """The bounds of every position in `block`, by edge index; the outside (`None`) has none.

    A block with one edge or no source edge bounds nothing; else `L` bounds `D` when `L` is `D` or
    `D` has no source-holding cycle without `L`. Each gets the tightest limit per kind.
    """
    found: dict[int, list[CurrentBound]] = {at: [] for at in block if ties[at] is not None}
    if _holds_source(sorted(block), ties):
        for limiter in sorted(block):
            tie = ties[limiter]
            if tie is None or not tie.limits:
                continue
            rest = sorted(block - {limiter})
            free = {
                rest[at]: _holds_source([rest[i] for i in part], ties)
                for part in blocks([ends[at] for at in rest])
                for at in part
            }
            for device, limits in found.items():
                if device == limiter or not free[device]:
                    limits.extend(tie.limits)
    return {device: tightest(limits) for device, limits in found.items()}


def tightest(limits: Sequence[CurrentBound]) -> tuple[CurrentBound, ...]:
    """The smallest limit per kind, AC before DC; ties by role name, then function id."""
    return tuple(
        min(
            (limit for limit in limits if limit.kind is kind),
            key=lambda limit: (limit.value, limit.role.value, limit.by, limit.ports),
        )
        for kind in Current
        if any(limit.kind is kind for limit in limits)
    )


def highest(bounds: Iterable[CurrentBound]) -> CurrentBound:
    """The highest of `bounds`, the one choice both `current_states` and the check make.

    The largest value; equal values by role name, then function id, as `tightest` orders them,
    then by `states` and `ports`, so the choice never depends on the order of `bounds`.
    """
    return min(bounds, key=lambda b: (-b.value, b.role.value, b.by, b.states, b.ports))
