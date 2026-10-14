"""layout-0193: `in_key_order` gives each column the natural place of its key parts."""

from samples import column

from fransys_layout.engines.schematic.read.column_places import in_key_order
from fransys_layout.stages._ordering import column_order


def test_h10_sorts_after_h2_and_the_plain_key_would_not() -> None:
    h2, h10 = column("H2", (1,)), column("H10", (2,))
    assert h10.key < h2.key  # the plain text sort, the bug
    (placed,) = in_key_order((h10, h2))
    ordered = sorted(placed, key=column_order)
    assert [c.key[-1] for c in ordered] == ["H2", "H10"]
