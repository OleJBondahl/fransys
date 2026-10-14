"""LC1 (layout-0215): the keys of the parts of a column cut between its rows, and the cut itself.

A part is keyed by its column's key and its first row, and a part cut again counts from the
column. Two cells in two parts of one column stand across the cut.
"""

from dataclasses import replace

from samples import column

from fransys_layout.stages.row_parts import (
    base_of,
    row_part_key,
    row_parts,
    share_spacing,
)

KEY = ("invented", "tall")


def test_a_part_key_is_the_column_key_with_its_first_row() -> None:
    assert row_part_key(KEY, 7) == (*KEY, "row", "0007")


def test_a_part_of_a_part_counts_from_the_column() -> None:
    assert row_part_key(row_part_key(KEY, 7), 3) == row_part_key(KEY, 10)
    assert row_part_key(row_part_key(KEY, 7), 3) == (*KEY, "row", "0010")


def test_base_of_gives_the_column_and_its_first_row() -> None:
    assert base_of(KEY) == (KEY, 0)
    assert base_of(row_part_key(KEY, 7)) == (KEY, 7)


def test_row_parts_splits_the_rows_and_renumbers_each_part_from_zero() -> None:
    tall = column("tall", (1, 2, 3, 4, 5))
    tall = replace(
        tall, cells=tuple(replace(c, lane=c.index % 2, side=c.index == 4) for c in tall.cells)
    )
    first, second = row_parts(tall, [[0, 1, 2], [3, 4]])

    assert first.key == KEY
    assert second.key == row_part_key(KEY, 3)
    assert [(c.function, c.index) for c in first.cells] == [
        (c.function, c.index) for c in tall.cells[:3]
    ]
    assert second.cells == tuple(replace(c, index=i) for i, c in enumerate(tall.cells[3:]))
    assert [c.lane for c in second.cells] == [1, 0]
    assert second.cells[1].side is True
    assert (second.group, second.role, second.location) == (tall.group, tall.role, tall.location)


def test_the_parts_of_a_cut_column_share_the_narrowest_spacing_and_other_columns_keep_theirs() -> (
    None
):
    other = ("invented", "other")
    narrowed = {KEY: 40, row_part_key(KEY, 8): 42, other: 30}
    keys = [KEY, row_part_key(KEY, 8), row_part_key(KEY, 16), other]
    found = share_spacing(narrowed, keys, 88)
    assert [found[k] for k in keys[:3]] == [40, 40, 40]
    assert found[other] == 30
    assert share_spacing({}, keys, 88) == {}
