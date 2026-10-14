"""The geometry of a contact table, on plain values (model-0216, CR2)."""

from fransys_model.derive.contact_rows import column_split, heading_room, table_geometry


def test_a_lone_table_starts_at_its_columns_and_ends_one_pad_below_its_last_row() -> None:
    geo = table_geometry(3, 8, 2, headed=False)
    assert (geo.heading, geo.columns, geo.titles) == (0, 0, 2)
    assert (geo.rule, geo.first_row) == (10, 12)
    assert geo.height == 12 + 3 * 8 + 2


def test_a_headed_table_pushes_everything_below_its_heading_by_one_step() -> None:
    lone, headed = table_geometry(2, 8, 2, headed=False), table_geometry(2, 8, 2, headed=True)
    assert headed.heading == 0
    assert (headed.columns, headed.titles) == (8, 10)
    assert headed.rule == lone.rule + 8
    assert headed.first_row == lone.first_row + 8
    assert headed.height == lone.height + 8


def test_the_height_is_the_old_layout_sum_head_and_rows_plus_three_pads() -> None:
    for rows, step, pad in [(1, 8, 2), (5, 9, 3), (0, 7, 1)]:
        assert table_geometry(rows, step, pad, headed=False).height == (1 + rows) * step + 3 * pad


def test_the_heading_room_and_the_column_split() -> None:
    assert (heading_room(8, headed=True), heading_room(8, headed=False)) == (8, 0)
    assert (column_split(98), column_split(99)) == (49, 49)
