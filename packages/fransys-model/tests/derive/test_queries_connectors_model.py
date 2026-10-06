"""Tests for `connector_rows` and `function_designation` (design/vocabulary.md 6 and
design/derive-queries-structure.md)."""

import pytest
from connector_builders import make_connector
from plant import Plant
from query_builders import make_footprint, make_node, make_placement, reversed_tables

from fransys_model.derive import (
    board_netlist,
    connector_rows,
    function_designation,
    port_designation,
)
from fransys_model.kernel import Id, Model, SchemaError, make_id
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind, Gender

_MARKINGS = ("10", "2", "A1", "1", "B2")


class _Design:
    """Board `JB1` with connector `J1` and a child `X1` with connector `J2`; housing `H1`."""

    def __init__(self) -> None:
        self.plant = Plant()
        self.board = self.plant.item("jb1", designation="JB1")
        self.j1, self.j1_ports = make_connector(self.plant, ("jb1", "J1"), _MARKINGS)
        self.plant.item("x1", parent=self.board, designation="X1")
        self.j2, self.j2_ports = make_connector(
            self.plant, ("x1", "J2"), ("1", "2"), gender=Gender.FEMALE
        )
        self.plant.item("h1", designation="H1")
        self.p1, self.p1_ports = make_connector(
            self.plant, ("h1", "P1"), ("1", "2", "10", "A1", "Z9"), gender=Gender.FEMALE
        )

    def model(self) -> Model:
        return self.plant.model()


def test_a_connector_of_the_board_and_one_of_a_child_are_both_listed_by_designation() -> None:
    """`JB1` (the board's own) and `X1` (on a child item) come out sorted by designation."""
    design = _Design()
    rows = connector_rows(design.model(), design.board)
    assert [(row.designation, row.connector) for row in rows] == [
        ("-JB1", design.j1),
        ("-X1", design.j2),
    ]


def test_a_connector_on_its_own_item_shows_that_items_designation_not_the_function_key() -> None:
    """A connector modeled as its own item (as a real part's `class_code` numbers it): the
    row's designation, and its mate's, are that item's own -- never the connector function's
    internal template key. A real part names its one function `"x1"`, never a reference
    designator (RULING C1, decision model-0049)."""
    plant = Plant()
    board = plant.item("u2", designation="U2")
    plant.item("j1item", parent=board, designation="J1")
    plant.item("j2item", parent=board, designation="J2")
    conn_a, _ = make_connector(plant, ("j1item", "x"), ("1",))
    conn_b, _ = make_connector(plant, ("j2item", "x"), ("1",))
    plant.mate(conn_a, conn_b)
    rows = connector_rows(plant.model(), board)
    row_a = next(row for row in rows if row.connector == conn_a)
    assert row_a.designation == "-J1"
    assert row_a.mate_designation == "-J2"


def test_two_connector_functions_on_one_item_keep_the_function_name_to_tell_them_apart() -> None:
    """A board-edge connector, a bare `Function` of the board item with no item of its own
    (DESIGN 503): with only one such function on `JB1` it would print `JB1` bare (as
    `test_a_connector_of_the_board_and_one_of_a_child_are_both_listed_by_designation` shows),
    but two on the same item would collide there, so both read as sub-parts,
    `<item>-<function name>` -- the function's own name is what tells them apart (decision
    model-0071, which replaced model-0049's `<item>:<function name>`)."""
    plant = Plant()
    board = plant.item("jb1", designation="JB1")
    make_connector(plant, ("jb1", "J1"), ("1",))
    make_connector(plant, ("jb1", "J3"), ("1",))
    rows = connector_rows(plant.model(), board)
    assert [row.designation for row in rows] == ["-JB1-J1", "-JB1-J3"]


def test_mate_designation_follows_the_same_per_item_function_count_rule() -> None:
    """The mate's own item is counted the same way, whichever board's rows are asked for."""
    plant = Plant()
    board = plant.item("jb1", designation="JB1")
    j1, _ = make_connector(plant, ("jb1", "J1"), ("1",))
    make_connector(plant, ("jb1", "J3"), ("1",))
    housing = plant.item("h1", designation="H1")
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",))
    plant.mate(j1, p1)
    model = plant.model()
    (j1_row,) = [row for row in connector_rows(model, board) if row.connector == j1]
    assert j1_row.mate_designation == "-H1"
    (p1_row,) = connector_rows(model, housing)
    assert p1_row.mate_designation == "-JB1-J1"


def test_a_row_projects_the_connector_facet() -> None:
    """Style, pin count and gender come from the facet of the function's template."""
    design = _Design()
    j1, j2 = connector_rows(design.model(), design.board)
    assert (j1.style, j1.pincount, j1.gender) == ("header", 5, Gender.MALE)
    assert (j2.style, j2.pincount, j2.gender) == ("header", 2, Gender.FEMALE)


def test_pins_sort_digit_markings_by_value_then_the_rest_by_string() -> None:
    """`1, 2, 10, A1, B2`, not the string order `1, 10, 2, A1, B2`."""
    design = _Design()
    (j1, _) = connector_rows(design.model(), design.board)
    assert [pin.marking for pin in j1.pins] == ["1", "2", "10", "A1", "B2"]
    assert sorted(_MARKINGS) == ["1", "10", "2", "A1", "B2"]


def test_equal_values_of_two_markings_fall_back_to_the_string_then_the_port() -> None:
    """`01` and `1` are one value, so the string decides; two ports of one name, the port id."""
    plant = Plant()
    board = plant.item("jb1", designation="JB1")
    _, ports = make_connector(plant, ("jb1", "J1"), ("1", "01"))
    twin = plant.port(make_id(Function, ("jb1", "J1")), "1", again="-twin")
    (row,) = connector_rows(plant.model(), board)
    assert [(pin.marking, pin.port) for pin in row.pins] == [
        ("01", ports["01"]),
        *sorted([("1", ports["1"]), ("1", twin)]),
    ]


def test_a_mate_pairs_pins_by_equal_port_name() -> None:
    """`J1` mated with `P1`: pins `1`, `2`, `10`, `A1` meet, `B2` has no partner."""
    design = _Design()
    design.plant.mate(design.j1, design.p1)
    model = design.model()
    j1, _ = connector_rows(model, design.board)
    assert (j1.mate, j1.mate_designation) == (design.p1, "-H1")
    assert [(pin.marking, pin.mate_port, pin.mate_port_designation) for pin in j1.pins] == [
        ("1", design.p1_ports["1"], "-H1:1"),
        ("2", design.p1_ports["2"], "-H1:2"),
        ("10", design.p1_ports["10"], "-H1:10"),
        ("A1", design.p1_ports["A1"], "-H1:A1"),
        ("B2", None, None),
    ]
    assert j1.pins[0].mate_port_designation == port_designation(model, design.p1_ports["1"])


def test_the_mate_is_found_whichever_end_the_connector_is() -> None:
    """A `Mate` stores its ends in id order, so the connector may be `a` or `b`."""
    for ends in ((0, 1), (1, 0)):
        design = _Design()
        pair = (design.j1, design.p1)
        design.plant.mate(pair[ends[0]], pair[ends[1]])
        j1, _ = connector_rows(design.model(), design.board)
        assert j1.mate == design.p1


def test_an_unmated_connector_has_no_mate_and_no_mate_ports() -> None:
    """`J2` is mated with nothing: `None` throughout."""
    design = _Design()
    design.plant.mate(design.j1, design.p1)
    _, j2 = connector_rows(design.model(), design.board)
    assert (j2.mate, j2.mate_designation) == (None, None)
    assert all((pin.mate_port, pin.mate_port_designation) == (None, None) for pin in j2.pins)


def test_a_connector_with_several_mates_takes_the_smallest_partner_id() -> None:
    """Two mates on `J1`: the partner with the smaller function id is `mate`."""
    design = _Design()
    design.plant.item("h2", designation="H2")
    other, _ = make_connector(design.plant, ("h2", "P1"), ("1",))
    design.plant.mate(design.j1, design.p1, key="m-1")
    design.plant.mate(design.j1, other, key="m-2")
    j1, _ = connector_rows(design.model(), design.board)
    assert j1.mate == min(design.p1, other)


def test_a_pin_carries_the_net_that_lists_it_named_as_board_netlist_names_it() -> None:
    """A named net, an unnamed one (its key) and one past the board; a pin in none has `None`."""
    design = _Design()
    plant = design.plant
    plant.net("v5", (design.j1_ports["1"], design.j2_ports["1"]), name="V5")
    plant.net("gnd", (design.j1_ports["2"], design.j2_ports["2"]))
    plant.net("harness", (design.j1_ports["10"], design.p1_ports["10"]), name="HARNESS")
    model = design.model()
    j1, j2 = connector_rows(model, design.board)
    assert [(pin.marking, pin.net) for pin in j1.pins] == [
        ("1", "V5"),
        ("2", "gnd"),
        ("10", "HARNESS"),
        ("A1", None),
        ("B2", None),
    ]
    assert [(pin.marking, pin.net) for pin in j2.pins] == [("1", "V5"), ("2", "gnd")]
    assert {net.name for net in board_netlist(model, design.board).nets} == {"V5", "gnd"}


def test_every_board_netlist_net_reappears_as_the_net_of_its_connector_pins() -> None:
    """The two queries name a net alike: each `board_netlist` name is on the pins it lists."""
    design = _Design()
    design.plant.net("v5", (design.j1_ports["1"], design.j2_ports["1"]), name="V5")
    design.plant.net("gnd", (design.j1_ports["2"], design.j2_ports["2"]))
    model = design.model()
    on_pin = {pin.port: pin.net for row in connector_rows(model, design.board) for pin in row.pins}
    for net in board_netlist(model, design.board).nets:
        assert {on_pin[port] for port in net.pins} == {net.name}


def test_a_pin_in_two_declared_nets_takes_the_smallest_name_then_net_id() -> None:
    """A port listed in two nets (a short) is named by the smaller `(name, net id)`."""
    design = _Design()
    pin = design.j1_ports["1"]
    design.plant.net("b-net", (pin, design.j2_ports["1"]), name="B")
    design.plant.net("a-net", (pin, design.j2_ports["2"]), name="A")
    j1, _ = connector_rows(design.model(), design.board)
    assert j1.pins[0].net == "A"


def test_functions_that_are_not_connectors_of_the_board_are_left_out() -> None:
    """No facet, another kind, or an item outside the board: none is a row, none is defaulted.

    `J3` has no facet, so it is no row, but it is still a connector function of `JB1`: the item
    has two, and `J1`'s row reads `-JB1-J1` (model-0071 counts by kind, as its pins print).
    """
    design = _Design()
    plant = design.plant
    make_connector(plant, ("jb1", "J3"), ("1",), gender=None)
    make_connector(plant, ("jb1", "K1"), ("1",), kind=FunctionKind.COIL)
    plant.item("far", designation="F1")
    make_connector(plant, ("far", "J1"), ("1",))
    rows = connector_rows(design.model(), design.board)
    assert [row.designation for row in rows] == ["-JB1-J1", "-X1"]


def test_a_board_with_no_connector_has_no_rows() -> None:
    """A board holding only components gives the empty tuple."""
    plant = Plant()
    board = plant.item("jb1", designation="JB1")
    plant.item("r1", parent=board, part=make_footprint(plant, "r", "R_0603"), designation="R1")
    assert connector_rows(plant.model(), board) == ()


def test_a_parent_cycle_through_the_board_does_not_hang() -> None:
    """The board and `x1` are each other's parent (a `CONTAINMENT_CYCLE`); the walk still ends."""
    plant = Plant()
    board = plant.item("jb1", parent=make_id(Item, ("x1",)), designation="JB1")
    plant.item("x1", parent=board, designation="X1")
    make_connector(plant, ("x1", "J1"), ("1",))
    make_connector(plant, ("jb1", "J2"), ("1",))
    assert [row.designation for row in connector_rows(plant.model(), board)] == ["-JB1", "-X1"]


def test_the_rows_do_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same rows."""
    design = _Design()
    design.plant.mate(design.j1, design.p1)
    design.plant.net("v5", (design.j1_ports["1"], design.j2_ports["1"]), name="V5")
    model = design.model()
    assert connector_rows(reversed_tables(model), design.board) == connector_rows(
        model, design.board
    )


def test_a_board_that_is_not_an_item_raises() -> None:
    """The refusal every query gives for an identity id the model does not hold."""
    design = _Design()
    with pytest.raises(SchemaError):
        connector_rows(design.model(), Id(kind="item", value="9" * 32))


def test_a_connector_whose_item_has_no_designation_raises() -> None:
    """A row that shows an unnumbered item raises, as every query that prints a designation."""
    plant = Plant()
    board = plant.item("jb1", designation=None)
    make_connector(plant, ("jb1", "J1"), ("1",))
    with pytest.raises(SchemaError):
        connector_rows(plant.model(), board)


def test_function_designation_renders_item_and_function_and_refuses_other_ids() -> None:
    """`JB1:J1`; an id that is not a function raises."""
    design = _Design()
    model = design.model()
    assert function_designation(model, design.j1) == "JB1:J1"
    with pytest.raises(SchemaError):
        function_designation(model, Id(kind="function", value="9" * 32))


def test_an_unknown_board_raises_a_schema_error_naming_the_bad_id() -> None:
    """The `require()` locator: `.kind` is `"item"`, `.record_id` is the id that was given."""
    design = _Design()
    bad = Id(kind="item", value="9" * 32)
    with pytest.raises(SchemaError) as excinfo:
        connector_rows(design.model(), bad)
    assert excinfo.value.kind == "item"
    assert excinfo.value.record_id == bad


def test_context_is_ignored_once_a_real_unit_is_given() -> None:
    """model-0056: a unit's own location stands in for whatever `context` the caller passes.

    `JB1` (unit `bu`) sits at `+C1`; its mate `H1` sits at `+EXT`, outside `+C1`. Passing
    `H1`'s own location as a distracting `context` would, if honoured, print the mate short
    (`-H1:1`); the unit's own location `C1` overrules it, so the mate still reads by its full
    path from `C1`, `+EXT-H1:1`.
    """
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    bu = plant.unit("bu", name="bu")
    board = plant.item("jb1", designation="JB1", unit=bu)
    housing = plant.item("h1", designation="H1")
    plant.add(
        make_placement("board-loc", board, c1.id),
        make_placement("housing-loc", housing, ext.id),
    )
    j1, _ = make_connector(plant, ("jb1", "J1"), ("1",))
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",), gender=Gender.FEMALE)
    plant.mate(j1, p1)
    model = plant.model()
    (row,) = connector_rows(model, board, unit=bu, context=ext.id)
    assert row.pins[0].mate_port_designation == "+EXT-H1:1"


def test_rows_sort_by_designation_then_by_connector_id_as_a_tiebreak() -> None:
    """Two connectors given out of designation order come back sorted; a tied designation
    text falls back to the connector id."""
    plant = Plant()
    board = plant.item("jb1", designation="JB1")
    plant.item("z9", parent=board, designation="Z9")
    plant.item("a1", parent=board, designation="A1")
    make_connector(plant, ("z9", "J1"), ("1",))
    make_connector(plant, ("a1", "J1"), ("1",))
    plant.item("t1", parent=board, designation="TIE")
    plant.item("t2", parent=board, designation="TIE")
    j_t1, _ = make_connector(plant, ("t1", "J1"), ("1",))
    j_t2, _ = make_connector(plant, ("t2", "J1"), ("1",))
    rows = connector_rows(plant.model(), board)
    assert [row.designation for row in rows] == ["-A1", "-TIE", "-TIE", "-Z9"]
    tied = [row.connector for row in rows if row.designation == "-TIE"]
    assert tied == sorted([j_t1, j_t2])


def test_a_mate_outside_a_nested_unit_blanks_its_text_but_keeps_the_ids() -> None:
    """units spec U2, model-0056: a nested unit's own reading blanks an outside mate's printed
    text (`mate_designation`, `mate_port_designation`), but `mate` and `mate_port` keep the
    ids so the row still says who it is."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    hu = plant.unit("hu", name="hu", parent=cabinet)
    board = plant.item("jb1", designation="JB1", unit=hu)
    j1, _ = make_connector(plant, ("jb1", "J1"), ("1",))
    plant.item("h1", designation="H1")
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",), gender=Gender.FEMALE)
    plant.mate(j1, p1)
    model = plant.model()
    (row,) = connector_rows(model, board, unit=hu)
    assert row.mate == p1
    assert row.mate_designation is None
    assert row.pins[0].mate_port is not None
    assert row.pins[0].mate_port_designation is None


def test_pins_sort_by_pin_order_numeric_markings_before_alpha() -> None:
    """`2, 10, A1`, not the string order `10, 2, A1` (`_pins`' sort key, via `connector_rows`)."""
    plant = Plant()
    board = plant.item("jb1", designation="JB1")
    make_connector(plant, ("jb1", "J1"), ("2", "10", "A1"))
    (row,) = connector_rows(plant.model(), board)
    assert [pin.marking for pin in row.pins] == ["2", "10", "A1"]
