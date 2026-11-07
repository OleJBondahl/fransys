"""The ERRORs for authored order hints that contradict each other (R468, FLIP-NOW F2) or name a group that draws nothing (R1841)."""

from graphlib import CycleError, TopologicalSorter

from fransys_model.derive.drawn_groups import group_draws, group_members_drawn_in
from fransys_model.derive.order import order_hint_key
from fransys_model.derive.placement_reads import node_label
from fransys_model.layout import OrderHint, layout_of
from fransys_model.vocab.codes import ORDER_GROUP_DRAWS_NOTHING, ORDER_HINT_CYCLE, finding
lazy from fransys_model.kernel import Finding, Id, Model
lazy from fransys_model.vocab import AspectNode

__all__ = ["check_order_hint_cycle", "check_order_hint_draws_nothing"]


def check_order_hint_cycle(model: Model) -> tuple[Finding, ...]:
    """One ERROR naming the Origin of each hint in a cycle of `d.layout.order` hints, else none."""
    hints = tuple(layout_of(model, OrderHint).values())
    graph: dict[object, set[object]] = {}
    for hint in hints:
        graph.setdefault(hint.after, set()).add(hint.before)
    try:
        TopologicalSorter(graph).prepare()
    except CycleError as error:
        loop = set(error.args[1])
    else:
        return ()
    ring = sorted((h for h in hints if h.before in loop and h.after in loop), key=order_hint_key)
    places = ", ".join(f"{model.origins[h.id].file}:{model.origins[h.id].line}" for h in ring)
    return (
        finding(
            ORDER_HINT_CYCLE,
            tuple(h.id for h in ring),
            f"order hints contradict each other in a cycle ({places})",
        ),
    )


def _draws_nothing_text(model: Model, group: Id[AspectNode]) -> str:
    """The message for a hint end `group` that draws no function: where its members are drawn, and the fix."""
    name = f"={node_label(model, group)}"
    elsewhere = ", ".join(f"={node_label(model, g)}" for g in group_members_drawn_in(model, group))
    where = f"its members are drawn in {elsewhere}" if elsewhere else "it has no member to draw"
    return f"order hint names group {name}, which draws nothing ({where}); order the group they are drawn in, or drop the hint"


def check_order_hint_draws_nothing(model: Model) -> tuple[Finding, ...]:
    """One ERROR per end of an `OrderHint` naming a group in which no function is drawn, in any set."""
    hints = sorted(layout_of(model, OrderHint).values(), key=order_hint_key)
    return tuple(
        finding(ORDER_GROUP_DRAWS_NOTHING, (hint.id,), _draws_nothing_text(model, end))
        for hint in hints
        for end in (hint.before, hint.after)
        if not group_draws(model, end)
    )
