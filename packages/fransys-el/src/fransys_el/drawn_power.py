"""The printed power join and R4 over the drawn netlist (READ-RAILS, READ-POWER-INK).

Two power symbols are one piece when they print the same potential, with the same symbol, in one scope: the unit of the page's drawing set.
A power symbol is joined to its pin by ink; the model's hidden net no longer carries a rail across pages.
"""

from typing import TYPE_CHECKING

from electrical_symbols import marking_slot, power_symbol_key
from fransys_model.derive import (
    PowerKind,
    item_of_port,
    item_unit,
    net_of,
    port_power_kind,
    power_identity,
    set_unit,
)
from fransys_model.layout import DrawingSet, Page, layout_of

from .drawn_finding import drawn_finding
from .placement_ids import net_key

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Port, Unit

    from .drawn_netlist import Netlist, PagePart

__all__ = ["PE_KEY", "POWER_KEYS", "join_power", "page_unit", "port_nets", "power_findings", "symbol_classes"]

_KINDS = {power_symbol_key(kind.value): kind for kind in (PowerKind.SUPPLY, PowerKind.GROUND, PowerKind.PE)}
POWER_KEYS = frozenset(_KINDS)
_SUPPLY = power_symbol_key("supply")
_MARKING = marking_slot("")
PE_KEY = power_symbol_key("pe")
RailClass = tuple["Id[Unit] | None", str, object]


def _pe_classes(model: Model, keys: dict[str, str], ids: Mapping[str, Id[Port]]) -> dict[str, str]:
    """The class of each earth-declared PE net: one per cabinet, bonded through its DIN rail (owner 10-29, R1962)."""
    return {keys[p]: f"PE:{item_unit(model, item_of_port(model, one))}" for p, one in ids.items() if port_power_kind(model, one) is PowerKind.PE}


def port_nets(model: Model, ids: Mapping[str, Id[Port]]) -> dict[str, str]:
    """The physical net of each port, spelled as `Net.id` is (`net_key`), built once; the PE nets of a bonded cabinet are one (R1937)."""
    found = {port: net_of(model, one) for port, one in ids.items()}
    nets = {net.ports[0]: net for net in found.values() if net}  # a net by its first port: one spelling per net
    spelled = {first: net_key(model, net.ports) for first, net in nets.items()}
    keys = {port: spelled[net.ports[0]] if net else port for port, net in found.items()}
    held = _pe_classes(model, keys, ids)
    return {port: held.get(key, key) for port, key in keys.items()}


def _symbols(net: Netlist) -> Iterator[tuple[Id[Page], PagePart, str, str, str | None]]:
    """Each port drawn as a power symbol that names its potential (R1631): (page, part, port, symbol key, printed text).

    A ground or PE symbol names it by its kind; a supply symbol only with a text its marking slot prints (the page, never the model).
    """
    for page, part in net.pages.items():
        for symbol in (s for s in part.drawing.symbols if s.key in POWER_KEYS):
            text = next((t for slot, t in symbol.slots if t and slot.startswith(_MARKING)), None)
            for port in symbol.ports if symbol.key != _SUPPLY or text is not None else ():
                yield page, part, port, symbol.key, text


def _inked(net: Netlist, page: Id[Page], part: PagePart, port: str) -> bool:
    """True when the symbol of `port` is joined to its pin by ink: its own port point and the pin lie in one inked piece (R4)."""
    pin, power = part.ports.get(port), part.powers.get(port)
    return pin is not None and power is not None and net.union.find((page, pin)) == net.union.find((page, power))


def page_unit(model: Model, page: Id[Page]) -> Id[Unit] | None:
    """The unit of the drawing set of `page`, `None` for the design's own set: the scope a reader of that page reads its symbols in."""
    return set_unit(layout_of(model, DrawingSet)[layout_of(model, Page)[page].drawing_set])


def _class(model: Model, page: Id[Page], port: Id[Port], key: str, text: str | None) -> RailClass:
    """The (scope, symbol key, printed identity) a power symbol joins by: the unit of the page's drawing set."""
    scope = page_unit(model, page)
    return scope, key, power_identity(model, port, _KINDS[key], text)


def symbol_classes(net: Netlist, model: Model) -> Iterator[tuple[str, RailClass, bool]]:
    """Each power symbol that names its potential: (port, join class, inked)."""
    for page, part, port, key, text in _symbols(net):
        yield port, _class(model, page, net.ids[port], key, text), _inked(net, page, part, port)


def join_power(net: Netlist, model: Model) -> None:
    """Join the inked power symbols of one class: one scope, one symbol, one printed identity (READ-RAILS); ink only (CP-S2c-1).

    A ground class that carries a source unit is its own class, so two unbonded sources stay two pieces (R2590).
    """
    first: dict[RailClass, tuple[Id[Page], tuple[int, int]]] = {}
    for page, part, port, key, text in _symbols(net):
        if _inked(net, page, part, port):
            at = (page, part.ports[port])
            net.union.union(first.setdefault(_class(model, page, net.ids[port], key, text), at), at)


def power_findings(net: Netlist, model: Model) -> tuple[Finding, ...]:
    """POWER_SYMBOL_NOT_JOINED per power symbol that names its potential with no ink to its pin (R4), WRONG_KIND per symbol of another kind."""
    wrong = (
        drawn_finding("POWER_SYMBOL_WRONG_KIND", (net.ids[port],), "a power symbol is not the symbol of its pin's potential kind")
        for part in net.pages.values()
        for symbol in part.drawing.symbols
        for port in (symbol.ports if symbol.key in POWER_KEYS else ())
        if symbol.key != power_symbol_key(port_power_kind(model, net.ids[port]).value)
    )
    loose = (
        drawn_finding(
            "POWER_SYMBOL_NOT_JOINED", (net.ids[port],), "a power symbol has no wire to its pin: report it as a Fransys defect with the model"
        )
        for page, part, port, _, _ in _symbols(net)
        if not _inked(net, page, part, port)
    )
    return (*wrong, *loose)
