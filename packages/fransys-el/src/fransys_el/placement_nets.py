"""The nets (facts 4, 10): a physical net with two drawn ends, its rail, its bundle."""

from typing import TYPE_CHECKING, cast

from fransys_layout.core import Bundle, Net, natural_key
from fransys_model.derive import (
    boundary_rail_wires,
    bundle_of,
    conductor_ends,
    drawn_net_of,
    drawn_physical_nets,
    is_rail_terminal,
    item_of_port,
    no_conductor_at,
    port_function,
    port_power_kind,
)
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached

from .placement_env import drawn_pins
from .placement_forms import DRAWN_FORMS
from .placement_ids import net_key, net_lead, symbol_key
from .placement_sets import home_unit
from .placement_skips import NET_UNDER_TWO_DRAWN_PINS, Skipped, in_order

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.core import PinRef, Sym
    from fransys_model.derive import PhysicalNet
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Conductor, Function, Port, Unit

    from .placement_env import Env

_TWO_ENDS = 2  # a net needs two ends to be a wire

__all__ = ["net_ports", "nets_of"]


def _pin_key(pin: PinRef) -> tuple[object, ...]:
    """Natural order of a pin: its symbol, then its name."""
    return (natural_key(pin.sym), natural_key(pin.pin))


def _bundle(env: Env, ports: Sequence[Id[Port]]) -> Bundle | None:
    """The bundle every port of the net travels in, with its pole; `None` when the ports do not agree (R1623)."""
    rows = {bundle_of(env.model, p, DRAWN_FORMS) for p in ports}
    found = next(iter(rows)) if len(rows) == 1 else None
    return None if found is None else Bundle(net_key(env.model, cast("PhysicalNet", drawn_net_of(env.model, found[0])).ports), found[1], found[2])


def _net(env: Env, ports: Sequence[Id[Port]], unit_of: Mapping[str, Id[Unit] | None]) -> Net | Skipped | None:
    """The `Net` of `ports`; `None` for a lone port, a `Skipped` unless two ports are drawn."""
    if all(port_function(env.model, p) in env.spare for p in ports):
        return None  # a spare terminal's own net is listed, not drawn (R356)
    if len(ports) < _TWO_ENDS:  # a pin with no second end is no net (Ruling 86)
        return None
    first = net_lead(env.model, ports)  # the lead port by order text names the net, whatever order `ports` comes in (R1615)
    name = symbol_key(env.model, first)
    pins = sorted(set(drawn_pins(env, ports)), key=_pin_key)
    if len(pins) < _TWO_ENDS:
        if all(no_conductor_at(env.model, p) for p in ports):
            return None  # only a mate or a join inside a part joins them: no conductor, nothing to draw (R616.3, R1765)
        return Skipped("net", name, NET_UNDER_TWO_DRAWN_PINS)
    crosses = len({unit_of[p.sym] for p in pins}) > 1
    return Net(name, tuple(pins), _bundle(env, ports), crosses)


def _rail_wires(model: Model) -> list[tuple[Id[Port], ...]]:
    """The ends of the boundary rail terminals' wires, the wires of one terminal as one group."""
    groups: dict[Id[Function] | Id[Conductor], set[Id[Port]]] = {}
    for wire in boundary_rail_wires(model):
        ends = conductor_ends(model, wire)
        terminal = next((p for p in ends if is_rail_terminal(model, item_of_port(model, p))), None)  # else the wire is its own group
        home = None if terminal is None else port_function(model, terminal)
        groups.setdefault(wire if home is None else home, set()).update(ends)
    return [tuple(g) for g in groups.values()]


@digest_cached(DIGEST_CACHE_SIZE)
def net_ports(model: Model) -> frozendict[str, Id[Port]]:
    """Every net id the core is handed, by its lead port: how a reader goes from a net id back to a record, with no parsing."""
    found = {}
    for ports in (*(ph.ports for ph in drawn_physical_nets(model)), *_rail_wires(model)):
        lead = net_lead(model, ports)
        found[symbol_key(model, lead)] = lead
    return frozendict(found)


def nets_of(env: Env, syms: Sequence[Sym]) -> tuple[tuple[Net, ...], tuple[Skipped, ...]]:
    """Every net with two drawn ends, in the order of its first pin, and the nets left out."""
    lead_of = {sym: lead for lead, sym in env.ids.items()}
    unit_of = {s.id: home_unit(env.model, lead_of[s.id]) for s in syms}
    # a power net is drawn by anchors (G08-POWER); a boundary rail terminal's wires are nets of their own ends
    found = [_net(env, ph.ports, unit_of) for ph in drawn_physical_nets(env.model) if port_power_kind(env.model, ph.ports[0]).name == "NONE"]
    found += [_net(env, ends, unit_of) for ends in _rail_wires(env.model)]
    nets = sorted((n for n in found if isinstance(n, Net)), key=lambda n: _pin_key(n.pins[0]))
    # a lone port gives None: neither a Net nor a Skipped
    return tuple(nets), in_order({n for n in found if isinstance(n, Skipped)})
