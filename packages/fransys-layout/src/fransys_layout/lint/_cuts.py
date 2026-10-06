"""The cuts `links` should have decided and their markers, private to `coherence`.

Refs: package-layout.md 4, lint.md 6.8.

A conductor is cut only when its ends share no page, on the pages `cut_pages` names: that rule is
shared code from `stages`, called by `links` and here alike (decision layout-0078). The net-group
rule is restated on purpose, so the check does not trust the stage it checks: a net group is cut
between each consecutive pair of its pages, at its lowest-handle port on each (design/links.md 6.6).
"""

from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.stages import MarkerSide, cut_pages

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.geometry import Point
    from fransys_layout.stages import Connection, Handle, LinkMarker, NetGroup

    from ._ports import Page, Ports


@dataclass(frozen=True, slots=True)
class Cut:
    """One cut: its identity `(connection, a, b)`; the owner is the end on the earlier page."""

    connection: Handle
    a: Handle
    b: Handle
    owner: tuple[Handle, Page]
    user: tuple[Handle, Page]


def conductor_cut(
    conductor: Connection,
    ports: Ports,
    *,
    function_units: Mapping[Handle, Handle | None],
    set_units: Mapping[int, Handle | None],
) -> Cut | None:
    """The cut of a conductor whose ends are placed and share no page, else `None`."""
    pages_a = ports.pages.get(conductor.a.function, ())
    pages_b = ports.pages.get(conductor.b.function, ())
    if not pages_a or not pages_b or set(pages_a) & set(pages_b):
        return None
    page_a, page_b = cut_pages(
        pages_a,
        pages_b,
        own_units=(
            function_units.get(conductor.a.function),
            function_units.get(conductor.b.function),
        ),
        set_units=set_units,
    )
    owner, user = sorted(
        ((conductor.a.port, page_a), (conductor.b.port, page_b)), key=lambda end: end[1]
    )
    return Cut(
        connection=conductor.handle, a=conductor.a.port, b=conductor.b.port, owner=owner, user=user
    )


def group_cuts(group: NetGroup, ports: Ports) -> tuple[Cut, ...]:
    """The cuts between consecutive pages of a net group, each at its lowest port on the page."""
    lowest: dict[Page, Handle] = {}
    for ref in group.ports:
        for page in ports.pages.get(ref.function, ()):
            lowest.setdefault(page, ref.port)
    cuts = []
    for before, after in pairwise(sorted(lowest)):
        first, second = sorted((lowest[before], lowest[after]))
        cuts.append(
            Cut(
                connection=group.net,
                a=first,
                b=second,
                owner=(lowest[before], before),
                user=(lowest[after], after),
            )
        )
    return tuple(cuts)


def unpaired(
    cuts: tuple[Cut, ...],
    severed: frozenset[tuple[Handle, Handle, Handle]],
    markers: tuple[LinkMarker, ...],
    ports: Ports,
) -> list[tuple[Handle, ...]]:
    """The subjects of every `MARKER_UNPAIRED`."""
    cut_of: dict[tuple[Handle, Handle, MarkerSide, Page, int, int], Cut] = {}
    for cut in cuts:
        if (cut.connection, cut.a, cut.b) not in severed:
            continue
        for (port, page), side in ((cut.owner, MarkerSide.OWNER), (cut.user, MarkerSide.USER)):
            key = _key(cut.connection, port, side, page, ports.at[port, page])
            cut_of[key] = cut
    keys = [_marker_key(one) for one in markers]
    seen = Counter(keys)
    faults: list[tuple[Handle, ...]] = [
        (cut.connection, cut.a, cut.b) for key, cut in cut_of.items() if seen[key] != 1
    ]
    faults += [
        (one.connection, one.port)
        for one, key in zip(markers, keys, strict=True)
        if key not in cut_of
    ]
    return faults


def _key(
    connection: Handle, port: Handle, side: MarkerSide, page: Page, at: Point
) -> tuple[Handle, Handle, MarkerSide, Page, int, int]:
    """What identifies an expected marker: `(connection, port, side, page)` and where it stands."""
    return (connection, port, side, page, at.x, at.y)


def _marker_key(one: LinkMarker) -> tuple[Handle, Handle, MarkerSide, Page, int, int]:
    return _key(one.connection, one.port, one.side, (one.drawing_set, one.page), one.at)
