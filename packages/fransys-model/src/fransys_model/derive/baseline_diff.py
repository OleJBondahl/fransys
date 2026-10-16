"""`diff(a, b)`, composed from the per-section diffs."""

from fransys_model.kernel import SchemaError

from .baseline_ancestry import removed_ancestry
from .baseline_diff_keyed import keyed_pair, rename_to_b, renamed_first
from .baseline_diff_units import (
    _boundary_changes,
    _item_changes,
    _nested_unit_changes,
    _unit_changes,
    unit_subject_text,
)
from .baseline_diff_wiring import _conductor_changes, _mate_changes, _net_changes
from .rows_baseline import Change, Listing, ListingDiff


def diff(a: Listing, b: Listing) -> ListingDiff:
    """The change list from listing `a` (earlier) to `b` (later).

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
    a_unit, b_unit = a.unit, b.unit
    if a_unit.name != b_unit.name:
        msg = f"cannot diff listings of different units: {a_unit.name!r} and {b_unit.name!r}"
        raise SchemaError(msg, kind="listing")
    subject = unit_subject_text(b_unit)
    earlier, keyed = a, keyed_pair(a, b)
    renamed: list[Change] = []
    if keyed:
        a, renamed = rename_to_b(a, b, unit_subject_text(a_unit), subject)
    items = [
        *(r for r in renamed if r.section == "items"),
        *_item_changes(a.items, b.items, subject),
    ]
    boundary = [
        *(r for r in renamed if r.section == "boundary"),
        *_boundary_changes(a.boundary, b.boundary, subject),
    ]
    rows = (
        *_unit_changes(a_unit, b_unit),
        *sorted(items, key=renamed_first),
        *_nested_unit_changes(a.units, b.units),
        *sorted(boundary, key=renamed_first),
        *_conductor_changes(a.conductors, b.conductors, keyed=keyed),
        *_mate_changes(a.mates, b.mates, keyed=keyed),
        *_net_changes(a.nets, b.nets, keyed=keyed),
    )
    return ListingDiff(
        a=a_unit,
        b=b_unit,
        changes=rows,
        ancestry=removed_ancestry(earlier, rows, subject),
        keyed=keyed,
    )
