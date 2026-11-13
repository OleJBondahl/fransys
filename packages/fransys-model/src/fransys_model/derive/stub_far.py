"""The far end a lone reference marker (a stub or a copy) names (CORE-TEXTS FIX3, model-0340).

One fact for every writer of a stub: the conductor at the pin, else at its function (a pin only a bridge reaches names none, R885), and the
cable that carries it, as the layout engine prints a stub's `-W3`.
"""

lazy from collections.abc import Collection, Sequence

from fransys_model.derive.facts.conductor_facts import is_bridge
from fransys_model.derive.facts.units import item_root
from fransys_model.derive.far_pins import reach
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.rows_drawn import MateEnd
from fransys_model.vocab.tables import conductors, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item, Port

__all__ = ["stub_far"]


def _function_ports(model: Model, near: Sequence[Id[Port]]) -> list[Id[Port]]:
    """Every port of the functions the `near` ports belong to, `near` included."""
    by_function = build_indexes(model).ports_by_function
    functions = {ports(model)[port].function for port in near}
    return [port for function in functions for port in by_function[function]]


def stub_far(
    model: Model,
    near: Sequence[Id[Port]],
    far: Collection[Id[Port]] = (),
) -> tuple[tuple[Id[Port], Id[Port], Id[Item] | None], ...]:
    """`(near, far, carrier)` of each conductor a stub names, empty when no conductor leaves the pin.

    `near` are the ports the pin draws. A wired pin names the far end (`conductor_ends`) of its conductor. A pin none wires
    (a terminal's unwired side) takes a port of its own function, the through path. `far`, the ports of the far end the stub names,
    picks every reach ending there; with none, every reach, by `order.stub_far_order`.
    `carrier` is the outermost item above the conductor's own cable, `None` for a wire or a mate: the `-W3` a stub prints.
    """
    by_port = build_indexes(model).conductors_by_port
    bridged = any(is_bridge(model, c) for port in near for c in by_port.get(port, ()))
    picks = reach(model, near) or ([] if bridged else reach(model, _function_ports(model, near)))
    return tuple((p.port, p.far, None if isinstance(p, MateEnd) else _carrier(model, p.conductor)) for p in picks if not far or p.far in far)


def _carrier(model: Model, conductor: Id[Conductor]) -> Id[Item] | None:
    """The outermost item above the conductor's own cable, `None` for a wire."""
    cable = conductors(model)[conductor].carrier
    return None if cable is None else item_root(model, cable)
