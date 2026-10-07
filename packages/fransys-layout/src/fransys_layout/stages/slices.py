"""Page slices (D10): which functions a page draws, and the items of a run that belong to it.

A page's data is taken from the plan's own columns, never by asking each item for "its" page: a
function drawn on two pages (a replica) is in both slices. Every slice is built once, in one pass
over the items, so a run over N pages does not scan the whole run N times.
"""

from operator import attrgetter, itemgetter
from typing import TYPE_CHECKING, Any

FUNCTION = attrgetter("function")  # the key of a spec or a drawn function into `by_page`

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from fransys_model.kernel import AuthoringKey

    from .types import (
        Column,
        Connection,
        Handle,
        LinkMarker,
        PagePlan,
        PlacedFunction,
        PlacedLabel,
        PlacedOutline,
        Route,
    )


def page_columns(
    plans: tuple[PagePlan, ...], columns: tuple[Column, ...]
) -> tuple[tuple[Column, ...], ...]:
    """Per plan, the columns its `plan.columns` name, in the plan's order (I4 D2)."""
    by_key = {column.key: column for column in columns}
    return tuple(
        tuple(by_key[one.column] for one in plan.columns if one.column in by_key) for plan in plans
    )


def pages_of(on_page: tuple[tuple[Column, ...], ...]) -> dict[Handle, tuple[int, ...]]:
    """Each function's page indices, ascending, from the cells of the columns of each page."""
    found: dict[Handle, list[int]] = {}
    for page, page_cols in enumerate(on_page):
        for column in page_cols:
            for cell in column.cells:
                pages = found.setdefault(cell.function, [])
                if not pages or pages[-1] != page:
                    pages.append(page)
    return {function: tuple(pages) for function, pages in found.items()}


def rooms_by_page(
    rooms: Mapping[tuple[Any, Any], tuple[int, int]], plans: tuple[PagePlan, ...]
) -> tuple[dict[tuple[AuthoringKey, Handle], tuple[int, int]], ...]:
    """Per plan, the entries of `rooms` (keyed `(column key, function)`) of the columns it names."""
    planned = by_key(
        ((one.column, page) for page, plan in enumerate(plans) for one in plan.columns),
        itemgetter(0),
    )
    entries = _per_page(
        ((page, (key, room)) for key, room in rooms.items() for _, page in planned.get(key[0], ())),
        len(plans),
    )
    return tuple(dict(found) for found in entries)


def by_page[T](
    items: Iterable[T],
    key: Callable[[T], Handle],
    pages: Mapping[Handle, tuple[int, ...]],
    count: int,
) -> tuple[tuple[T, ...], ...]:
    """One slice per page: the `items` whose `key` function is on that page, in their own order."""
    return _per_page(((page, item) for item in items for page in pages.get(key(item), ())), count)


def by_ends[T](
    items: Iterable[T],
    ends: Callable[[T], tuple[Handle, ...]],
    pages: Mapping[Handle, tuple[int, ...]],
    *,
    count: int,
    every: bool,
) -> tuple[tuple[T, ...], ...]:
    """One slice per page: the `items` whose `ends` stand on it (`every`: all, else any)."""
    return _per_page(
        ((page, item) for item in items for page in _pages_with(ends(item), pages, every=every)),
        count,
    )


def by_plan[T](
    items: Iterable[T], key: Callable[[T], tuple[int, int]], plans: tuple[PagePlan, ...]
) -> tuple[tuple[T, ...], ...]:
    """One slice per plan: the `items` whose `key` is `(drawing_set, page number)` of that plan."""
    grouped = by_key(items, key)
    return tuple(grouped.get((plan.drawing_set, plan.number), ()) for plan in plans)


def by_key[T, K](items: Iterable[T], key: Callable[[T], K]) -> dict[K, tuple[T, ...]]:
    """The one grouping: `items` by `key` in one pass, each in item order (layout-0086)."""
    grouped: dict[K, list[T]] = {}
    for item in items:
        grouped.setdefault(key(item), []).append(item)
    return {found: tuple(group) for found, group in grouped.items()}


def page_of(
    item: LinkMarker | Route | PlacedFunction | PlacedLabel | PlacedOutline,
) -> tuple[int, int]:
    """The `(drawing set, page number)` a placed thing is on."""
    return item.drawing_set, item.page


def connection_ends(conductor: Connection) -> tuple[Handle, Handle]:
    """The two functions a conductor joins."""
    return conductor.a.function, conductor.b.function


def _per_page[T](pairs: Iterable[tuple[int, T]], count: int) -> tuple[tuple[T, ...], ...]:
    """One tuple per page `0..count - 1` of the items paired with it, each in the pairs' order."""
    grouped = by_key(pairs, itemgetter(0))
    return tuple(tuple(item for _, item in grouped.get(page, ())) for page in range(count))


def _pages_with(
    functions: tuple[Handle, ...], pages: Mapping[Handle, tuple[int, ...]], *, every: bool
) -> list[int]:
    """The pages, ascending, that hold every one (or any one) of `functions`."""
    if not functions:
        return []
    found = [set(pages.get(function, ())) for function in functions]
    return sorted(set.intersection(*found) if every else set.union(*found))
