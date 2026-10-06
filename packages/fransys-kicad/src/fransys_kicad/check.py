"""KiCad-side ERC, reported as findings (spec section 8)."""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from fransys_model.derive import board_netlist, build_indexes, item_label, item_of_port
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import items, ports

from ._pins import pin_of

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.derive import BoardNetlist
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Port

PART_WITHOUT_FOOTPRINT: Final[str] = "PART_WITHOUT_FOOTPRINT"
NET_SINGLE_PIN: Final[str] = "NET_SINGLE_PIN"
NODE_WITHOUT_COMPONENT: Final[str] = "NODE_WITHOUT_COMPONENT"
REFERENCE_DUPLICATE: Final[str] = "REFERENCE_DUPLICATE"
NET_NAME_DUPLICATE: Final[str] = "NET_NAME_DUPLICATE"
PAD_ON_MULTIPLE_NETS: Final[str] = "PAD_ON_MULTIPLE_NETS"
UNCONNECTED_PIN: Final[str] = "UNCONNECTED_PIN"


@dataclass(frozen=True, slots=True)
class _Pin:
    """One net pin as the netlist writes it."""

    port: Id[Port]
    item: Id[Item]
    ref: str
    pad: str

    @property
    def label(self) -> str:
        return f"{self.ref}:{self.pad}"


@dataclass(frozen=True, slots=True)
class _Net:
    name: str
    pins: tuple[_Pin, ...]


def _finding(code: str, severity: Severity, subjects: Iterable[Id[Any]], message: str) -> Finding:
    return Finding(code=code, severity=severity, subjects=tuple(subjects), message=message)


def _single_pin(nets: tuple[_Net, ...]) -> list[Finding]:
    return [
        _finding(
            NET_SINGLE_PIN,
            Severity.WARNING,
            (net.pins[0].port,),
            f"net {net.name} has one pin, {net.pins[0].label}",
        )
        for net in nets
        if len(net.pins) == 1
    ]


def _without_footprint(model: Model, rows: BoardNetlist) -> list[Finding]:
    all_items = items(model)
    found = []
    for item_id in rows.without_footprint:
        item = all_items[item_id]
        message = f"part {item_label(model, item)} has no footprint, so the netlist omits it"
        found.append(_finding(PART_WITHOUT_FOOTPRINT, Severity.WARNING, (item_id,), message))
    return found


def _without_component(rows: BoardNetlist, nets: tuple[_Net, ...]) -> list[Finding]:
    comps = {part.item for part in rows.parts}
    lonely = {pin.port: pin for net in nets for pin in net.pins if pin.item not in comps}
    found = []
    for pin in lonely.values():
        if pin.item == rows.board:
            message = (
                f"pin {pin.label} is a pin of the board itself, which is not a KiCad footprint, "
                "so KiCad drops it on import; a board connector that needs a pad in KiCad is "
                "modelled as a child item with a part that has a footprint, not as a function "
                "of the bare board"
            )
        else:
            message = (
                f"pin {pin.label} belongs to an item with no footprint, so it has no component "
                "in the netlist and KiCad drops it on import"
            )
        found.append(_finding(NODE_WITHOUT_COMPONENT, Severity.WARNING, (pin.port,), message))
    return found


def _reference_duplicate(rows: BoardNetlist) -> list[Finding]:
    by_reference: defaultdict[str, list[Id[Item]]] = defaultdict(list)
    for part in rows.parts:
        by_reference[part.designation].append(part.item)
    return [
        _finding(
            REFERENCE_DUPLICATE,
            Severity.ERROR,
            parts,
            f"{len(parts)} parts share the reference {reference}",
        )
        for reference, parts in by_reference.items()
        if len(parts) > 1
    ]


def _net_name_duplicate(nets: tuple[_Net, ...]) -> list[Finding]:
    by_name: defaultdict[str, list[_Net]] = defaultdict(list)
    for net in nets:
        by_name[net.name].append(net)
    return [
        _finding(
            NET_NAME_DUPLICATE,
            Severity.ERROR,
            (pin.port for net in same for pin in net.pins),
            f"{len(same)} nets are named {name}, and KiCad merges nets that share a name",
        )
        for name, same in by_name.items()
        if len(same) > 1
    ]


def _pad_on_multiple_nets(nets: tuple[_Net, ...]) -> list[Finding]:
    uses: defaultdict[tuple[str, str], list[tuple[int, Id[Port]]]] = defaultdict(list)
    for index, net in enumerate(nets):
        for pin in net.pins:
            uses[pin.ref, pin.pad].append((index, pin.port))
    return [
        _finding(
            PAD_ON_MULTIPLE_NETS,
            Severity.ERROR,
            (port for _, port in pad_uses),
            f"pad {ref}:{pad} is in {len({index for index, _ in pad_uses})} nets, "
            "and KiCad puts a pad in one",
        )
        for (ref, pad), pad_uses in uses.items()
        if len({index for index, _ in pad_uses}) > 1
    ]


def _unconnected_pin(model: Model, rows: BoardNetlist, nets: tuple[_Net, ...]) -> list[Finding]:
    connected = {(pin.ref, pin.pad) for net in nets for pin in net.pins}
    idx = build_indexes(model)
    all_ports = ports(model)
    return [
        _finding(
            UNCONNECTED_PIN,
            Severity.INFO,
            (port,),
            f"pin {part.designation}:{all_ports[port].name} is in no net",
        )
        for part in rows.parts
        for function in idx.functions_by_item.get(part.item, ())
        for port in idx.ports_by_function.get(function, ())
        if (part.designation, all_ports[port].name) not in connected
    ]


def _net(
    model: Model,
    designations: dict[Id[Item], str],
    name: str,
    pins: Iterable[Id[Port]],
    board: Id[Item],
) -> _Net:
    return _Net(
        name=name,
        pins=tuple(
            _Pin(port, item_of_port(model, port), *pin_of(model, designations, port, board))
            for port in pins
        ),
    )


def check(model: Model, board: Id[Item]) -> tuple[Finding, ...]:
    """Run KiCad's import-time rule checks on one board; findings sorted by code, subjects, text.

    The rules read what `netlist` writes and repeat nothing the model's validators report. The
    seven codes and what is not checked are in the package README.

    Args:
        model: A frozen, numbered model.
        board: The board item; its part carries a ``pcb`` facet.

    Returns:
        One `Finding` per rule violation, sorted by `(code, subjects, message)`.

    Raises:
        SchemaError: as `board_netlist` (`board` unknown, or an item has no designation).
    """
    rows = board_netlist(model, board)
    designations = {part.item: part.designation for part in rows.parts}
    nets = tuple(_net(model, designations, net.name, net.pins, board) for net in rows.nets)
    found = [
        *_without_footprint(model, rows),
        *_single_pin(nets),
        *_without_component(rows, nets),
        *_reference_duplicate(rows),
        *_net_name_duplicate(nets),
        *_pad_on_multiple_nets(nets),
        *_unconnected_pin(model, rows, nets),
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
