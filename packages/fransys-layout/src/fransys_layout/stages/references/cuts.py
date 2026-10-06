"""Links: connections cut by a page boundary (docs/design/links.md 6.6).

The four cases are decided from the pages each function is seated on and what the engine read
from the model, never from geometry: a decision holds no coordinate (S9).
"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING
lazy from collections.abc import Sequence

from fransys_layout.geometry import LayoutError
from fransys_layout.stages.cutpages import cut_pages
from fransys_layout.stages.types import LinkCase, LinkDecision
from fransys_model.kernel import Finding, Severity

from .digits import FLOOR
from .ends import EndRead, marker_end
from .link_case import CutRead, drawn_of, link_case
from .marker_boxes import reference_size
from .types import Cut, LinkWorld, MarkerDecision, PortEnd

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.types import (
        Connection,
        Handle,
        NetGroup,
        PortRef,
        Profile,
        SheetFormat,
    )
    from fransys_model.kernel import AuthoringKey

    from .types import LocationPath, MarkerScene, Page, Seated

LINK_FANOUT = "LINK_FANOUT"
LINK_PARTNER_UNLOCATED = "LINK_PARTNER_UNLOCATED"


@dataclass(frozen=True, slots=True)
class CutLocations:
    """Where a cut's ends are, by unit and by path: the maps its case and its findings read."""

    location_paths: Mapping[int, LocationPath]
    units: Mapping[int, Handle | None]
    function_units: Mapping[Handle, Handle | None]


def links(
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    scene: MarkerScene,
    locations: CutLocations,
) -> tuple[
    tuple[LinkDecision, ...],
    tuple[MarkerDecision, ...],
    tuple[Cut, ...],
    tuple[Finding, ...],
]:
    """Decide every cut: decisions, marker decisions, tag-echo cuts, findings (links.md 6.6)."""
    units = locations.units
    world = link_world(scene)
    terminals = _terminals(connections, net_groups, world)
    cuts = _cuts(connections, net_groups, world, locations.function_units, units)
    cases = [(cut, link_case(CutRead(cut, terminals, world, units))) for cut in cuts]
    decisions = sorted(
        (
            LinkDecision(
                connection=cut.connection, a=cut.ends[0].ref.port, b=cut.ends[1].ref.port, case=case
            )
            for cut, case in cases
        ),
        key=lambda one: (one.connection, one.a, one.b),
    )
    severed = [cut for cut, case in cases if case is LinkCase.SEVERED]
    markers = sorted(
        (
            marker
            for cut in severed
            for marker in _markers(cut, scene.sheet, scene.profile, scene.digits)
        ),
        key=lambda one: (one.connection, one.port, one.side.value),
    )
    tag_echoes = [cut for cut, case in cases if case is LinkCase.TAG_ECHO]
    findings = (*_fanout(severed), *_unlocated([*severed, *tag_echoes], locations.location_paths))
    return (
        tuple(decisions),
        tuple(markers),
        tuple(tag_echoes),
        tuple(sorted(findings, key=lambda finding: (finding.code, finding.subjects))),
    )


def link_placements(seats: tuple[Seated, ...]) -> dict[Handle, dict[Page, AuthoringKey]]:
    """Every function's column by page; two seats on one page is an assembly fault."""
    found: dict[Handle, dict[Page, AuthoringKey]] = defaultdict(dict)
    for one in seats:
        page = (one.drawing_set, one.page)
        if page in found[one.function]:
            msg = "one function is placed twice on one page"
            raise LayoutError(msg)
        found[one.function][page] = one.column
    return dict(found)


def link_world(scene: MarkerScene) -> LinkWorld:
    """The scene's seats by page and its drawn functions by handle."""
    return LinkWorld(
        where=link_placements(scene.seats), drawn_of={one.function: one for one in scene.drawn}
    )


def _pages(ref: PortRef, world: LinkWorld) -> dict[Page, AuthoringKey]:
    """The pages a port's function is drawn on; a function drawn nowhere is a fault."""
    pages = world.where.get(ref.function)
    if pages is None:
        msg = "an end function of a connection or net group is not placed on any page"
        raise LayoutError(msg)
    return pages


def _terminals(
    connections: tuple[Connection, ...], net_groups: tuple[NetGroup, ...], world: LinkWorld
) -> dict[Handle, frozenset[Handle]]:
    """The terminal functions on each physical net: those at an end of one of its wires."""
    found: dict[Handle, set[Handle]] = defaultdict(set)
    for conductor in connections:
        found[conductor.physical_net].update(
            ref.function
            for ref in (conductor.a, conductor.b)
            if drawn_of(ref, world).roles.terminal
        )
    for group in net_groups:
        found[group.physical_net].update(
            ref.function for ref in group.ports if drawn_of(ref, world).roles.terminal
        )
    return {net: frozenset(functions) for net, functions in found.items()}


def _cuts(
    connections: tuple[Connection, ...],
    net_groups: tuple[NetGroup, ...],
    world: LinkWorld,
    function_units: Mapping[Handle, Handle | None],
    units: Mapping[int, Handle | None],
) -> list[Cut]:
    """Every cut, conductors then net groups; a conductor's pages come from `cut_pages` (0078)."""
    cuts = []
    for conductor in connections:
        pages_a, pages_b = _pages(conductor.a, world), _pages(conductor.b, world)
        if pages_a.keys() & pages_b.keys():
            continue
        page_a, page_b = cut_pages(
            pages_a,
            pages_b,
            own_units=(
                function_units.get(conductor.a.function),
                function_units.get(conductor.b.function),
            ),
            set_units=units,
        )
        cuts.append(
            Cut(
                connection=conductor.handle,
                physical_net=conductor.physical_net,
                ends=(PortEnd(ref=conductor.a, page=page_a), PortEnd(ref=conductor.b, page=page_b)),
            )
        )
    wired = {frozenset((c.ends[0].ref.port, c.ends[1].ref.port)) for c in cuts}
    for group in net_groups:
        lowest: dict[Page, PortRef] = {}
        for ref in group.ports:
            for page in _pages(ref, world):
                lowest.setdefault(page, ref)
        pages = sorted(lowest)
        for before, after in pairwise(pages):
            ends = sorted(
                (
                    PortEnd(ref=lowest[before], page=before),
                    PortEnd(ref=lowest[after], page=after),
                ),
                key=lambda end: end.ref.port,
            )
            if frozenset((ends[0].ref.port, ends[1].ref.port)) in wired:
                continue  # a conductor already cuts these two ports: one marker pair, not two
            cuts.append(
                Cut(connection=group.net, physical_net=group.physical_net, ends=(ends[0], ends[1]))
            )
    return cuts


def _markers(
    cut: Cut, sheet: SheetFormat, profile: Profile, digits: Mapping[int, tuple[int, int]]
) -> list[MarkerDecision]:
    """The owner marker at the end on the earlier page and the user marker at the other (D4)."""
    owner, user = sorted(cut.ends, key=lambda end: end.page)
    ends = ((owner, user, EndRead("cut", earlier=True)), (user, owner, EndRead("cut")))
    return [
        MarkerDecision(
            connection=cut.connection,
            function=end.ref.function,
            port=end.ref.port,
            side=marker_end(read)[0],
            drawing_set=end.page[0],
            page=end.page[1],
            size=reference_size(sheet, profile, digits=digits.get(end.page[0], FLOOR)),
            partner=partner.ref.port,
            partner_set=partner.page[0],
            partner_page=partner.page[1],
        )
        for end, partner, read in ends
    ]


def _unlocated(
    cuts: Sequence[Cut], location_paths: Mapping[int, LocationPath]
) -> tuple[Finding, ...]:
    """One `LINK_PARTNER_UNLOCATED` per severed or tag-echo cut between two drawing sets."""
    return tuple(
        Finding(
            code=LINK_PARTNER_UNLOCATED,
            severity=Severity.WARNING,
            subjects=tuple(end.ref.port for end in cut.ends if end.page[0] not in location_paths),
            message="a signal crosses into a drawing set with no location: name one",
        )
        for cut in cuts
        if cut.ends[0].page[0] != cut.ends[1].page[0]
        and any(end.page[0] not in location_paths for end in cut.ends)
    )


def _fanout(severed: Sequence[Cut]) -> tuple[Finding, ...]:
    """One `LINK_FANOUT` per physical net and page pair that carries more than one severed cut."""
    groups: dict[tuple[Handle, Page, Page], list[Handle]] = defaultdict(list)
    for cut in severed:
        first, second = sorted(end.page for end in cut.ends)
        groups[cut.physical_net, first, second].append(cut.connection)
    return tuple(
        sorted(
            (
                Finding(
                    code=LINK_FANOUT,
                    severity=Severity.WARNING,
                    subjects=tuple(connections),
                    message="net severed more than once between two pages: use a terminal",
                )
                for connections in groups.values()
                if len(connections) > 1
            ),
            key=lambda finding: (finding.code, finding.subjects),
        )
    )
