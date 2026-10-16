"""The one order of a listing's item rows (model-0309): built rows and stored rows alike."""

lazy from .rows_baseline import BaselineItem


def num_key(value: int | None) -> tuple[bool, int]:
    """A None-safe sort key for an optional number."""
    return (value is None, value or 0)


def item_order(pair: tuple[BaselineItem, str]) -> tuple[object, ...]:
    """The sort key of an item row: its fields, then its unit-local key (model-0309).

    The key last makes a tie independent of the build path: alone or nested, the order is one.
    """
    r, key = pair
    return (
        r.designation,
        r.mpn,
        r.manufacturer,
        r.installed,
        r.external,
        num_key(r.position),
        key,
    )


def key_ordered(rows: tuple[BaselineItem, ...]) -> tuple[BaselineItem, ...]:
    """Keyed `rows` in `item_order`, so a stored tie compares whatever order it was stored in.

    Rows without a key (a version-1 listing) are returned as they are (model-0309).
    """
    if any(r.key is None for r in rows):
        return rows
    return tuple(r for r, _ in sorted(((r, str(r.key)) for r in rows), key=item_order))
