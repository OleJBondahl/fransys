"""R7 B4 (deep dive): the star and split texts' decisions, and the one decider they share.

A star net is drawn as one marker per port (`nets.py` finds the nets); this module decides those
texts and the C17 split texts: the port and page each stands at, which of its function's ports
it leaves by, what it names and its box's size. `texts.markers` builds each marker (S9).
"""

from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_model.derive.drawing_text import marker_lines

from .cuts import link_world
from .digits import FLOOR
from .ends import EndRead, marker_end
from .marker_boxes import reference_size
from .nets import branch_pages, shown
from .types import Leave, LinkWorld, MarkerDecision, MarkerSpec, PortEnd

if TYPE_CHECKING:
    from fransys_layout.stages.types import Column, Connection, Profile
    from fransys_model.kernel import Id

    from .types import MarkerScene, Page, Star


def terminal_lift(profile: Profile) -> int:
    """How far a terminal's marker stands out, clear of a packed strip row's point texts (C15)."""
    return 2 * profile.text_height


def star_markers(stars: tuple[Star, ...], scene: MarkerScene) -> tuple[MarkerDecision, ...]:
    """One text per seated counted port and one at each reference seat (C22, 0070, LD3 d, C15)."""
    world = link_world(scene)
    plans = [plan for star in stars if (plan := _star_plan(star, world)) is not None]
    found = [m for plan in plans for m in _page_markers(plan, scene)]
    owner = {port.port: one.function for one in scene.drawn for port in one.ports}
    terminals = {one.function for one in scene.drawn if one.roles.terminal}
    step = terminal_lift(scene.profile)
    return tuple(
        replace(m, out=m.out + step) if owner.get(m.port) in terminals else m for m in found
    )


def _star_plan(
    star: Star, world: LinkWorld
) -> (
    tuple[
        Id[Any],
        dict[Page, tuple[PortEnd, Leave]],
        dict[Page, list[tuple[PortEnd, Leave]]],
    ]
    | None
):
    """Pass 1 of `star_markers`: one star's reference seats and its branches' page groups."""
    ref_pages = sorted(shown(world, star.ref, star.exempt))
    if not ref_pages:
        return None
    # the reference is a terminal point when not by designation: all its ports are one
    leave = marker_end(EndRead("star_ref", by_designation=star.by_designation))[1]
    refs = {page: (PortEnd(ref=star.ref, page=page), leave) for page in ref_pages}
    home = refs[ref_pages[0]]
    connection = min(star.conductors or star.wires)
    naming: dict[Page, list[tuple[PortEnd, Leave]]] = defaultdict(list)
    for ref in star.ports:
        if ref.port == star.ref.port:
            continue
        pages = sorted(shown(world, ref, star.exempt))
        # C3 per set: one text per wired cluster, none in the reference's cluster
        for page in branch_pages(pages, ref.port, star.ref.port, star.set_cluster):
            end = (PortEnd(ref=ref, page=page), marker_end(EndRead("star_branch"))[1])
            own_set = [r for p, r in refs.items() if p[0] == page[0]]
            target = refs.get(page) or next(iter(own_set), home)
            naming[target[0].page].append(end)
    return connection, refs, naming


def _page_markers(
    plan: tuple[
        Id[Any],
        dict[Page, tuple[PortEnd, Leave]],
        dict[Page, list[tuple[PortEnd, Leave]]],
    ],
    scene: MarkerScene,
) -> list[MarkerDecision]:
    """Pass 2 of `star_markers`: every text of one star's page-groups (LD3 (d), symmetric)."""
    connection, refs, naming = plan
    found = []
    branch_side = marker_end(EndRead("star_branch"))[0]
    ref_side = marker_end(EndRead("star_ref"))[0]
    for page, ref_end in refs.items():
        branches = naming[page]
        if not branches:
            continue
        lines = marker_lines(len(branches))  # LD3 (d), C2: one count for all, one past two
        for end in branches:
            spec = MarkerSpec(connection, end, ref_end, lines, kind="branch", side=branch_side)
            found.append(decided(spec, scene))
        spec = MarkerSpec(connection, ref_end, branches[0], lines, kind="ref", side=ref_side)
        found.append(decided(spec, scene))
    return found


def split_markers(
    columns: tuple[Column, ...], scene: MarkerScene, connections: tuple[Connection, ...]
) -> tuple[MarkerDecision, ...]:
    """C17: a C7 split says where it continues."""
    world = link_world(scene)
    terminal = {one.function for one in scene.drawn if one.roles.terminal}
    found = []
    for column in columns:
        for cell in column.cells:
            if not cell.replica or cell.host is None or cell.host not in terminal:
                continue
            wire = next(
                (
                    c
                    for c in connections
                    if {c.a.function, c.b.function} == {cell.function, cell.host}
                ),
                None,
            )
            pages = world.where.get(cell.function, {})
            there = next((pg for pg, key in pages.items() if key == column.key), None)
            home = next((pg for pg, key in sorted(pages.items()) if key != column.key), None)
            if wire is None or there is None or home is None:
                continue
            ref = wire.a if wire.a.function == cell.function else wire.b
            home_side, home_leave = marker_end(EndRead("split", at_home=True, terminal=True))
            there_side, there_leave = marker_end(EndRead("split", terminal=True))
            at_home = (PortEnd(ref=ref, page=home), home_leave)
            at_there = (PortEnd(ref=ref, page=there), there_leave)
            owner = MarkerSpec(wire.handle, at_home, at_there, 1, kind="branch", side=home_side)
            user = MarkerSpec(wire.handle, at_there, at_home, 1, kind="branch", side=there_side)
            found.extend((decided(owner, scene), decided(user, scene)))
    step = terminal_lift(scene.profile)
    return tuple(replace(m, out=m.out + step) for m in found)


def decided(spec: MarkerSpec, scene: MarkerScene) -> MarkerDecision:
    """A star or split text; LD3 (c): a fixed-width box, `spec.lines` lines tall."""
    (end, leave), (partner, partner_leave) = spec.end, spec.partner
    digits = scene.digits.get(end.page[0], FLOOR)
    return MarkerDecision(
        connection=spec.connection,
        function=end.ref.function,
        port=end.ref.port,
        side=spec.side,
        drawing_set=end.page[0],
        page=end.page[1],
        star=spec.kind,
        lines=spec.lines,
        size=reference_size(scene.sheet, scene.profile, lines=spec.lines, digits=digits),
        partner=partner.ref.port,
        partner_set=partner.page[0],
        partner_page=partner.page[1],
        leave=leave,
        partner_leave=partner_leave,
    )
