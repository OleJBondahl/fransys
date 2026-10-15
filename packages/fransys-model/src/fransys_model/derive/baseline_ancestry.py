"""`removed_ancestry`: where each removed item of a diff sat in the earlier listing (RC3)."""

from typing import TYPE_CHECKING

from .rows_removed import RemovedAncestry

if TYPE_CHECKING:
    from .rows_baseline import BaselineItem, Change, Listing


def _chain(
    index: dict[str, BaselineItem], item: BaselineItem, own: str, unit: str
) -> tuple[str, ...]:
    """`item`'s parent subjects, nearest first, ending with the listed unit's `unit`."""
    found: list[str] = []
    seen = {own}
    row = item
    while row.parent is not None:
        subject = row.parent or unit
        if subject in seen or subject not in index:
            break
        found.append(subject)
        seen.add(subject)
        row = index[subject]
    return (*found, *(() if unit in seen else (unit,)))


def removed_ancestry(
    earlier: Listing, changes: tuple[Change, ...], unit: str
) -> tuple[RemovedAncestry, ...]:
    """One `RemovedAncestry` per removed `items` row; `unit` stands for a `""` designation."""
    index = {row.designation or unit: row for row in earlier.items}
    return tuple(
        RemovedAncestry(
            change=at, ancestors=_chain(index, index[change.subject], change.subject, unit)
        )
        for at, change in enumerate(changes)
        if change.section == "items" and change.change == "removed" and change.field == ""
    )
