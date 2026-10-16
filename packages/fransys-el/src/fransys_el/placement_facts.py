"""`Facts` (facts 6, 11, 12, 13): keep-whole sets, units with their boundary, mates, row tags."""

from typing import TYPE_CHECKING

from fransys_layout.core import Facts, Size, Unit, natural_key
from fransys_model.derive import (
    item_functions,
    item_tag_text,
    keep_whole_sets,
    mate_ports,
    unit_boundary_pins,
    unit_chain,
    unit_ids,
)
from fransys_model.derive.text_width import text_width
from fransys_model.kernel import render_id

from .placement_env import pin_ref
from .placement_skips import FUNCTION_WITHOUT_SYMBOL, Skipped, in_order

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


def _owners(env: Env, drawn: Iterable[Id[Function]]) -> frozenset[str]:
    """The symbols that draw `drawn`; a function with no symbol is left out."""
    return frozenset(env.owner[f] for f in drawn if f in env.owner)


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
    lost = {
        Skipped("function", render_id(f), FUNCTION_WITHOUT_SYMBOL)
        for s in sets
        for f in s
        if f not in env.owner
    }
    return _sorted_sets([_owners(env, s) for s in sets]), in_order(lost)


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
            tuple(pin_ref(env, p) for p in unit_boundary_pins(env.model, u)),
        )
        for u in unit_ids(env.model)
    ]
    return tuple(sorted(found, key=lambda u: natural_key(u.id)))


def row_tags(env: Env, syms: Sequence[Sym]) -> tuple[tuple[str, Size], ...]:
    """Fact 13: each strip's id with the size of its tag text."""
    height = env.conventions.text_height
    strips = {s.row_group for s in syms if s.row_group}
    by_value = {i.value: i for i in env.parents.values()}
    return tuple(
        (g, Size(text_width(item_tag_text(env.model, by_value[g]), height=height), height))
        for g in sorted(strips, key=natural_key)
    )


def facts_of(env: Env, syms: Sequence[Sym]) -> tuple[Facts, tuple[Skipped, ...]]:
    """The `Facts`, and the functions the keep-whole sets lost for want of a symbol."""
    mates = tuple((pin_ref(env, a), pin_ref(env, b)) for a, b in mate_ports(env.model))
    sets, skipped = keep_whole(env)
    return Facts(sets, units_of(env), mates, row_tags(env, syms)), skipped
