"""The orders of the conventions: the chain tie rules (T4) and the band lookup (T5).

`CHAIN_TIES` is a rank-key order over the two directions of a direction-free chain: the first
criterion that separates them decides, and a full tie keeps the walk's direction. `BANDS` is a
first-match table over a cell's place in its column: the suffix of its band key, `""` for none.
"""

from .rows import Criterion, Order, Row, Table, any_, not_

CHAIN_TIES = Order(
    "chain tie rules",
    (
        Criterion("D1vote", "strip_entry_outvoted", prefer=False),
        Criterion("C20", "potential_below_top", prefer=False),
        Criterion("A6", "designation_after", prefer=False),
    ),
)

BANDS = Table(
    "band lookup",
    "first match",
    (
        Row("T5.1", "first_in_row", ".first"),
        Row("T5.2", "last_in_row", ".last"),
        Row("T5.3", not_(any_("first_in_row", "last_in_row")), ""),
    ),
)
