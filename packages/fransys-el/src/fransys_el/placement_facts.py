"""`Facts` (facts 6, 11, 12, 13): keep-whole sets, units with their boundary, mates, far ends."""

from typing import TYPE_CHECKING

from fransys_layout.core import Facts, Unit, natural_key
from fransys_model.derive import (
    drawn_groups,
    far_pins,
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
from .placement_chains import anchored
from .placement_env import drawn_pins, pin_ref
from .placement_series import bridges_of, series_of, trees
from .placement_skips import FUNCTION_WITHOUT_SYMBOL, Skipped, in_order, unwired_reason
from .symbol_kit import drawn_functions

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_layout.core import PinRef, Sym
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function

    from .placement_env import Env

_WHOLE_SET = 2  # one symbol is nothing to keep whole

__all__ = ["facts_of"]


def _sorted_sets(found: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    """The sets with two symbols or more, once each, in natural order."""
    kept = {s for s in found if len(s) >= _WHOLE_SET}
    return tuple(sorted(kept, key=lambda s: sorted(natural_key(i) for i in s)))


def _drawn_by(env: Env) -> dict[Id[Function], set[str]]:
    """Each drawn function with its symbols: a connector's are its pins' (el-0014, el-0053)."""
    found: dict[Id[Function], set[str]] = {}
    for key, symbol in env.owner.items():
        found.setdefault(function_of(env.model, key), set()).add(symbol)
    return found


def _why(env: Env, function: Id[Function]) -> str:
    """Unwired when no pin of the function is drawn (R364), a spare when declared `unused=` (R1528), else it has no symbol (el-0053)."""
    own = function_ports(env.model, function)
    if not (own and set(own) <= env.undrawn):
        return FUNCTION_WITHOUT_SYMBOL
    return unwired_reason(env.model, function, kept_sibling=False)


def _function_sets(env: Env) -> list[frozenset[Id[Function]]]:
    """Each `keep_whole_sets` set as functions: item sets expanded to the items' functions."""
    sets = keep_whole_sets(env.model)
    of_item = item_functions(env.model)
    expanded = [frozenset(f for i in s for f in of_item.get(i, ())) for s in (*sets.item_boxes, *sets.line_units)]
    return [*expanded, *(frozenset(s) for s in sets.pole_groups)]


def keep_whole(env: Env) -> tuple[tuple[frozenset[str], ...], tuple[Skipped, ...]]:
    """Fact 11: each set as symbol ids (under two symbols is dropped), and the functions lost."""
    sets = _function_sets(env)
    drawn_by = _drawn_by(env)
    attempted = set(drawn_functions(env.model))  # inside a black-box board nothing is attempted
    lost = {Skipped("function", render_id(f), _why(env, f)) for s in sets for f in s if f in attempted and f not in drawn_by and f not in env.spare}
    return _sorted_sets([frozenset(s for f in one for s in drawn_by.get(f, ())) for one in sets]), in_order(lost)


def units_of(env: Env) -> tuple[Unit, ...]:
    """Fact 12: each unit with its parent and its boundary pins, in natural order of id."""
    return tuple(
        Unit(
            u.value,
            next((p.value for p in unit_chain(env.model, u)[1:2]), None),  # the parent id text, `None` at the top
            drawn_pins(env, unit_boundary_pins(env.model, u)),
        )
        for u in unit_ids(env.model)
    )


def far_ends_of(env: Env, syms: Sequence[Sym]) -> tuple[tuple[PinRef, PinRef], ...]:
    """Fact 13: each drawn pin with the drawn pin the far end of its conductor lands on.

    Page-free: `derive.far_pins` gives the ports, once for each pair; a port with no pick, an
    undrawn connector pin, or a pin whose symbol is not placed (`syms`) is left out (R1544).
    """
    pairs = far_pins(env.model, env.pins)
    placed = {s.id for s in syms}
    drawn = ((a, b) for a, b in pairs if a in env.pins and b in env.pins)
    kept = ((env.pins[a], env.pins[b]) for a, b in drawn if not env.undrawn.intersection((a, b)))
    return tuple(dict.fromkeys((a, b) for a, b in kept if a.sym in placed and b.sym in placed))


def groups_of(env: Env) -> tuple[tuple[PinRef, ...], ...]:
    """Fact 14: each group the model joins (`derive.drawn_groups`) as its drawn pins, two or more, once each."""
    found = (tuple(dict.fromkeys(env.pins[p] for p in group if p in env.pins and p not in env.undrawn)) for group in drawn_groups(env.model))
    return tuple(dict.fromkeys(g for g in found if len(g) >= _WHOLE_SET))


def facts_of(env: Env, syms: Sequence[Sym]) -> tuple[Facts, tuple[Skipped, ...]]:
    """The `Facts`, and the functions the keep-whole sets lost for want of a symbol."""
    mates = tuple((pin_ref(env, a), pin_ref(env, b)) for a, b in mate_ports(env.model) if not env.undrawn.intersection((a, b)))
    sets, skipped = keep_whole(env)
    found = trees(env, syms)
    far_ends = far_ends_of(env, syms)
    series = (*series_of(found), *anchored(env, syms, far_ends))
    facts = Facts(sets, units_of(env), mates, series=series, far_ends=far_ends, groups=groups_of(env))
    return facts, (*skipped, *bridges_of(env, found))
