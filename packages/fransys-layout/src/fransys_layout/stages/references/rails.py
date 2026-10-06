"""V3: a pin wired to a rail takes the rail's power symbol, though no wire or reference leads there.

A rail wire is not drawn, so its pin has no marker to flag. One marker per pin and page stands in
for it; `power.with_power_ends` then gives it the symbol. A pin that already has one gets no second.
"""

from typing import TYPE_CHECKING, Any

from .cuts import link_world
from .ends import EndRead, marker_end
from .markers import decided
from .nets import shown
from .types import MarkerSpec, PortEnd

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from fransys_layout.stages.types import RailEnd
    from fransys_model.kernel import Id

    from .types import MarkerDecision, MarkerScene


def rail_markers(
    ends: tuple[RailEnd, ...],
    scene: MarkerScene,
    exempt: frozenset[tuple[Id[Any], int]],
    outward: Mapping[Id[Any], frozenset[int]],
    taken: Collection[tuple[Id[Any], int, int]],
) -> tuple[MarkerDecision, ...]:
    """One marker per rail end and page it is shown on, none at a `(port, set, page)` in `taken`."""
    world = link_world(scene)
    found = {}
    side, leave = marker_end(EndRead("rail_branch"))
    for end in ends:
        for page in shown(world, end.ref, exempt):
            key = (end.ref.port, *page)
            # a nested unit's boundary port: a black box in its `outward` sets, its lead ends there
            if key not in taken and page[0] not in outward.get(end.ref.function, ()):
                at = (PortEnd(ref=end.ref, page=page), leave)
                spec = MarkerSpec(end.connection, at, at, 1, kind="branch", side=side)
                found[key] = decided(spec, scene)
    return tuple(found.values())
