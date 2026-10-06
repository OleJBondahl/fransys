"""`diff(a, b)` (baseline spec M1), composed from the per-section diffs."""

from fransys_model.kernel import SchemaError

from .baseline_diff_units import (
    _boundary_changes,
    _item_changes,
    _nested_unit_changes,
    _unit_changes,
    unit_subject_text,
)
from .baseline_diff_wiring import _conductor_changes, _mate_changes, _net_changes
from .rows import (
    Change,
    Listing,
    ListingDiff,
)


def diff(a: Listing, b: Listing) -> ListingDiff:
    """The change list from listing `a` (earlier) to `b` (later) (baseline spec M1).

    One `Change` row per difference, in section, subject, field order. A moved identity is one
    removed and one added row; a nested unit compares only its release triple.

    Args:
        a: The earlier listing.
        b: The later listing.

    Returns:
        The `ListingDiff` of `a.unit` to `b.unit` with its `Change` rows.

    Raises:
        SchemaError: `a.unit.name != b.unit.name`; differing versions are what it diffs.
    """
    if a.unit.name != b.unit.name:
        msg = f"cannot diff listings of different units: {a.unit.name!r} and {b.unit.name!r}"
        raise SchemaError(msg, kind="listing")
    subject = unit_subject_text(b.unit)
    changes: list[Change] = [
        *_unit_changes(a.unit, b.unit),
        *_item_changes(a.items, b.items, subject),
        *_nested_unit_changes(a.units, b.units),
        *_boundary_changes(a.boundary, b.boundary, subject),
        *_conductor_changes(a.conductors, b.conductors),
        *_mate_changes(a.mates, b.mates),
        *_net_changes(a.nets, b.nets),
    ]
    return ListingDiff(a=a.unit, b=b.unit, changes=tuple(changes))
