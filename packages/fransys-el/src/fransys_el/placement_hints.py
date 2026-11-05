"""`Hints` (C2, C3): authored layout hints resolved to group labels and symbol ids."""

from functools import partial
from typing import TYPE_CHECKING

from fransys_layout.core import Hints
from fransys_model.derive import function_groups_in_order
from fransys_model.layout import (
    GroupHint,
    OrderHint,
    layout_of,
)

from .placement_groups import group_nodes, label_of
from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from fransys_layout.core import Sym
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode

    from .placement_env import Env

__all__ = ["hints_of"]


def _group(env: Env, known: Collection[str], node: Id[AspectNode]) -> str:
    """The label of `node`; `ProblemError` when no symbol is drawn in that group."""
    label = label_of(env.model, node)
    if label not in known:
        refuse(f"hint names group {label!r}", "draw a symbol in that group or drop the hint")
    return label


def _authored_order(model: Model, known: Collection[str]) -> tuple[str, ...]:
    """The drawn group labels in `function_groups_in_order`, the one home of the group order (R1361)."""
    node_of = {label_of(model, n): n for n in group_nodes(model)}
    return tuple(label_of(model, n) for n in function_groups_in_order(model, {node_of[g] for g in known}))


def hints_of(env: Env, syms: Sequence[Sym]) -> Hints:
    """The `Hints` the core reads: the order and group hints."""
    model = env.model
    known = {s.group for s in syms if s.group}
    group = partial(_group, env, known)
    return Hints(
        group_order=_authored_order(model, known),
        order_pairs=tuple(sorted({(group(o.before), group(o.after)) for o in layout_of(model, OrderHint).values()})),
        draw_in=tuple(sorted((env.owner[h.function], group(h.group)) for h in layout_of(model, GroupHint).values() if h.function in env.owner)),
    )
