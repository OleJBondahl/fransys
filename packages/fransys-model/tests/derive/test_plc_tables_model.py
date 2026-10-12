"""Tests: the PLC list is one table per controller or module, in the one derive order.

Invented racks: controller `-C1` has modules keyed against their rack order, `-C0` is keyed to
come last by key, and `-X9` sits in no rack (model-0194, L4).
"""

from collections import Counter

from rack_builders import build_racks

from fransys_model.derive import plc_channel_rows, plc_tables, printed_designation


def test_tables_run_controller_first_then_modules_in_rack_order() -> None:
    """A1: racks by designation, a controller's own table, its modules by position, loose last."""
    built = build_racks()
    tables = plc_tables(built.model)
    assert [table.item for table in tables] == [
        built.first_rack,
        built.first_rack_module,
        built.rack,
        *built.modules_in_rack_order,
        built.loose,
    ]
    assert [table.designation for table in tables] == [
        printed_designation(built.model, table.item) for table in tables
    ]


def test_a_module_without_channels_has_no_table() -> None:
    """L6: the coupler of the invented rack has no channel and no table."""
    built = build_racks()
    assert built.coupler not in [table.item for table in plc_tables(built.model)]


def test_channels_of_a_table_run_by_channel_number() -> None:
    """The rows of one table are ordered by channel number, not by creation order."""
    built = build_racks()
    module = next(t for t in plc_tables(built.model) if t.item == built.first_rack_module)
    assert [row.channel_designation.rsplit(":", 1)[1] for row in module.rows] == ["1", "2"]


def test_every_row_is_in_exactly_one_table_in_list_order() -> None:
    """A2: the rows of all tables are the rows of `plc_channel_rows`, once each and in order."""
    model = build_racks().model
    rows = plc_channel_rows(model)
    flat = tuple(row for table in plc_tables(model) for row in table.rows)
    assert flat == rows
    assert Counter(flat) == Counter(rows)
    assert len(rows) == 1 + 1 + 2 + 2 + 2 + 1
