"""Layout-0211: where a boxed pin view's leads run to, the value its box's cells face."""

from typing import TYPE_CHECKING, Any

from .route import port_end

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from fransys_layout.geometry import Point
    from fransys_model.kernel import Id

    from .box_views import ViewKey
    from .types import Connection, DrawnFunction, PlacedFunction


def lead_ends(
    connections: Sequence[Connection],
    placed: Sequence[PlacedFunction],
    drawn: Sequence[DrawnFunction],
    views: Collection[Id[Any]],
) -> dict[ViewKey, tuple[Point, ...]]:
    """Each pin view of `views`, on each page, to the far ports of its conductors there.

    A conductor between two boxed pin views, or to a symbol on another page, leads nowhere.
    """
    at = {_key(one): one for one in placed}
    pages: dict[Id[Any], list[PlacedFunction]] = {}
    for one in placed:
        pages.setdefault(one.function, []).append(one)
    drawn_of = {one.function: one for one in drawn}
    found: dict[ViewKey, list[Point]] = {}
    for one in connections:
        for near, far in ((one.a, one.b), (one.b, one.a)):
            if near.function not in views or far.function in views:
                continue
            for view in pages.get(near.function, ()):
                there = at.get((far.function, view.drawing_set, view.page))
                if there is not None:
                    end = port_end(far, {far.function: there}, drawn_of)
                    found.setdefault(_key(view), []).append(end.at)
    return {key: tuple(points) for key, points in found.items()}


def _key(one: PlacedFunction) -> ViewKey:
    return (one.function, one.drawing_set, one.page)
