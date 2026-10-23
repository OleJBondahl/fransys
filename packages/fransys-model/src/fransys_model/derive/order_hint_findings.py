"""The ERROR for authored order hints that contradict each other (R468, FLIP-NOW F2)."""

from graphlib import CycleError, TopologicalSorter

from fransys_model.derive.order import order_hint_key
from fransys_model.kernel import Finding, Model, Severity
from fransys_model.layout import OrderHint, layout_of
from fransys_model.vocab.codes import ORDER_HINT_CYCLE, fix_text

__all__ = ["check_order_hint_cycle"]


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
        Finding(
            code=ORDER_HINT_CYCLE,
            severity=Severity.ERROR,
            subjects=tuple(h.id for h in ring),
            message=f"order hints contradict each other in a cycle ({places})",
            fix=fix_text(ORDER_HINT_CYCLE),
        ),
    )
