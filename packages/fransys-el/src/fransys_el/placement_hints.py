"""`Hints` (C2, C3): authored layout hints resolved to group labels and symbol ids."""

from typing import TYPE_CHECKING

from fransys_layout.core import Hints, natural_key
from fransys_model.layout import (
    BreakBefore,
    Chain,
    GroupHint,
    KeepTogether,
    OrderHint,
    layout_of,
)

from .placement_chains import chain_of
from .placement_groups import label_of
from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from fransys_layout.core import Sym
    from fransys_model.kernel import Id
    from fransys_model.vocab import AspectNode

    from .placement_env import Env

__all__ = ["hints_of"]


def _group(env: Env, known: Collection[str], node: Id[AspectNode]) -> str:
    """The label of `node`; `ProblemError` when no symbol is drawn in that group."""
    label = label_of(env.model, node)
    if label not in known:
        refuse(f"hint names group {label!r}", "draw a symbol in that group or drop the hint")
    return label


def hints_of(env: Env, syms: Sequence[Sym]) -> Hints:
    """The `Hints`: `SideHint` and `Chain.beside` stay unread (el-0002)."""
    model = env.model
    known = {s.group for s in syms if s.group}
    group = lambda n: _group(env, known, n)  # noqa: E731 - one-line closure over env and known
    return Hints(
        group_order=tuple(sorted(known, key=natural_key)),
        break_before=frozenset(group(b.group) for b in layout_of(model, BreakBefore).values()),
        keep_together=tuple(
            sorted(
                {frozenset(map(group, k.groups)) for k in layout_of(model, KeepTogether).values()},
                key=lambda s: sorted(natural_key(g) for g in s),
            )
        ),
        order_pairs=tuple(
            sorted(
                {(group(o.before), group(o.after)) for o in layout_of(model, OrderHint).values()}
            )
        ),
        chains=tuple(
            chain_of(env, c) for c in sorted(layout_of(model, Chain).values(), key=lambda c: c.id)
        ),
        draw_in=tuple(
            sorted(
                (env.owner[h.function], group(h.group))
                for h in layout_of(model, GroupHint).values()
                if h.function in env.owner
            )
        ),
    )
