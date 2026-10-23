"""The symbol, pins, nodes and box spec of one pick (facts 1, 5 and 16), read from the layer."""

from typing import TYPE_CHECKING

from electrical_symbols import (
    G_PER_MODULE,
    box_port_marking,
    default_order,
    generic_box,
    is_generic_box,
)
from fransys_layout.core import BoxSpec, Pin, natural_key
from fransys_layout.symbols import library_symbol, symbol_shape
from fransys_model.derive import port_potential_rank, stands
from fransys_model.derive.text_width import marking_widths
from fransys_model.kernel import natural_key as kernel_key

from .placement_kit import refuse
from .placement_sides import box_sides
lazy from .kit_keys import PickKey

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.symbols import LibrarySymbol, Shape
    from fransys_model.kernel import Id
    from fransys_model.vocab import Port, PowerKind

    from .placement_env import Env
    from .placement_kit import Pick

__all__ = ["box_of", "nodes_of", "pins_of", "shape_of", "symbol_of"]

EDGE = ("N", "S")

#: Where a power pin prefers its chain end: supply to the head, ground and PE to the foot.
END_BIAS = {"SUPPLY": -1, "GROUND": 1, "PE": 1}

#: A rail whose potential no supply ranks draws below every ranked one.
UNRANKED = 1000


def symbol_of(env: Env, lead: PickKey, pick: Pick) -> LibrarySymbol:
    """The pick's library symbol; a generic box is built over the pick's port names."""
    if is_generic_box(pick.key):
        names = default_order(pick.ports.values(), kernel_key)
        widths = marking_widths((box_port_marking(n) for n in names), height=G_PER_MODULE)
        return generic_box(names, box_sides(env.model, pick, names), marking_widths=widths)
    try:
        return library_symbol(env.library, pick.key, pick.poles)
    except Exception as error:  # noqa: BLE001 - the layer's own errors, re-raised as ours
        refuse(
            f"function {env.ids[lead]}, symbol {pick.key!r}",
            f"pick a library symbol: {error}",
            env.ids[lead],
        )


def shape_of(env: Env, lead: PickKey, pick: Pick, symbol: LibrarySymbol) -> Shape:
    """The symbol at R0; `ProblemError` for a pick naming a port the symbol lacks."""
    shape = symbol_shape(symbol, env.library)
    unknown = set(pick.ports.values()) - set(shape.pins)
    if unknown:
        refuse(
            f"function {env.ids[lead]}, symbol port {min(unknown)!r}",
            f"name a port of symbol {pick.key!r} in Pick.ports",
            env.ids[lead],
        )
    return shape


def nodes_of(shape: Shape) -> tuple[tuple[str, ...], ...]:
    """The pins that are one point, each node's pins and the nodes in natural order."""
    listed = {name for node in shape.nodes for name in node}
    alone = ((name,) for name in shape.pins if name not in listed)
    groups = (tuple(sorted(node, key=natural_key)) for node in (*shape.nodes, *alone))
    return tuple(sorted(groups, key=lambda node: natural_key(node[0])))


def pins_of(env: Env, pick: Pick, shape: Shape) -> tuple[Pin, ...]:
    """One `Pin` per symbol port, in natural order; the end bias and rank from its port's rail."""
    node_of = {name: index for index, node in enumerate(nodes_of(shape)) for name in node}
    port_of = {name: port for port, name in pick.ports.items()}
    power = stands(env.model)
    return tuple(
        Pin(
            name,
            shape.pins[name].side,
            shape.pins[name].dx,
            shape.pins[name].dy,
            node_of[name],
            *_bias(env, port_of.get(name), power),
        )
        for name in sorted(shape.pins, key=natural_key)
    )


def _bias(env: Env, port: Id[Port] | None, power: Mapping[Id[Port], PowerKind]) -> tuple[int, int]:
    """The (end bias, end rank) of a pin on a power net; (0, 0) for any other pin."""
    if port is None or port not in power:
        return 0, 0
    rank = port_potential_rank(env.model, port)
    return END_BIAS[power[port].name], UNRANKED if rank is None else rank


def box_of(env: Env, pick: Pick, shape: Shape, pins: tuple[Pin, ...]) -> BoxSpec | None:
    """Fact 16: the movable pins of a generic box in printed-marking order, else `None`."""
    if not is_generic_box(pick.key):
        return None
    edge = [p for p in pins if p.side in EDGE]
    if not edge:
        return None
    order = default_order((p.id for p in edge), kernel_key)
    sides = sorted({p.side for p in edge})
    natural = max(sides, key=lambda side: sum(p.side == side for p in edge))
    margin = min(p.dx for p in edge) - shape.body.x
    return BoxSpec(order, natural, env.conventions.options.box_pin_pitch_min, margin)
