"""Rows an old rule governs that today's model cannot print: `leave_out` (LS3, model-0289).

A contact block numbered before 0.18.2 has no number now, so a listing cut under the old
holder rule marks each text it cannot build with `UNPRINTABLE`. Those fresh rows stand for the
stored rows they match; both leave the comparison and are counted, so the rest still compares.
"""

import dataclasses
import re

from .baseline_codec import without_parent
from .rows_baseline import Listing

UNPRINTABLE = "\x00"


def _holds(value: object) -> bool:
    """Whether `value`, a row or a part of one, holds a text that could not be printed."""
    if isinstance(value, str):
        return UNPRINTABLE in value
    if isinstance(value, tuple):
        return any(_holds(part) for part in value)
    if dataclasses.is_dataclass(value):
        return any(_holds(getattr(value, f.name)) for f in dataclasses.fields(value))
    return False


def _text_matches(pattern: str, stored: object) -> bool:
    if UNPRINTABLE not in pattern:
        return pattern == stored
    wild = ".+".join(re.escape(part) for part in pattern.split(UNPRINTABLE))
    return isinstance(stored, str) and re.fullmatch(wild, stored) is not None


def _tuple_matches(pattern: tuple[object, ...], stored: object) -> bool:
    if not isinstance(stored, tuple) or len(stored) != len(pattern):
        return False
    rest = list(stored)
    for part in sorted(pattern, key=_holds):
        found = next((i for i, s in enumerate(rest) if _matches(part, s)), None)
        if found is None:
            return False
        del rest[found]
    return True


def _matches(pattern: object, stored: object) -> bool:
    """Whether `stored` is what the fresh `pattern` stands for, `UNPRINTABLE` a wildcard."""
    if isinstance(pattern, str):
        return _text_matches(pattern, stored)
    if isinstance(pattern, tuple):
        return _tuple_matches(pattern, stored)
    if dataclasses.is_dataclass(pattern):
        return type(pattern) is type(stored) and all(
            _matches(getattr(pattern, f.name), getattr(stored, f.name))
            for f in dataclasses.fields(pattern)
        )
    return pattern == stored


def _section(
    stored: tuple[object, ...], fresh: tuple[object, ...]
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    wild = [row for row in fresh if _holds(row)]
    kept = tuple(row for row in stored if not any(_matches(w, row) for w in wild))
    return kept, tuple(row for row in fresh if not _holds(row))


def leave_out(stored: Listing, fresh: Listing) -> tuple[Listing, Listing, int]:
    """`stored` and `fresh` without the rows `fresh` could not print, and how many stored rows left.

    `parent` is dropped from both, as `differing_sections` does. With no `UNPRINTABLE` in `fresh`
    both come back unchanged and the count is `0`.
    """
    stored, fresh = without_parent(stored), without_parent(fresh)
    left = 0
    stored_rows: dict[str, tuple[object, ...]] = {}
    fresh_rows: dict[str, tuple[object, ...]] = {}
    for field in dataclasses.fields(Listing):
        rows = getattr(fresh, field.name)
        if not isinstance(rows, tuple):
            continue
        kept, shown = _section(getattr(stored, field.name), rows)
        left += len(getattr(stored, field.name)) - len(kept)
        stored_rows[field.name], fresh_rows[field.name] = kept, shown
    return (
        dataclasses.replace(stored, **stored_rows),
        dataclasses.replace(fresh, **fresh_rows),
        left,
    )
