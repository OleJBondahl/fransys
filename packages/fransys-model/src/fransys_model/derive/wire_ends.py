"""The fixed order of a wire's two ends (V8): one home for the wire label and the wire row."""

from typing import TYPE_CHECKING

from fransys_model.derive.designation import bom_sort_key
from fransys_model.derive.lookups import item_of_port
from fransys_model.derive.port_marking import port_marking

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port


def _end_key(model: Model, port: Id[Port]) -> tuple[tuple[int, str, str, int], str, Id[Port]]:
    return (bom_sort_key(model, item_of_port(model, port)), port_marking(model, port), port)


def ordered_wire_ends(model: Model, a: Id[Port], b: Id[Port]) -> tuple[Id[Port], Id[Port]]:
    """The two ends in one fixed order, never the authored one: `bom_sort_key`, then marking."""
    return (a, b) if _end_key(model, a) <= _end_key(model, b) else (b, a)
