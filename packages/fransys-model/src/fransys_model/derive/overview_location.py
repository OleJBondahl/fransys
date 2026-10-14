"""The location fold of the system level (O9): boxes folded by the top node of the location aspect.

Each system box falls in the place at the top of its location tree; one line joins two places that
share cables. The fold exists only when the model has two or more top places. Reached as
`derive.location_fold`; `top_place_of` is the stub fold's rule too (model-0199).
"""

from typing import Any, cast

from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import aspect_nodes
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item

from .designation import location_node_designation, unit_location
from .lookups import effective_placement
from .order import natural_key
from .overview_levels import overview_level
from .rows_overview import LocationBox, LocationFold, LocationLine
lazy from .rows import OverviewLevel

__all__ = ["location_fold", "location_place_title", "top_place_of"]

_MIN_PLACES = 2


def _roots(model: Model) -> list[Id[AspectNode]]:
    """The location nodes with no parent."""
    return [
        n.id
        for n in aspect_nodes(model).values()
        if n.aspect is Aspect.LOCATION and n.parent is None
    ]


def _top(model: Model, node: Id[AspectNode] | None) -> Id[AspectNode] | None:
    """The root of the location tree holding `node`, `None` for no node."""
    nodes = aspect_nodes(model)
    while node is not None and nodes[node].parent is not None:
        node = cast("Id[AspectNode]", nodes[node].parent)
    return node


def top_place_of(model: Model, item: Id[Item]) -> Id[AspectNode] | None:
    """The top place of `item`'s location, `None` when it has none or the model has under two."""
    if len(_roots(model)) < _MIN_PLACES:
        return None
    return _top(model, effective_placement(model, item, Aspect.LOCATION))


def _box_place(model: Model, box: Id[Any]) -> Id[AspectNode] | None:
    """The top place of a system box: a unit's own location, else the item's."""
    if box.kind == "unit":
        return _top(model, unit_location(model, box))
    return _top(model, effective_placement(model, box, Aspect.LOCATION))


def _place_lines(model: Model, place: Id[AspectNode]) -> tuple[str, ...]:
    """A place's printed lines: its designation, then its description when it has one."""
    text = (location_node_designation(model, place), aspect_nodes(model)[place].description)
    return tuple(t for t in text if t)


def location_place_title(model: Model, place: Id[AspectNode]) -> str:
    """A place's printed title, its designation then its text on one line (`+ER Engine room`).

    The box prints these as two lines; the overview's panel prints the title. One spelling.
    """
    return " ".join(_place_lines(model, place))


def _place_box(model: Model, place: Id[AspectNode] | None, members: list[Id[Any]]) -> LocationBox:
    """One place as a box: its designation and description, or "No location"."""
    if place is None:
        return LocationBox(place=None, lines=("No location",), boxes=tuple(members))
    return LocationBox(place=place, lines=_place_lines(model, place), boxes=tuple(members))


def _lines(
    level: OverviewLevel, where: dict[Id[Any], Id[AspectNode] | None], rank: dict[Any, int]
) -> tuple[LocationLine, ...]:
    """One line per pair of places that share cables, with those cables."""
    pairs: dict[tuple[Any, Any], set[Id[Item]]] = {}
    for line in level.lines:
        a, b = sorted((where[line.ref.a], where[line.ref.b]), key=rank.__getitem__)
        if a != b and line.ref.via is not None:
            pairs.setdefault((a, b), set()).add(line.ref.via)
    return tuple(
        LocationLine(a=a, b=b, count=len(cables), cables=tuple(sorted(cables)))
        for (a, b), cables in sorted(pairs.items(), key=lambda kv: (rank[kv[0][0]], rank[kv[0][1]]))
    )


def location_fold(model: Model) -> LocationFold | None:
    """The system level folded by top place, or `None` when the model has under two top places.

    A box in no place stands in a "No location" box, last. A line joins two boxes with the number
    of distinct cables between their members; cables inside one place are no line.
    """
    if len(_roots(model)) < _MIN_PLACES:
        return None
    level = overview_level(model, None)
    where = {box.box: _box_place(model, box.box) for box in level.boxes}
    members: dict[Id[AspectNode] | None, list[Id[Any]]] = {}
    for box, place in where.items():
        members.setdefault(place, []).append(box)
    made = [_place_box(model, place, held) for place, held in members.items()]
    made.sort(key=lambda b: (b.place is None, tuple(natural_key(t) for t in b.lines)))
    rank = {box.place: at for at, box in enumerate(made)}
    return LocationFold(boxes=tuple(made), lines=_lines(level, where, rank))
