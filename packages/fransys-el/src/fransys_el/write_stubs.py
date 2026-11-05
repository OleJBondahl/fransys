"""The `layout.link_marker` of a core layout's lone marker, a stub or a copy (CORE-TEXTS C).

A lone marker has no partner on another page. It is an off stub: its own partner, its `far` and
`carrier` from `derive.stub_far`, its text the off-stub text of `derive.marker_text`.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import mate_ports, stub_far
from fransys_model.kernel import ModelError

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from fransys_layout.core import PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Port

__all__ = ["drawn_ports", "far_port", "stub_ends"]

type PortPairs = Collection[tuple[Id[Port], Id[Port]]]


def drawn_ports(pins: Mapping[PinRef, Sequence[Id[Port]]], drawn: Collection[tuple[PinRef, PinRef]]) -> frozenset[tuple[Id[Port], Id[Port]]]:
    """The `(port, far port)` pairs the layout's drawn `(pin, far pin)` pairs stand for (R777)."""
    return frozenset((a, b) for p, q in drawn for a in pins.get(p, ()) for b in pins.get(q, ()))


def stub_ends(model: Model, ports: Sequence[Id[Port]], far: Collection[Id[Port]] = ()) -> tuple[tuple[Id[Port], Id[Port], Id[Item] | None], ...]:
    """`derive.stub_far` of the pin, else of the pin its mate joins: the line through the mate.

    A mated half no conductor leaves names its partner's far end, or that end's mate (R467 Q02).
    """
    found = stub_far(model, ports, far)
    if found:
        return found
    pairs = mate_ports(model)
    for here, there in (*pairs, *((b, a) for a, b in pairs)):
        via = stub_far(model, [there], far) if here in ports else ()
        if via:
            beyond = next((b for a, b in pairs if a == via[0][1]), None)
            beyond = beyond or next((a for a, b in pairs if b == via[0][1]), via[0][1])
            return ((here, beyond, via[0][2]),)
    return ()


def far_port(model: Model, ports: Sequence[Id[Port]]) -> tuple[Id[Port], Id[Port], Id[Item] | None]:
    """`(near, far, carrier)` of the stub the `ports` one pin draws (`stub_ends`).

    `ModelError` when no undrawn conductor leaves the pin, its function or its mate (R1539).
    """
    found = stub_ends(model, ports)
    if not found:
        msg = f"stub at ports {list(ports)}: no conductor leaves its pin, its function or its mate that is not drawn, so its far end is unknown"
        raise ModelError(msg)
    return found[0]
