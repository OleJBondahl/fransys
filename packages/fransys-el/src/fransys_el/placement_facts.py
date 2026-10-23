"""`Facts` (facts 6, 11, 12): keep-whole sets, units with their boundary, mates."""

from typing import TYPE_CHECKING

from fransys_layout.core import Facts, Unit, natural_key
from fransys_model.derive import (
    function_ports,
    item_functions,
    keep_whole_sets,
    mate_ports,
    unit_boundary_pins,
    unit_chain,
    unit_ids,
)
from fransys_model.kernel import render_id

from .kit_keys import function_of
from .placement_env import drawn_pins, pin_ref
from .placement_series import bridges_of, series_of, trees
from .placement_skips import FUNCTION_UNWIRED, FUNCTION_WITHOUT_SYMBOL, Skipped, in_order

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_layout.core import Sym
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function
    from fransys_model.vocab import Unit as UnitRecord

    from .placement_env import Env

__all__ = ["facts_of"]


def _sorted_sets(found: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    """The sets with two symbols or more, once each, in natural order."""
    kept = {s for s in found if len(s) >= 2}  # noqa: PLR2004 - one symbol is nothing to keep whole
    return tuple(sorted(kept, key=lambda s: sorted(natural_key(i) for i in s)))


def _drawn_by(env: Env) -> dict[Id[Function], set[str]]:
    """Each drawn function with its symbols: a connector's are its pins' (el-0014, el-0053)."""
    found: dict[Id[Function], set[str]] = {}
    for key, symbol in env.owner.items():
        found.setdefault(function_of(env.model, key), set()).add(symbol)
    return found


def _owners(
    drawn_by: dict[Id[Function], set[str]], drawn: Iterable[Id[Function]]
) -> frozenset[str]:
    """The symbols that draw `drawn`; a function with no symbol is left out."""
    return frozenset(s for f in drawn for s in drawn_by.get(f, ()))


def _why(env: Env, function: Id[Function]) -> str:
    """Unwired when no pin of the function is drawn (R364), else it has no symbol (el-0053)."""
    own = function_ports(env.model, function)
    return FUNCTION_UNWIRED if own and set(own) <= env.undrawn else FUNCTION_WITHOUT_SYMBOL


def _function_sets(env: Env) -> list[frozenset[Id[Function]]]:
    """Each `keep_whole_sets` set as functions: item sets expanded to the items' functions."""
    sets = keep_whole_sets(env.model)
    of_item = item_functions(env.model)
    items_sets = [*sets.item_boxes, *sets.line_units]
    expanded = [frozenset(f for i in s for f in of_item.get(i, ())) for s in items_sets]
    return [*expanded, *(frozenset(s) for s in sets.pole_groups)]


def keep_whole(env: Env) -> tuple[tuple[frozenset[str], ...], tuple[Skipped, ...]]:
    """Fact 11: each set as symbol ids (under two symbols is dropped), and the functions lost."""
    sets = _function_sets(env)
    drawn_by = _drawn_by(env)
    lost = {
        Skipped("function", render_id(f), _why(env, f))
        for s in sets
        for f in s
        if f not in drawn_by and f not in env.spare
    }
    return _sorted_sets([_owners(drawn_by, s) for s in sets]), in_order(lost)


def _parent(env: Env, unit: Id[UnitRecord]) -> str | None:
    """The unit's parent id text, read from `unit_chain`, or `None` at the top."""
    chain = unit_chain(env.model, unit)
    return chain[1].value if len(chain) > 1 else None


def units_of(env: Env) -> tuple[Unit, ...]:
    """Fact 12: each unit with its parent and its boundary pins, in natural order of id."""
    found = [
        Unit(
            u.value,
            _parent(env, u),
            drawn_pins(env, unit_boundary_pins(env.model, u)),
        )
        for u in unit_ids(env.model)
    ]
    return tuple(sorted(found, key=lambda u: natural_key(u.id)))


def facts_of(env: Env, syms: Sequence[Sym]) -> tuple[Facts, tuple[Skipped, ...]]:
    """The `Facts`, and the functions the keep-whole sets lost for want of a symbol."""
    pairs = (pair for pair in mate_ports(env.model) if not env.undrawn.intersection(pair))
    mates = tuple((pin_ref(env, a), pin_ref(env, b)) for a, b in pairs)
    sets, skipped = keep_whole(env)
    found = trees(env, syms)
    facts = Facts(sets, units_of(env), mates, series=series_of(found))
    return facts, (*skipped, *bridges_of(env, found))
