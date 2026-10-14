"""The key of a column part: its column key, a kind word and its first line (layout-0230).

The one scheme for the lane parts of `wide_columns` and the row parts of `row_parts`. The kind
word (`lane`, `row`) names the cut; a part cut again counts from its base column.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey


def base_and_first(key: AuthoringKey, kind: str) -> tuple[AuthoringKey, int]:
    """The key of the column a `kind` part was cut from, and the part's first line there."""
    if len(key) > 1 and key[-2] == kind and key[-1].isdigit():
        return key[:-2], int(key[-1])
    return key, 0


def part_key_of(key: AuthoringKey, kind: str, first: int) -> AuthoringKey:
    """The key of the `kind` part from line `first`; a part cut again counts from its base."""
    base, at = base_and_first(key, kind)
    return (*base, kind, f"{at + first:04d}")
