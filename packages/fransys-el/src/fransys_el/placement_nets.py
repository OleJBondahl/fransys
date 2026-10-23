"""The nets (facts 4, 10): a physical net with two drawn ends, its rail, its bundle."""

from typing import TYPE_CHECKING

from fransys_layout.core import Bundle, Net, natural_key
from fransys_model.derive import (
    bundle_of,
    function_item,
    item_unit,
    physical_nets,
    port_function,
    port_power_kind,
)

from .kit_keys import PickKey, function_of
from .placement_env import drawn_pins
from .placement_skips import NET_UNDER_TWO_DRAWN_PINS, Skipped, in_order

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.core import PinRef, Sym
    from fransys_model.derive import PhysicalNet
    from fransys_model.kernel import Id
    from fransys_model.vocab import Port, Unit

    from .placement_env import Env

__all__ = ["nets_of"]


def _pin_key(pin: PinRef) -> tuple[object, ...]:
    """Natural order of a pin: its symbol, then its name."""
    return (natural_key(pin.sym), natural_key(pin.pin))


def _bundle(env: Env, first: Id[Port]) -> Bundle | None:
    """The bundle the net travels in, with its pole, else `None`."""
    found = bundle_of(env.model, first)
    return None if found is None else Bundle(found[0].value, found[1])


def _unit(env: Env, lead: PickKey) -> Id[Unit] | None:
    """The unit the item of function `lead` is recorded in."""
    return item_unit(env.model, function_item(env.model, function_of(env.model, lead)))


def _net(
    env: Env, physical: PhysicalNet, unit_of: Mapping[str, Id[Unit] | None]
) -> Net | Skipped | None:
    """The `Net` of `physical`; `None` for a lone port, a `Skipped` unless two ports are drawn."""
    first = physical.ports[0]
    if all(port_function(env.model, p) in env.spare for p in physical.ports):
        return None  # a spare terminal's own net is listed, not drawn (R356)
    if len(physical.ports) < 2:  # noqa: PLR2004 - a pin with no second end is no net (Ruling 86)
        return None
    pins = sorted(set(drawn_pins(env, physical.ports)), key=_pin_key)
    if len(pins) < 2:  # noqa: PLR2004 - a net needs two ends to be a wire
        return Skipped("net", first.value, NET_UNDER_TWO_DRAWN_PINS)
    if port_power_kind(env.model, first).name != "NONE":  # a power net is drawn by anchors
        return None
    crosses = len({unit_of[p.sym] for p in pins}) > 1
    return Net(first.value, tuple(pins), _bundle(env, first), crosses)


def nets_of(env: Env, syms: Sequence[Sym]) -> tuple[tuple[Net, ...], tuple[Skipped, ...]]:
    """Every net with two drawn ends, in the order of its first pin, and the nets left out."""
    lead_of = {sym: lead for lead, sym in env.ids.items()}
    unit_of = {s.id: _unit(env, lead_of[s.id]) for s in syms}
    found = [_net(env, physical, unit_of) for physical in physical_nets(env.model)]
    nets = sorted((n for n in found if isinstance(n, Net)), key=lambda n: _pin_key(n.pins[0]))
    # a lone port gives None: neither a Net nor a Skipped
    return tuple(nets), in_order({n for n in found if isinstance(n, Skipped)})
