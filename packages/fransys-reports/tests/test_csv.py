import csv
import io
from decimal import Decimal
from typing import Any

import pytest
from fransys_reports import (
    bom_csv,
    cables_csv,
    connectors_csv,
    designations_csv,
    plc_csv,
    terminal_csv,
    wires_csv,
)

from fransys_model.derive import TOP_LEVEL, bom_lines, connector_rows, terminal_rows, wire_rows
from fransys_model.kernel import SchemaError, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Gender, PartCategory, SignalType
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part

# `cables_csv`'s row count for the two top-level cables `_two_cable_plant` builds.
CABLES_CSV_ROW_COUNT = 2


def _all_reports(model, strip):
    return (
        terminal_csv(model, strip),
        bom_csv(model),
        plc_csv(model),
        wires_csv(model),
        designations_csv(model),
    )


def test_two_calls_give_equal_text(cabinet, strip):
    assert _all_reports(cabinet, strip) == _all_reports(cabinet, strip)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_shuffled_draft_insertion_order_gives_equal_bytes(cabinet_plant, cabinet, strip, seed):
    shuffled = cabinet_plant.model(shuffled=seed)
    assert cabinet_plant.insertion_order(seed) != cabinet_plant.insertion_order()  # a real shuffle
    assert _all_reports(shuffled, strip) == _all_reports(cabinet, strip)


def test_a_different_model_gives_different_bytes(cabinet, cabinet_k3_installed, strip):
    assert _all_reports(cabinet_k3_installed, strip) != _all_reports(cabinet, strip)


def test_connectors_csv_is_deterministic(board_model, board):
    assert connectors_csv(board_model, board) == connectors_csv(board_model, board)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_connectors_csv_of_a_shuffled_draft_is_equal(board_draft, board, seed):
    assert board_draft.insertion_order(seed) != board_draft.insertion_order()  # a real shuffle
    shuffled = connectors_csv(board_draft.model(shuffled=seed), board)
    assert shuffled == connectors_csv(board_draft.model(), board)


def test_terminal_csv_header_is_side_a_and_side_b_and_a_jumper_partner_stays(cabinet, strip):
    """Owner ruling 2026-09-24 (item 4): the ends are `side_a`/`side_b`; rows are the derive
    rows as they were (L:1's jumper partner `-X1:L:2` stays: `jumper_group` names the bridge)."""
    lines = terminal_csv(cabinet, strip).splitlines()
    assert lines[0] == "designation,group,index,side_a,side_b,jumper_group"
    assert lines[1] == "-X1:L:1,L,1,-X1:L:2; -K1:1,-B1:1,1"


def test_terminal_and_bom_rows_keep_the_query_order(cabinet, strip):
    terminal_lines = terminal_csv(cabinet, strip).splitlines()[1:]
    assert [line.split(",")[0] for line in terminal_lines] == [
        row.designation for row in terminal_rows(cabinet, strip)
    ]
    bom_lines_text = list(csv.reader(io.StringIO(bom_csv(cabinet))))[1:]
    assert [line[0] for line in bom_lines_text] == [line.mpn for line in bom_lines(cabinet)]


def test_connector_lines_keep_the_query_row_order_and_pin_order(board_model, board):
    lines = list(csv.reader(io.StringIO(connectors_csv(board_model, board))))[1:]
    rows = connector_rows(board_model, board)
    assert [line[0] for line in lines] == [row.designation for row in rows for _ in row.pins]
    assert [line[5] for line in lines] == [pin.marking for row in rows for pin in row.pins]
    # the query's pin order is 1, 2, 10, A1 (numbers by value); a string sort gives 1, 10, 2, A1
    assert [line[5] for line in lines][:4] == ["1", "2", "10", "A1"]


def test_wire_rows_stay_in_the_order_the_query_gives_and_an_unlabelled_wire_has_one(cabinet):
    rows = list(csv.reader(io.StringIO(wires_csv(cabinet))))[1:]
    assert [row[0] for row in rows] == [
        "-X1:L:1",
        "-X1:L:1",
        "-X1:S:1",
    ]  # `from`, as the query sorts
    assert len(rows) == len(wire_rows(cabinet))  # the unlabelled wire is a row too


def test_text_has_no_byte_order_mark_and_only_lf_line_endings(cabinet, strip, board_model, board):
    for text in (*_all_reports(cabinet, strip), connectors_csv(board_model, board)):
        assert not text.startswith("\N{ZERO WIDTH NO-BREAK SPACE}")
        assert "\r" not in text
        assert text.endswith("\n")


def test_comma_quote_and_newline_in_a_description_are_quoted(new_plant):
    plant = new_plant()
    plant.item("a", "A1", description="one, two")
    plant.item("b", "A2", description='say "hi"')
    plant.item("c", "A3", description="line1\nline2")
    text = designations_csv(plant.model())
    assert text == (
        "designation,reference,description\n"
        '-A1,-A1,"one, two"\n'
        '-A2,-A2,"say ""hi"""\n'
        '-A3,-A3,"line1\nline2"\n'
    )
    parsed = list(csv.reader(io.StringIO(text, newline="")))
    assert [row[2] for row in parsed[1:]] == ["one, two", 'say "hi"', "line1\nline2"]


def test_comma_and_quote_in_a_connector_style_or_net_name_are_quoted(new_plant):
    plant = new_plant()
    board = plant.item("jb1", "JB1")
    _, ports = plant.connector(board, "J1", ("1",), style='2.54 mm, "vertical"')
    plant.net("filtered", (ports["1"],), name="+5 V, filtered")
    assert connectors_csv(plant.model(), board) == (
        "designation,style,pincount,gender,mate_designation,marking,net,mate_port_designation\n"
        '-JB1,"2.54 mm, ""vertical""",1,male,,1,"+5 V, filtered",\n'
    )


def test_a_plain_description_is_not_quoted(new_plant):
    plant = new_plant()
    plant.item("a", "A1", description="plain text")
    assert designations_csv(plant.model()).splitlines()[1] == "-A1,-A1,plain text"


def test_a_report_with_no_rows_is_the_header_row_only(new_plant):
    plant = new_plant()
    plant.item("x1", "X1")  # a strip with no terminal; no part, channel or wire either
    model = plant.model()
    strip = make_id(Item, ("x1",))
    assert terminal_csv(model, strip) == ("designation,group,index,side_a,side_b,jumper_group\n")
    # reports-0002: revision is bom.csv's second column, always present, empty on a part line
    assert bom_csv(model) == "mpn,revision,manufacturer,description,count,designations\n"
    assert plc_csv(model) == "channel_designation,signal,wired_to,signal_name\n"
    assert wires_csv(model) == "from,to,colour,cross_section_mm2,label\n"
    assert connectors_csv(model, strip) == _CONNECTORS_HEADER  # the item is no board with pins


_CONNECTORS_HEADER = (
    "designation,style,pincount,gender,mate_designation,marking,net,mate_port_designation\n"
)


def test_a_board_with_no_connector_or_only_pinless_ones_gives_the_header_row_only(new_plant):
    plant = new_plant()
    board = plant.item("jb1", "JB1")
    assert connectors_csv(plant.model(), board) == _CONNECTORS_HEADER
    plant.connector(board, "J1", (), pincount=4)  # a connector, but no pin declared
    assert connectors_csv(plant.model(), board) == _CONNECTORS_HEADER


def test_a_connector_with_no_gender_writes_an_empty_gender_cell(new_plant):
    """Decision model-0080: an unstated gender is a blank cell, not `None` or `neutral`."""
    plant = new_plant()
    board = plant.item("jb1", "JB1")
    plant.connector(board, "J1", ("1",), gender=None)
    assert connectors_csv(plant.model(), board) == _CONNECTORS_HEADER + "-JB1,header,1,,,1,,\n"


def test_a_board_with_a_pin_is_more_than_the_header_row(new_plant):
    plant = new_plant()
    board = plant.item("jb1", "JB1")
    plant.connector(board, "J1", ("1",))
    assert connectors_csv(plant.model(), board) == _CONNECTORS_HEADER + "-JB1,header,1,male,,1,,\n"


def test_the_designation_list_of_an_empty_model_is_the_header_row_only(new_plant):
    assert designations_csv(new_plant().model()) == "designation,reference,description\n"


def test_a_report_with_a_row_is_more_than_the_header_row(new_plant):
    plant = new_plant()
    plant.item("x1", "X1")
    assert (
        designations_csv(plant.model()) == "designation,reference,description\n-X1,-X1,Invented\n"
    )


def test_terminal_csv_of_an_unknown_strip_raises(cabinet):
    with pytest.raises(SchemaError):
        terminal_csv(cabinet, make_id(Item, ("no-such-strip",)))


def test_connectors_csv_of_an_unknown_board_raises(board_model):
    with pytest.raises(SchemaError):
        connectors_csv(board_model, make_id(Item, ("no-such-board",)))


def _scoped_plant(new_plant):
    """Panel `A9` holds relay `K1`, which is placed at `+C1`; relay `K2` is in neither."""
    plant = new_plant()
    panel = plant.item("panel", "A9")
    relay = plant.part("relay", "R-1")
    inside = plant.item("inside", "K1", part=relay, parent=panel)
    plant.item("outside", "K2", part=relay)
    node = plant.location("c1", "C1")
    plant.place(inside, node)
    return plant, panel, node


def test_bom_scope_restricts_to_items_under_an_item(new_plant):
    plant, panel, _ = _scoped_plant(new_plant)
    model = plant.model()
    assert bom_csv(model, scope=panel).splitlines()[1] == "R-1,,Example Co,Invented,1,-K1"
    assert bom_csv(model).splitlines()[1] == "R-1,,Example Co,Invented,2,-K1; -K2"  # without: both


def test_bom_scope_restricts_to_items_at_a_location_node(new_plant):
    plant, _, node = _scoped_plant(new_plant)
    model = plant.model()
    assert bom_csv(model, scope=node).splitlines()[1] == "R-1,,Example Co,Invented,1,-K1"
    assert "K2" in bom_csv(model)  # the whole model still counts it


def test_bom_scope_with_no_installed_part_in_it_is_the_header_row_only(new_plant):
    plant, _, _ = _scoped_plant(new_plant)
    empty = plant.item("empty", "A8")
    assert bom_csv(plant.model(), scope=empty) == (
        "mpn,revision,manufacturer,description,count,designations\n"
    )


def test_a_bom_scope_that_is_no_item_or_location_node_of_the_model_raises(new_plant):
    plant, _, _ = _scoped_plant(new_plant)
    model = plant.model()
    wrong: list[Any] = [make_id(Item, ("no-such-item",)), make_id(Part, ("relay",))]
    for scope in wrong:
        with pytest.raises(SchemaError):
            bom_csv(model, scope=scope)


# -- units spec U6: the unit= keyword filters, a pure pass-through to the model's own query --


def test_plc_csv_unit_filters_to_that_units_own_channels(new_plant):
    plant = new_plant()
    unit_a = plant.unit("ua", "unit-a")
    unit_b = plant.unit("ub", "unit-b")
    plant.channels("moda", "A1", (SignalType.DI,), unit=unit_a)
    plant.channels("modb", "B1", (SignalType.DI,), unit=unit_b)
    text = plc_csv(plant.model(), unit=unit_a)
    assert "A1:1" in text
    assert "B1:1" not in text


def test_wires_csv_unit_filters_to_that_units_own_conductor(new_plant):
    plant = new_plant()
    unit_a = plant.unit("ua", "unit-a")
    unit_b = plant.unit("ub", "unit-b")
    a1 = plant.pin("a1", "A1", unit=unit_a)
    a2 = plant.pin("a2", "A2", unit=unit_a)
    b1 = plant.pin("b1", "B1", unit=unit_b)
    b2 = plant.pin("b2", "B2", unit=unit_b)
    plant.label(plant.wire(a1, a2, "wa"), "WA")
    plant.label(plant.wire(b1, b2, "wb"), "WB")
    text = wires_csv(plant.model(), unit=unit_a)
    assert "A1:1" in text
    assert "B1:1" not in text


def test_designations_csv_unit_filters_to_that_units_own_items(new_plant):
    plant = new_plant()
    unit_a = plant.unit("ua", "unit-a")
    unit_b = plant.unit("ub", "unit-b")
    plant.item("a1", "A1", unit=unit_a)
    # A second root: a unit's sole root has no designation row (UNIT-ID I4), which is not
    # what this test is about.
    plant.item("a2", "A2", unit=unit_a)
    plant.item("b1", "B1", unit=unit_b)
    text = designations_csv(plant.model(), unit=unit_a)
    assert "A1" in text
    assert "B1" not in text


def test_terminal_csv_unit_changes_a_far_ends_printed_text(new_plant):
    """`terminal_csv` really passes `unit=` through to `terminal_rows` (model-0056): with the
    unit given, its own location becomes the print context, so a far end placed there prints
    short (the far end is in the unit); with no unit, `None` forces every located end to print
    its full path instead."""
    plant = new_plant()
    unit = plant.unit("u", "unit")
    strip = plant.item("strip", "X1", unit=unit)
    _internal, external = plant.terminal(strip, "L", 1)
    c1 = plant.location("c1", "C1")
    plant.place(strip, c1)
    far = plant.pin("far", "B1", unit=unit)
    plant.place(make_id(Item, ("far",)), c1)
    plant.wire(external, far, "w1")
    model = plant.model()
    assert terminal_csv(model, strip, unit=unit) != terminal_csv(model, strip, unit=None)


def test_connectors_csv_unit_changes_a_mates_printed_text(new_plant):
    """`connectors_csv` really passes `unit=` through to `connector_rows` (model-0056): with the
    unit given, its own location becomes the print context, so a mate placed there prints
    short; with no unit, `None` forces every located mate to print its full path instead."""
    plant = new_plant()
    unit = plant.unit("u", "unit")
    board = plant.item("board", "JB1", unit=unit)
    conn, _ = plant.connector(board, "J1", ("1",))
    c1 = plant.location("c1", "C1")
    plant.place(board, c1)
    far = plant.item("far", "H1")
    plant.place(far, c1)
    mate_conn, _ = plant.connector(far, "P1", ("1",), gender=Gender.FEMALE)
    plant.mate(conn, mate_conn)
    model = plant.model()
    assert connectors_csv(model, board, unit=unit) != connectors_csv(model, board, unit=None)


def test_unit_none_keeps_every_unit_scoped_reports_default_unchanged(new_plant):
    """`unit=None`'s default value is unchanged: a pure pass-through to the row query, whose
    own default is also `None` (model-0041) -- no behaviour to verify beyond that."""
    plant = new_plant()
    unit_a = plant.unit("ua", "unit-a")
    plant.channels("moda", "A1", (SignalType.DI,), unit=unit_a)
    a1 = plant.pin("a1", "A1", unit=unit_a)
    a2 = plant.pin("a2", "A2", unit=unit_a)
    plant.label(plant.wire(a1, a2, "wa"), "WA")
    model = plant.model()
    assert plc_csv(model) == plc_csv(model, unit=None)
    assert wires_csv(model) == wires_csv(model, unit=None)
    assert designations_csv(model) == designations_csv(model, unit=None)


# -- cables.csv (units spec U3, root decision 0016): no unit= -- cable_list_rows has none --


def _two_cable_plant(new_plant):
    """W1: a full-fact top-level cable, part, product facet, length and one end.

    W2: bare -- a cable `Part` carrying no product facts (`core_colours=()`), the minimum that
    still makes it a cable under `is_cable` (RW4b, model-0108: the part's `cable_product` facet
    alone, not the item's own installed-length `CableFacet`).
    """
    plant = new_plant()
    cable_part = plant.part(
        "cable-1", "CBL-4C15", description="4-core cable", category=PartCategory.CABLE
    )
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, ("cable-1", "product")),
            key=("cable-1", "product"),
            subject=cable_part,
            core_colours=("brown", "black", "grey", "blue"),
            gauge_mm2=Decimal("1.5"),
            shielded=False,
        )
    )
    cable_1 = plant.item("w1", "W1", part=cable_part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable_1,
            length_mm=15000,
        )
    )
    bare_part = plant.part("cable-2", "CBL-BARE", category=PartCategory.CABLE)
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, ("cable-2", "product")),
            key=("cable-2", "product"),
            subject=bare_part,
            core_colours=(),
            gauge_mm2=Decimal(0),
            shielded=False,
        )
    )
    cable_2 = plant.item("w2", "W2", part=bare_part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w2", "cable")),
            key=("w2", "cable"),
            subject=cable_2,
            length_mm=None,
        )
    )
    return plant


def test_cables_csv_header_and_a_full_row_match_exactly(new_plant):
    plant = _two_cable_plant(new_plant)
    lines = cables_csv(plant.model()).splitlines()
    assert lines[0] == (
        "designation,mpn,description,core_count,gauge_mm2,length_mm,from_label,to_label"
    )
    assert lines[1] == "-W1,CBL-4C15,4-core cable,4,1.5,15000,,"  # W1 sorts before W2
    assert len(lines) - 1 == CABLES_CSV_ROW_COUNT


def test_cables_csv_has_no_unit_parameter(new_plant):
    """`cables_csv` takes no `unit=`: `cable_list_rows` only ever returns `unit=None` cables."""
    plant = _two_cable_plant(new_plant)
    with pytest.raises(TypeError):
        cables_csv(plant.model(), unit=None)  # ty: ignore[unknown-argument] -- the removed `unit=` this test's `TypeError` confirms is gone at runtime too


def test_bom_csv_accepts_a_unit_scope_and_matches_bom_lines(new_plant):
    """`bom_csv`'s widened `scope` type (reports-0002): a unit `Id` doesn't raise, and the
    rows it writes are exactly `bom_lines(model, that_unit)`'s own, `bom_csv` already just
    forwards `scope` straight through."""
    plant = new_plant()
    unit_a = plant.unit("ua", "unit-a")
    relay = plant.part("relay", "R-1")
    plant.item("k1", "K1", part=relay, unit=unit_a)
    # A second root: a unit's sole root has an empty designations cell (UNIT-ID I4), which is
    # not what this test is about.
    plant.item("k2", "K2", part=relay, unit=unit_a)
    model = plant.model()
    expected = list(bom_lines(model, unit_a))
    assert len(expected) > 0
    lines = bom_csv(model, scope=unit_a).splitlines()[1:]
    assert len(lines) == len(expected)
    assert lines[0] == f"{expected[0].mpn},,{expected[0].manufacturer},Invented,2,-K1; -K2"


def test_bom_csv_writes_one_unit_row_per_release_of_a_board(new_plant):
    """FD acceptance 7b, csv half: one board at 1.1 and one at 2.1 are two rows, not one."""
    plant = new_plant()
    board = plant.part("board", "BOARD-1")
    for key, version in (("ub2", 2), ("ub1", 1)):
        unit = plant.unit(key, "demo-io-board", version=version)
        plant.item(f"{key}-item", "A1", part=board, unit=unit)
    rows = list(csv.DictReader(io.StringIO(bom_csv(plant.model(), scope=TOP_LEVEL))))
    unit_rows = [row for row in rows if row["mpn"] == "demo-io-board"]
    assert [(row["revision"], row["count"]) for row in unit_rows] == [("1.1", "1"), ("2.1", "1")]
