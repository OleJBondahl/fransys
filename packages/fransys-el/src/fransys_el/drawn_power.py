"""The printed power join and R4 over the drawn netlist (READ-RAILS, READ-POWER-INK).

Two power symbols are one piece when they print the same potential, with the same symbol, in one cabinet.
A power symbol is joined to its pin by ink; the model's hidden net no longer carries a rail across pages.
"""

from typing import TYPE_CHECKING

from electrical_symbols import power_symbol_key
from fransys_model.derive import (
    PowerKind,
    is_rail_terminal,
    item_of_port,
    item_unit,
    net_of,
    port_power_kind,
    port_power_text,
    port_rails,
    rail_scope,
    rail_source_unit,
)

from .drawn_finding import drawn_finding
from .placement_ids import net_key

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Port, Unit

    from .drawn_netlist import Netlist, PagePart

__all__ = ["PE_KEY", "POWER_KEYS", "inked_power", "join_power", "port_nets", "power_findings", "rail_flagged", "symbol_classes"]

POWER_KEYS = frozenset(power_symbol_key(kind) for kind in ("supply", "ground", "pe"))
_SUPPLY = power_symbol_key("supply")
PE_KEY = power_symbol_key("pe")
Identity = str | tuple[frozenset[str], "Id[Unit] | None"] | None
RailClass = tuple["Id[Unit]", str, Identity]


def _scope(model: Model, port: Id[Port]) -> Id[Unit] | None:
    """The cabinet of `port` (the unit of its item); `None` for a unit-less field device, which stands in no rail scope."""
    return item_unit(model, item_of_port(model, port))


def _identity(model: Model, port: Id[Port], key: str, text: str | None) -> Identity:
    """What one symbol key prints as one potential: the text for supply, the rails and source unit for ground, `PE` for every PE symbol."""
    if key == _SUPPLY:
        return text
    return PowerKind.PE.name if key == PE_KEY else (port_rails(model, port), rail_source_unit(model, port))


def _pe_classes(model: Model, keys: dict[str, str], ids: Mapping[str, Id[Port]]) -> dict[str, str]:
    """The class of each earth-declared PE net: one per cabinet, bonded through its DIN rail (owner 10-29, R1962)."""
    return {keys[p]: f"PE:{_scope(model, one)}" for p, one in ids.items() if port_power_kind(model, one) is PowerKind.PE}


def port_nets(model: Model, ids: Mapping[str, Id[Port]]) -> dict[str, str]:
    """The physical net of each port, spelled as `Net.id` is (`net_key`), built once; the PE nets of a bonded cabinet are one (R1937)."""
    found = {port: net_of(model, one) for port, one in ids.items()}
    nets = {net.ports[0]: net for net in found.values() if net}  # a net by its first port: one spelling per net
    spelled = {first: net_key(model, net.ports) for first, net in nets.items()}
    keys = {port: spelled[net.ports[0]] if net else port for port, net in found.items()}
    held = _pe_classes(model, keys, ids)
    return {port: held.get(key, key) for port, key in keys.items()}


def _symbols(net: Netlist, model: Model) -> Iterator[tuple[Id[Page], PagePart, str, str, str | None]]:
    """Each port drawn as a power symbol that names its potential (R1631): (page, part, port, symbol key, printed text).

    A ground or PE symbol names it by its kind; a supply symbol only with a printed text.
    """
    for page, part in net.pages.items():
        for symbol in part.drawing.symbols:
            for port in symbol.ports if symbol.key in POWER_KEYS else ():
                text = port_power_text(model, net.ids[port])
                if symbol.key != _SUPPLY or text is not None:
                    yield page, part, port, symbol.key, text


def _inked(part: PagePart, port: str) -> bool:
    """True when the symbol of `port` is joined to its pin by ink: the pin stands on a node, or the lead is zero-length (R4)."""
    pin = part.ports.get(port)
    return pin is not None and (pin in part.nodes or part.powers.get(port) == pin)


def inked_power(net: Netlist, model: Model) -> set[str]:
    """The ports drawn as a power symbol that names its potential and is joined to its pin by ink: R4 replaces the model-net read."""
    return {port for _, part, port, _, _ in _symbols(net, model) if _inked(part, port)}


def _class(model: Model, port: Id[Port], key: str, text: str | None) -> RailClass | None:
    """The (cabinet, symbol key, printed identity) a power symbol joins by; `None` for a symbol in no cabinet."""
    scope = _scope(model, port)
    return None if scope is None else (scope, key, _identity(model, port, key, text))


def symbol_classes(net: Netlist, model: Model) -> Iterator[tuple[str, RailClass, bool]]:
    """Each power symbol that names its potential and stands in a cabinet: (port, join class, inked)."""
    for _, part, port, key, text in _symbols(net, model):
        if (joined := _class(model, net.ids[port], key, text)) is not None:
            yield port, joined, _inked(part, port)


def rail_flagged(model: Model, joined: RailClass) -> bool:
    """True when the class joins by its key: a printed supply, or a ground or PE symbol whose cabinet flags a rail of its potential (R1936)."""
    scope, key, identity = joined
    potentials = {identity} if isinstance(identity, str) else identity[0] if identity else ()
    return key == _SUPPLY or any((scope, potential) in rail_scope(model) for potential in potentials)


def _strip_classes(net: Netlist, model: Model) -> set[RailClass]:
    """The classes of the power symbols standing at a flagged rail terminal: the flagged strip's own sources (R2590)."""
    held = ((port, key, text) for _, _, port, key, text in _symbols(net, model) if is_rail_terminal(model, item_of_port(model, net.ids[port])))
    return {joined for port, key, text in held if (joined := _class(model, net.ids[port], key, text)) is not None}


def _joins(model: Model, joined: RailClass, strip: set[RailClass]) -> bool:
    """Whether the class joins by its key: flagged, and when it carries a source unit, only the class the flagged strip stands in."""
    sourced = isinstance(joined[2], tuple) and joined[2][1] is not None
    return rail_flagged(model, joined) and (joined in strip or not sourced)


def join_power(net: Netlist, model: Model) -> None:
    """Join inked power symbols of one identity in one cabinet (a textless one only where its rail is flagged): ink only (CP-S2c-1).

    A ground class that carries a source unit joins only when the flagged strip stands in it; the others stay separate (R2590).
    """
    first: dict[RailClass, tuple[Id[Page], tuple[int, int]]] = {}
    strip = _strip_classes(net, model)
    for page, part, port, key, text in _symbols(net, model):
        if _inked(part, port):
            at = (page, part.ports[port])
            if (joined := _class(model, net.ids[port], key, text)) is not None and _joins(model, joined, strip):
                net.union.join(first.setdefault(joined, at), at)


def power_findings(net: Netlist, model: Model) -> tuple[Finding, ...]:
    """POWER_SYMBOL_NOT_JOINED per power symbol that names its potential and has no ink to its pin (R4)."""
    return tuple(
        drawn_finding(
            "POWER_SYMBOL_NOT_JOINED", (net.ids[port],), "a power symbol has no wire to its pin: report it as a Fransys defect with the model"
        )
        for _, part, port, _, _ in _symbols(net, model)
        if not _inked(part, port)
    )
