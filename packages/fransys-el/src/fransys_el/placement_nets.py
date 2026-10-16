"""The nets (facts 4, 10): a physical net with two drawn ends, its rail, its bundle."""

from typing import TYPE_CHECKING

from fransys_layout.core import Bundle, Net, Rail, natural_key
from fransys_model.derive import (
    bundle_of,
    function_item,
    item_unit,
    physical_nets,
    port_potential_rank,
    port_power_kind,
)

from .placement_env import pin_ref
from .placement_skips import NET_UNDER_TWO_DRAWN_PINS, Skipped, in_order

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.core import PinRef, Sym
    from fransys_model.derive import PhysicalNet
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function, Port, Unit

    from .placement_env import Env

__all__ = ["UNRANKED", "nets_of"]

#: A rail whose potential no supply ranks draws below every ranked one.
UNRANKED = 1000


def _pin_key(pin: PinRef) -> tuple[object, ...]:
    """Natural order of a pin: its symbol, then its name."""
    return (natural_key(pin.sym), natural_key(pin.pin))


def _rail(env: Env, first: Id[Port]) -> Rail | None:
    """`Rail` for a net whose first port has a potential rank or a power kind, else `None`."""
    rank = port_potential_rank(env.model, first)
    power = port_power_kind(env.model, first).name
    if rank is None and power == "NONE":
        return None
    return Rail(UNRANKED if rank is None else rank, power)


def _bundle(env: Env, first: Id[Port]) -> Bundle | None:
    """The bundle the net travels in, with its pole, else `None`."""
    found = bundle_of(env.model, first)
    return None if found is None else Bundle(found[0].value, found[1])


def _unit(env: Env, lead: Id[Function]) -> Id[Unit] | None:
    """The unit the item of function `lead` is recorded in."""
    return item_unit(env.model, function_item(env.model, lead))


def _net(env: Env, physical: PhysicalNet, unit_of: Mapping[str, Id[Unit] | None]) -> Net | Skipped:
    """The `Net` of `physical`; a `Skipped` unless two of its ports are drawn."""
    pins = sorted({pin_ref(env, p) for p in physical.ports}, key=_pin_key)
    first = physical.ports[0]
    if len(pins) < 2:  # noqa: PLR2004 - a net needs two ends to be a wire
        return Skipped("net", first.value, NET_UNDER_TWO_DRAWN_PINS)
    crosses = len({unit_of[p.sym] for p in pins}) > 1
    return Net(first.value, tuple(pins), _rail(env, first), _bundle(env, first), crosses)


def nets_of(env: Env, syms: Sequence[Sym]) -> tuple[tuple[Net, ...], tuple[Skipped, ...]]:
    """Every net with two drawn ends, in the order of its first pin, and the nets left out."""
    lead_of = {sym: lead for lead, sym in env.ids.items()}
    unit_of = {s.id: _unit(env, lead_of[s.id]) for s in syms}
    found = [_net(env, physical, unit_of) for physical in physical_nets(env.model)]
    nets = sorted((n for n in found if isinstance(n, Net)), key=lambda n: _pin_key(n.pins[0]))
    return tuple(nets), in_order({n for n in found if isinstance(n, Skipped)})
