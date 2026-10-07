"""D1 step 4, `references` (layout-0090, S1): which net ends are wires, references or stubs.

`references` is the package's one entry point (S12), called before `place` on the planned pages
(S10): it decides the joins (`joins.joined_runs`, on `place`'s own stacking), the star nets
(`nets`), the cuts across pages (`cuts`), a wired conductor's ends apart in another drawing set
(`apart`, S21), the reference and stub texts they give (`markers`,
`off_stubs`, sized by `marker_boxes` for each set's `digits`), and returns them as one
`References` of decisions only (S9): `texts` builds every marker from them on the placed page.
Room's first call for a reference beside an E or W port reads `columns` alone
(`side_reference_rooms`, S11).
"""

from dataclasses import replace
from types import MappingProxyType
from typing import TYPE_CHECKING

from fransys_layout.stages.offstubs import off_ends

from .apart import apart_markers
from .cuts import LINK_FANOUT, LINK_PARTNER_UNLOCATED, CutLocations, links
from .digits import FLOOR, Digits, set_digits
from .joins import JOIN_UNALIGNED, joined_runs
from .markers import split_markers, star_markers
from .nets import side_functions, star_nets, with_orphans, without_starred
from .off_stubs import black_box_sets, with_off_markers
from .power import with_power_ends
from .rails import rail_markers
from .room_check import REFERENCE_BOX_EXCEEDS_ROOM, box_room_findings
from .side_rooms import Wiring, side_reference_rooms
from .turned import turned_stars
from .types import (
    BlackBoxReads,
    MarkerScene,
    OffInputs,
    ReferenceInputs,
    References,
    Star,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Finding

    from .types import Joins, MarkerDecision

__all__ = (
    "JOIN_UNALIGNED",
    "LINK_FANOUT",
    "LINK_PARTNER_UNLOCATED",
    "REFERENCE_BOX_EXCEEDS_ROOM",
    "BlackBoxReads",
    "CutLocations",
    "ReferenceInputs",
    "References",
    "Star",
    "Wiring",
    "black_box_sets",
    "box_room_findings",
    "joined_runs",
    "links",
    "references",
    "side_reference_rooms",
)


def references(inputs: ReferenceInputs) -> tuple[References, tuple[Finding, ...]]:
    """D1 step 4, before `place` (S10): every net end's decision in one `References`."""
    seating = inputs.seating
    joins = joined_runs(
        inputs.connections,
        inputs.functions,
        seating,
        chains=inputs.chains,
        power=frozenset(inputs.power),
    )
    decided, findings = _decided(inputs, joins, MappingProxyType({}))
    # S4: a power end prints no `#n`, so it is no reference group
    digits = set_digits(
        (one for one in decided.markers if not one.symbol), seating.plans, inputs.location_paths
    )
    wider = {one.drawing_set: one.digits for one in digits}
    if any(counts != FLOOR for counts in wider.values()):
        decided, findings = _decided(inputs, joins, wider)
    return replace(decided, digits=digits), findings


def _with_rail_ends(
    markers: tuple[MarkerDecision, ...], inputs: ReferenceInputs, scene: MarkerScene, off: OffInputs
) -> tuple[MarkerDecision, ...]:
    """The power-flagged markers, and a symbol at each rail end that has none (V3)."""
    flagged = with_power_ends(with_off_markers(markers, inputs.seating, off), inputs.power)
    taken = {(one.port, one.drawing_set, one.page) for one in flagged if one.symbol}
    rails = rail_markers(inputs.rail_ends, scene, inputs.exempt, inputs.outward, taken)
    return (*flagged, *with_power_ends(rails, inputs.power))


def _decided(
    inputs: ReferenceInputs, joins: Joins, digits: Mapping[int, Digits]
) -> tuple[References, tuple[Finding, ...]]:
    """`references` on `joins`, with each set's texts sized for its `digits` (`digits` empty)."""
    plans, columns = inputs.seating.plans, inputs.seating.columns
    drawn, placed = inputs.seating.drawn, inputs.seating.seats
    # R7 B4: a net of three or more ports is drawn as markers: its conductors are not routed
    stars = with_orphans(
        star_nets(inputs.connections, inputs.functions, columns, joins.beside),
        inputs.net_groups,
        side_functions(columns),
    )
    # S20 M12: a wire that would turn back round a device is a reference pair
    starred = {handle for star in stars for handle in star.wires}
    stars = (
        *stars,
        *turned_stars(
            tuple(c for c in inputs.connections if c.handle not in starred),
            inputs.functions,
            inputs.seating,
            chains=inputs.chains,
            off_ports=frozenset(end.port for end in inputs.off_ends),
        ),
    )
    stars = tuple(replace(star, exempt=inputs.exempt) for star in stars)
    connections, net_groups = without_starred(inputs.connections, inputs.net_groups, stars)
    scene = MarkerScene(placed, drawn, inputs.sheet, inputs.profile, digits)
    locations = CutLocations(
        location_paths=inputs.location_paths,
        units={plan.drawing_set: plan.unit for plan in plans},
        function_units={spec.function: spec.unit for spec in inputs.functions},
    )
    decisions, markers, echoes, link_findings = links(connections, net_groups, scene, locations)
    markers = (
        *markers,
        *star_markers(stars, scene),
        *split_markers(columns, scene, connections),
        *apart_markers(connections, scene, inputs.exempt, stars),
    )
    off = OffInputs(inputs.sheet, inputs.profile, inputs.crossing, inputs.off_texts, inputs.outward)
    decided = References(
        joins=joins.runs,
        decisions=decisions,
        markers=_with_rail_ends(markers, inputs, scene, off),
        off_ends=off_ends(inputs.off_ends, inputs.off_texts),
        digits=(),
        echoes=echoes,
        connections=connections,
        net_groups=net_groups,
    )
    return decided, (*joins.findings, *link_findings)
