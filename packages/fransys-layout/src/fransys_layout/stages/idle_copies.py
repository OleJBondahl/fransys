"""A copy left with no wire on its page goes, once every wire of it is drawn elsewhere (0216).

The caller names the functions under the rule by their wires `(function, far function)`. A copy
on a page that holds none of its far ends goes when each of its wires has both ends on some
page of the same drawing set, so nothing still needs it there. A column left with no cell leaves
its page, a page left with no column leaves its set, and the set's later pages move up.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from fransys_layout.stages.types import Column, Handle, PagePlan
    from fransys_model.kernel import AuthoringKey

    type _Page = tuple[int, int]


def without_idle_copies(
    plans: tuple[PagePlan, ...],
    columns: tuple[Column, ...],
    links: Sequence[tuple[Handle, Handle]],
) -> tuple[tuple[PagePlan, ...], tuple[Column, ...]]:
    """`plans` and `columns` without the copies of `links`' functions no wire needs."""
    by_key = {column.key: column for column in columns}
    page_of = {
        planned.column: (plan.drawing_set, plan.number)
        for plan in plans
        for planned in plan.columns
    }
    seated: dict[_Page, set[Handle]] = {}
    for key, page in page_of.items():
        seated.setdefault(page, set()).update(cell.function for cell in by_key[key].cells)
    gone = _gone(seated, links, by_key, page_of)
    if not gone:
        return plans, columns
    kept = tuple(
        replace(
            column,
            cells=tuple(
                c for c in column.cells if (page_of.get(column.key), c.function) not in gone
            ),
        )
        for column in columns
    )
    left = {column.key for column in kept if column.cells}
    return _pruned(plans, left), tuple(column for column in kept if column.cells)


def _gone(
    seated: Mapping[_Page, AbstractSet[Handle]],
    links: Sequence[tuple[Handle, Handle]],
    by_key: Mapping[AuthoringKey, Column],
    page_of: Mapping[AuthoringKey, _Page],
) -> set[tuple[_Page, Handle]]:
    """The `(page, function)` copies with no far end on their page, every wire drawn in its set."""
    fars: dict[Handle, set[Handle]] = {}
    for own, far in links:
        fars.setdefault(own, set()).add(far)
    drawn = _drawn(seated, fars)
    hosting = {(page_of[key], c.host) for key in page_of for c in by_key[key].cells if c.host}
    return {
        (page, own)
        for page, here in seated.items()
        for own in here & fars.keys()
        if (page[0], own) in drawn and not fars[own] & here and (page, own) not in hosting
    }


def _drawn(
    seated: Mapping[_Page, AbstractSet[Handle]], fars: Mapping[Handle, AbstractSet[Handle]]
) -> set[tuple[int, Handle]]:
    """The `(set, function)` pairs whose every wire has both ends on one page of the set."""
    together = {
        (page[0], own, far)
        for page, here in seated.items()
        for own in here & fars.keys()
        for far in fars[own] & here
    }
    return {
        (drawing_set, own)
        for drawing_set in {page[0] for page in seated}
        for own, ends in fars.items()
        if all((drawing_set, own, far) in together for far in ends)
    }


def _pruned(plans: tuple[PagePlan, ...], left: AbstractSet[AuthoringKey]) -> tuple[PagePlan, ...]:
    """`plans` with only the columns in `left`; an emptied page goes and its set renumbers."""
    result: list[PagePlan] = []
    emptied: dict[int, int] = {}
    for plan in plans:
        kept = tuple(planned for planned in plan.columns if planned.column in left)
        if not kept:
            emptied[plan.drawing_set] = emptied.get(plan.drawing_set, 0) + 1
            continue
        moved = plan.number - emptied.get(plan.drawing_set, 0)
        result.append(replace(plan, columns=kept, number=moved))
    return tuple(result)
