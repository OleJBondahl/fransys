"""A board's pins resolved once: reference, pad and the spelling `ref:pad` (decision model-0275)."""

from fransys_model.kernel import Id, Model  # noqa: TC001 -- signature tests resolve hints at runtime
from fransys_model.vocab import ports
from fransys_model.vocab.core import Item, Port  # noqa: TC001 -- signature tests resolve hints at runtime

from .designation import item_designation
from .indexes import build_indexes
from .lookups import item_of_port
from .rows_netlist import BoardPins, NetlistPin, PinNet
from .structure import board_netlist

__all__ = ["board_pins", "pin_text"]


def pin_text(pin: NetlistPin) -> str:
    """The one spelling of a pin for a netlist output: `ref:pad`.

    Args:
        pin: A resolved pin.

    Returns:
        The component reference, a colon and the pad name.
    """
    return f"{pin.ref}:{pin.pad}"


def _pin(
    model: Model,
    designations: dict[Id[Item], str],
    port: Id[Port],
    board: Id[Item],
) -> NetlistPin:
    """`port`'s item, reference and pad by ids; no part row: board-relative (model-0040)."""
    item = item_of_port(model, port)
    ref = (
        designations[item]
        if item in designations
        else item_designation(model, item, relative_to=board)
    )
    return NetlistPin(port=port, item=item, ref=ref, pad=ports(model)[port].name)


def board_pins(model: Model, board: Id[Item]) -> BoardPins:
    """`board_netlist`'s nets with each pin resolved once, and the open pins of its parts.

    A pin of an item with no part row takes its board-relative designation. `unconnected` lists,
    per part in `board_netlist` order, every port of its functions whose `ref:pad` is in no net.

    Args:
        model: The model to read.
        board: The item whose netlist is built.

    Returns:
        A `BoardPins` (defined in `derive.rows_netlist`).

    Raises:
        SchemaError: as `board_netlist`.
    """
    rows = board_netlist(model, board)
    designations = {part.item: part.designation for part in rows.parts}
    nets = tuple(
        PinNet(
            name=net.name,
            pins=tuple(_pin(model, designations, port, board) for port in net.pins),
        )
        for net in rows.nets
    )
    connected = {(pin.ref, pin.pad) for net in nets for pin in net.pins}
    idx = build_indexes(model)
    all_ports = ports(model)
    open_pins = tuple(
        NetlistPin(port=port, item=part.item, ref=part.designation, pad=all_ports[port].name)
        for part in rows.parts
        for function in idx.functions_by_item.get(part.item, ())
        for port in idx.ports_by_function.get(function, ())
        if (part.designation, all_ports[port].name) not in connected
    )
    return BoardPins(nets=nets, unconnected=open_pins)
