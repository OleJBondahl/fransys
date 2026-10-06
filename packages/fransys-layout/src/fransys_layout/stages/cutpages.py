"""Which pages a severed conductor's cut uses: one rule, read by `links` and the check.

Refs: links.md 6.6.

A cut belongs to the unit whose drawing draws the wire. A boundary function stands twice: at
home, in its own unit's drawing set, and as a black box in its parent's (units spec U1); the black
box draws the unit's interface, not its insides. So the earliest page of a function is not always
the page its wire is drawn on (decision layout-0078).
"""

from typing import TYPE_CHECKING
lazy from collections.abc import Sequence

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .types import Handle

# `(drawing_set, page)`: pages are ordered by this pair throughout the stage.
type Page = tuple[int, int]

# A unit's handle, `None` for the top level.
type Unit = Handle | None


def cut_pages(
    pages_a: Iterable[Page],
    pages_b: Iterable[Page],
    *,
    own_units: tuple[Unit, Unit],
    set_units: Mapping[int, Unit],
) -> tuple[Page, Page]:
    """The page of each end a conductor's cut stands on, the ends sharing none (layout-0078)."""
    ends_a, ends_b = sorted(pages_a), sorted(pages_b)
    unit_a, unit_b = own_units
    if unit_a == unit_b and (both := _earliest_in(ends_a, ends_b, unit_a, set_units)):
        return both
    seen: set[Unit] = set()
    for drawing_set in sorted(set_units):
        unit = set_units[drawing_set]
        if unit in seen:
            continue
        seen.add(unit)
        if both := _earliest_in(ends_a, ends_b, unit, set_units):
            return both
    return ends_a[0], ends_b[0]


def _earliest_in(
    pages_a: Sequence[Page], pages_b: Sequence[Page], unit: Unit, set_units: Mapping[int, Unit]
) -> tuple[Page, Page] | None:
    """Each end's earliest page in `unit`'s drawing sets, or `None` when an end has none there."""
    first_a = next((page for page in pages_a if set_units.get(page[0]) == unit), None)
    first_b = next((page for page in pages_b if set_units.get(page[0]) == unit), None)
    if first_a is None or first_b is None:
        return None
    return first_a, first_b
