"""The oracle of the symdef layer: placement_pins as it was on the old engine's `symbol_geometry`.

A copy taken before the geometry moved into `fransys_layout.symbols`; it dies with the old
engine at SCHEMATIC-FLIP (SB9). Tests compare the layer's values against it."""

from typing import TYPE_CHECKING, cast

from fransys_el.placement_kit import refuse
from fransys_el.placement_sides import box_sides

from electrical_symbols import default_order, is_generic_box
from fransys_layout import generic_box_geometry, symbol_geometry
from fransys_layout.core import BoxSpec, Pin, natural_key
from fransys_model.derive import port_potential_rank, stands
from fransys_model.kernel import natural_key as kernel_key

if TYPE_CHECKING:
    from fransys_el.placement_env import Env
    from fransys_el.placement_kit import Pick

    from fransys_layout import SymbolGeometry
    from fransys_layout.core import Side
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function

__all__ = ["box_of", "geometry_of", "nodes_of", "pins_of"]

EDGE = ("N", "S")


def geometry_of(env: Env, lead: Id[Function], pick: Pick) -> SymbolGeometry:
    """The geometry of the pick's symbol; a generic box is built over the pick's port names."""
    if is_generic_box(pick.key):
        names = default_order(pick.ports.values(), kernel_key)
        return generic_box_geometry(names, box_sides(env.model, pick, names))
    try:
        geometry = symbol_geometry(pick.key, poles=pick.poles)
    except Exception as error:  # noqa: BLE001 - the library's own errors, re-raised as ours
        refuse(f"function {env.ids[lead]}, symbol {pick.key!r}", f"pick a library symbol: {error}")
    unknown = set(pick.ports.values()) - {p.name for p in geometry.ports}
    if unknown:
        refuse(
            f"function {env.ids[lead]}, symbol port {min(unknown)!r}",
            f"name a port of symbol {pick.key!r} in Pick.ports",
        )
    return geometry


def nodes_of(geometry: SymbolGeometry) -> tuple[tuple[str, ...], ...]:
    """The pins that are one point, each node's pins and the nodes in natural order."""
    listed = {name for node in geometry.nodes for name in node}
    alone = ((p.name,) for p in geometry.ports if p.name not in listed)
    groups = (tuple(sorted(node, key=natural_key)) for node in (*geometry.nodes, *alone))
    return tuple(sorted(groups, key=lambda node: natural_key(node[0])))


_END_BIAS = {"SUPPLY": -1, "GROUND": 1, "PE": 1}


def _bias(env, port, power) -> tuple[int, int]:
    if port not in power:
        return 0, 0
    rank = port_potential_rank(env.model, port)
    return _END_BIAS[power[port].name], 1000 if rank is None else rank


def pins_of(env: Env, pick: Pick, geometry: SymbolGeometry) -> tuple[Pin, ...]:
    """One `Pin` per symbol port, in natural order; the end bias and rank from its port's rail."""
    nodes = nodes_of(geometry)
    node_of = {name: index for index, node in enumerate(nodes) for name in node}
    port_of = {name: port for port, name in pick.ports.items()}
    power = stands(env.model)
    ports = sorted(geometry.ports, key=lambda p: natural_key(p.name))
    return tuple(
        Pin(
            p.name,
            cast("Side", p.facing.value.upper()),
            p.at.x,
            p.at.y,
            node_of[p.name],
            *_bias(env, port_of.get(p.name), power),
        )
        for p in ports
    )


def box_of(env: Env, pick: Pick, geometry: SymbolGeometry, pins: tuple[Pin, ...]) -> BoxSpec | None:
    """Fact 16: the movable pins of a generic box in printed-marking order, else `None`."""
    if not is_generic_box(pick.key):
        return None
    edge = [p for p in pins if p.side in EDGE]
    if not edge:
        return None
    order = default_order((p.id for p in edge), kernel_key)
    sides = sorted({p.side for p in edge})
    natural = max(sides, key=lambda side: sum(p.side == side for p in edge))
    margin = min(p.dx for p in edge) - geometry.body.x
    return BoxSpec(order, natural, env.conventions.options.box_pin_pitch_min, margin)
