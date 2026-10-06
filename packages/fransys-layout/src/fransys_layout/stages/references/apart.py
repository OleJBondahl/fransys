"""S21: a wired conductor whose two ends stand apart in another drawing set.

`links` cuts a conductor only when its ends share no page anywhere; one whose ends share a page
is wired there, once (`onepage`). A drawing set that seats both ends too, but on no common page,
then shows no wire at either, and the member check (layout-0071) wants each end drawn in every
set it stands in. There the pair is a `#n` reference (D4): one text at each end naming the
other, in the persisted shape of a C17 split (`"branch"` kind, mutual partners, no hub), so no
cut decision answers it and the wire stays the conductor's one drawing.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Sequence

from fransys_layout.stages.types import MarkerSide

from .cuts import link_world
from .markers import decided
from .nets import shown
from .types import Leave, MarkerSpec, PortEnd

if TYPE_CHECKING:
    from fransys_layout.stages.types import Connection
    from fransys_model.kernel import Id

    from .types import MarkerDecision, MarkerScene, Page, Star


def apart_markers(
    connections: tuple[Connection, ...],
    scene: MarkerScene,
    exempt: frozenset[tuple[Id[Any], int]],
    stars: tuple[Star, ...],
) -> tuple[MarkerDecision, ...]:
    """S21: each wired conductor's `#n` reference in every set that seats its ends apart."""
    world = link_world(scene)
    starred = {handle for star in stars for handle in star.wires}
    found = []
    for conductor in connections:
        pages_a = world.where.get(conductor.a.function, {})
        pages_b = world.where.get(conductor.b.function, {})
        if conductor.handle in starred or not pages_a.keys() & pages_b.keys():
            continue
        shown_a, shown_b = shown(world, conductor.a, exempt), shown(world, conductor.b, exempt)
        for page_a, page_b in _apart(shown_a, shown_b):
            owner, user = sorted(
                (PortEnd(ref=conductor.a, page=page_a), PortEnd(ref=conductor.b, page=page_b)),
                key=lambda end: end.page,
            )
            for end, partner, side in (
                (owner, user, MarkerSide.OWNER),
                (user, owner, MarkerSide.USER),
            ):
                spec = MarkerSpec(
                    conductor.handle,
                    (end, Leave.PORT),
                    (partner, Leave.PORT),
                    1,
                    kind="branch",
                    side=side,
                )
                found.append(decided(spec, scene))
    return tuple(found)


def _apart(pages_a: Sequence[Page], pages_b: Sequence[Page]) -> list[tuple[Page, Page]]:
    """Each drawing set holding both ends on no common page: the first page of each there."""
    by_set: dict[int, tuple[list[Page], list[Page]]] = defaultdict(lambda: ([], []))
    for page in pages_a:
        by_set[page[0]][0].append(page)
    for page in pages_b:
        by_set[page[0]][1].append(page)
    return [
        (min(in_a), min(in_b))
        for _, (in_a, in_b) in sorted(by_set.items())
        if in_a and in_b and not set(in_a) & set(in_b)
    ]
