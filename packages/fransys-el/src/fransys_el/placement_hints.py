"""`Hints` (C2, C3): authored layout hints resolved to group labels and symbol ids."""

from typing import TYPE_CHECKING

from fransys_layout.core import Hints
from fransys_model.derive import function_groups_in_order
from fransys_model.layout import (
    OrderHint,
    layout_of,
)

from .placement_groups import group_nodes, label_of

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from fransys_layout.core import Sym
    from fransys_model.kernel import Model

    from .placement_env import Env

__all__ = ["hints_of"]


def _authored_order(model: Model, known: Collection[str]) -> tuple[str, ...]:
    """The drawn group labels in `function_groups_in_order`, the one home of the group order (R1361)."""
    node_of = {label_of(model, n): n for n in group_nodes(model)}
    return tuple(label_of(model, n) for n in function_groups_in_order(model, {node_of[g] for g in known}))


def hints_of(env: Env, syms: Sequence[Sym]) -> Hints:
    """The `Hints` the core reads: the order hints."""
    model = env.model
    known = {s.group for s in syms if s.group}
    return Hints(
        group_order=_authored_order(model, known),
        order_pairs=tuple(sorted({(label_of(model, o.before), label_of(model, o.after)) for o in layout_of(model, OrderHint).values()})),
    )
