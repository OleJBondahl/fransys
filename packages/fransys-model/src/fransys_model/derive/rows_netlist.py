"""Row shapes of `derive.netlist_pins`: a board's pins as a netlist writes and checks them."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Item, Port

__all__ = ["BoardPins", "NetlistPin", "PinNet"]


@value
class NetlistPin:
    """One pin: its port and item by id, the component reference and the pad name."""

    port: Id[Port]
    item: Id[Item]
    ref: str
    pad: str


@value
class PinNet:
    """One net of a board, by the resolved pins it joins."""

    name: str
    pins: tuple[NetlistPin, ...]


@value
class BoardPins:
    """A board's nets with every pin resolved, every pin of its parts, and those in no net."""

    nets: tuple[PinNet, ...]
    unconnected: tuple[NetlistPin, ...]
    part_pins: tuple[NetlistPin, ...]
