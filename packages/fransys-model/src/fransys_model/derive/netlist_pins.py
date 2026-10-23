"""A board's pins resolved once: reference, pad and the spelling `ref:pad` (decision model-0275)."""

from fransys_model.kernel import Id, Model  # noqa: TC001 -- signature tests resolve hints at runtime
from fransys_model.vocab import ports
from fransys_model.vocab.core import Item, Port  # noqa: TC001 -- signature tests resolve hints at runtime
from fransys_model.vocab.tables import unused_boundaries

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

    An item with no part row takes its board-relative designation. `part_pins` is every port of
    each part's functions; `unconnected` those in no net, minus any of an `unused=` function.

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
    quiet = {unused.function for unused in unused_boundaries(model).values()}
    quiet_ports = {port for function in quiet for port in idx.ports_by_function.get(function, ())}
    part_pins = tuple(
        NetlistPin(port=port, item=part.item, ref=part.designation, pad=all_ports[port].name)
        for part in rows.parts
        for function in idx.functions_by_item.get(part.item, ())
        for port in idx.ports_by_function.get(function, ())
    )
    open_pins = tuple(
        pin
        for pin in part_pins
        if (pin.ref, pin.pad) not in connected and pin.port not in quiet_ports
    )
    return BoardPins(nets=nets, unconnected=open_pins, part_pins=part_pins)
