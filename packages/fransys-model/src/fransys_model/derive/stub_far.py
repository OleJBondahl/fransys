"""The far end a lone reference marker (a stub or a copy) names (CORE-TEXTS FIX3, model-0340).

One fact for every writer of a stub: the conductor at the pin, else at its function, and the
cable that carries it, as the layout engine prints a stub's `-W3`.
"""

lazy from collections.abc import Iterable, Sequence

from fransys_model.derive.facts.conductor_facts import conductor_ends
from fransys_model.derive.facts.units import item_chain
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.order import stub_far_key
from fransys_model.vocab.tables import conductors, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item, Port

__all__ = ["stub_far"]

type _Pick = tuple[Id[Port], Id[Port], Id[Conductor]]


def _reach(model: Model, near: Iterable[Id[Port]]) -> list[_Pick]:
    """Every `(near, far, conductor)` at any `near` port; the ends are `conductor_ends`."""
    by_port = build_indexes(model).conductors_by_port
    found: list[_Pick] = []
    for port in near:
        for conductor in by_port.get(port, ()):
            a, b = conductor_ends(model, conductor)
            found.append((port, b if a == port else a, conductor))
    return found


def _function_ports(model: Model, near: Sequence[Id[Port]]) -> list[Id[Port]]:
    """Every port of the functions the `near` ports belong to, `near` included."""
    by_function = build_indexes(model).ports_by_function
    functions = {ports(model)[port].function for port in near}
    return [port for function in functions for port in by_function[function]]


def stub_far(
    model: Model, near: Sequence[Id[Port]]
) -> tuple[Id[Port], Id[Port], Id[Item] | None] | None:
    """`(near, far, carrier)` of the stub a pin draws, or `None` when no conductor leaves it.

    `near` are the ports the pin draws. A wired pin names the far end (`conductor_ends`) of its
    conductor. A pin none
    wires (a terminal's unwired side) takes a port of its own function, the through path. Several
    reaches tie on `order.stub_far_key`, the lowest far port first. `carrier` is the outermost item
    above the conductor's own cable, `None` for a wire: the `-W3` a stub prints.
    """
    reach = _reach(model, near) or _reach(model, _function_ports(model, near))
    if not reach:
        return None
    port, far, conductor = min(reach, key=stub_far_key)
    cable = conductors(model)[conductor].carrier
    carrier = None if cable is None else list(item_chain(model, cable))[-1]
    return port, far, carrier
