"""The `layout.link_marker` of a core layout's lone marker, a stub or a copy (CORE-TEXTS C).

A lone marker has no partner on another page. It is an off stub: its own partner, its `far` and
`carrier` from `derive.stub_far`, its text the off-stub text of `derive.marker_text`.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import stub_far
from fransys_model.kernel import ModelError

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from fransys_layout.core import PinRef
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Port

__all__ = ["drawn_ports", "far_port"]

type PortPairs = Collection[tuple[Id[Port], Id[Port]]]


def drawn_ports(pins: Mapping[PinRef, Sequence[Id[Port]]], drawn: Collection[tuple[PinRef, PinRef]]) -> frozenset[tuple[Id[Port], Id[Port]]]:
    """The `(port, far port)` pairs the layout's drawn `(pin, far pin)` pairs stand for (R777)."""
    return frozenset((a, b) for p, q in drawn for a in pins.get(p, ()) for b in pins.get(q, ()))


def far_port(model: Model, ports: Sequence[Id[Port]]) -> tuple[Id[Port], Id[Port], Id[Item] | None]:
    """`(near, far, carrier)` of the stub the `ports` one pin draws (`stub_far`).

    `ModelError` when no undrawn conductor leaves the pin or its function (R1539).
    """
    found = stub_far(model, ports)
    if not found:
        msg = f"stub at ports {list(ports)}: no conductor leaves its pin, or its function that is not drawn, so its far end is unknown"
        raise ModelError(msg)
    return found[0]
