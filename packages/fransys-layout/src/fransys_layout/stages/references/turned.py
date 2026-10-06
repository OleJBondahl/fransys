"""S20 M12: a conductor that would enter a pin from the far side is a reference pair.

A device stands so that what connects to its top pins is above it and what connects to its
bottom pins is below it (owner, 2026-10-01). A wire from an N pin to a pin below the device's
bottom edge, or from an S pin to a pin above its top edge, leaves the pin outward and comes back
past the device: a 180 degree turn. Such a conductor is drawn as a reference at each end
instead (`nets.wires_star`: the star of its ports), decided from `place`'s own stacking like the
joins (S12). A link of a terminal chain (`terminal_rows`) never turns: its row
holds them level, and where the row cannot fit it stays a wire all the same.
"""

from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_model.kernel import UnionFind

from .joins import Spot, port_spots, turns_back
from .nets import side_functions, wires_star

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.terminal_rows import TerminalChains
    from fransys_layout.stages.types import Connection, FunctionSpec
    from fransys_model.kernel import Id

    from .types import Seating, Star


def turned_stars(
    connections: tuple[Connection, ...],
    specs: tuple[FunctionSpec, ...],
    seating: Seating,
    *,
    chains: TerminalChains,
    off_ports: frozenset[Id[Any]] = frozenset(),
) -> tuple[Star, ...]:
    """The stars of the conductors of `connections` that turn back round a device (S20 M12)."""
    spots = port_spots(seating.columns, seating.plans, seating.drawn, seating.stacks)
    side = side_functions(seating.columns)
    turned = [one for one in connections if _turns(one, spots, side, chains)]
    joined: UnionFind[Id[Any]] = UnionFind()
    for one in turned:
        joined.union(one.a.port, one.b.port)
    groups: dict[Id[Any], list[Connection]] = defaultdict(list)
    for one in turned:
        groups[joined.find(one.a.port)].append(one)
    stars = (wires_star(wires, specs) for wires in groups.values())
    found = (_at_stub(star, off_ports) for star in stars if star is not None)
    return tuple(sorted(found, key=lambda s: s.ref.port))


def _at_stub(star: Star, off_ports: frozenset[Id[Any]]) -> Star:
    """`star` with its reference moved to its first port that carries an off stub, if any."""
    at = sorted((ref for ref in star.ports if ref.port in off_ports), key=lambda ref: ref.port)
    return replace(star, ref=at[0]) if at else star


def _turns(
    conductor: Connection,
    spots: Mapping[Id[Any], tuple[Spot, ...]],
    side: frozenset[Id[Any]],
    chains: TerminalChains,
) -> bool:
    """Whether `conductor` leaves a pin outward and comes back past its device."""
    ends = {conductor.a.function, conductor.b.function}
    if len(ends) == 1 or ends & side or conductor.handle in chains.links:
        return False
    pairs = [
        (x, y)
        for x in spots.get(conductor.a.port, ())
        for y in spots.get(conductor.b.port, ())
        if x.page == y.page
    ]
    return len(pairs) == 1 and (turns_back(*pairs[0]) or turns_back(pairs[0][1], pairs[0][0]))
