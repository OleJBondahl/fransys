import pytest
from fransys_kicad import check, netlist

from fransys_model.derive import board_netlist
from fransys_model.derive.designation import item_label
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import SchemaError, Severity
from fransys_model.vocab.tables import items
from fransys_model.vocab.validators.connectivity import NET_SHORTED, check_connectivity


def _codes(findings):
    return sorted(finding.code for finding in findings)


def _only(findings, code):
    (found,) = [finding for finding in findings if finding.code == code]
    return found


def _board_with(new_design, functions, footprint=None):
    """A board `JB1` and one part `U` with `functions`, so a test can wire it as it needs."""
    design = new_design()
    board = design.item(design.part("board", "SIM-BOARD-DEMO", "A", board=True), "jb1", "JB1")
    part = design.part("u", "SIM-U", "U", functions, footprint=footprint)
    return design, board, part


def test_the_demo_board_has_one_open_pin_and_one_part_without_a_footprint(demo_board):
    findings = check(demo_board.freeze(), demo_board.board.item)
    assert _codes(findings) == ["PART_WITHOUT_FOOTPRINT", "UNCONNECTED_PIN"]
    finding = _only(findings, "UNCONNECTED_PIN")
    assert finding.severity is Severity.INFO
    assert finding.subjects == (demo_board.header.pin("4"),)
    assert "J1:4" in finding.message


def test_check_is_sorted_and_ignores_insertion_order(demo_board):
    demo_board.design.net("lone", (demo_board.header.pin("4"),), name="LONE")
    demo_board.design.net("gnd2", (demo_board.resistor_2.pin("2"),), name="GND2")
    board = demo_board.board.item
    findings = check(demo_board.freeze(), board)
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    assert len(findings) > 1
    for seed in range(4):
        assert check(demo_board.freeze(seed), board) == findings


def test_an_unknown_board_is_refused_not_reported(demo_board):
    with pytest.raises(SchemaError):
        check(demo_board.freeze(), demo_board.header.pin("1"))


def test_a_net_with_one_pin(demo_board):
    demo_board.design.net("lone", (demo_board.header.pin("4"),), name="LONE")
    findings = check(demo_board.freeze(), demo_board.board.item)
    finding = _only(findings, "NET_SINGLE_PIN")
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (demo_board.header.pin("4"),)
    assert "LONE" in finding.message
    assert "J1:4" in finding.message
    assert "UNCONNECTED_PIN" not in _codes(findings)


def test_a_net_of_two_pins_is_not_single_pin(demo_board):
    assert "NET_SINGLE_PIN" not in _codes(check(demo_board.freeze(), demo_board.board.item))


def test_a_part_with_no_functions_and_a_function_with_no_ports_give_no_unconnected_pin(new_design):
    """Both `.get(..., ())` defaults in `_unconnected_pin`: `H1` has no function at all
    (a mounting-hole standoff), `E1` has one function with no ports at all. Both carry a
    footprint, or `board_netlist` would drop them from `rows.parts` before `_unconnected_pin`
    ever looks them up, and neither default would be reached.
    """
    design = new_design()
    board = design.item(design.part("board", "SIM-BOARD-DEMO", "A", board=True), "jb1", "JB1")
    standoff = design.part("standoff", "SIM-STANDOFF", "H", footprint=("MountingHole", "M3"))
    h1 = design.item(standoff, "jb1-h1", "H1", parent=board)
    empty = design.part("empty", "SIM-EMPTY", "E", {"main": ()}, footprint=("Lib", "E"))
    e1 = design.item(empty, "jb1-e1", "E1", parent=board)
    model = design.freeze()
    assert {part.item for part in board_netlist(model, board.item).parts} == {h1.item, e1.item}
    assert check(model, board.item) == ()


def test_a_pin_of_the_bare_board(new_design):
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", {"edge": ("1",)}, board=True)
    resistor = design.part("r", "SIM-R", "R", {"main": ("1",)}, footprint=("Lib", "R"))
    board = design.item(board_part, "jb1", "JB1")
    r1 = design.item(resistor, "jb1-r1", "R1", parent=board)
    design.net("sig", (board.pin("1", "edge"), r1.pin("1")), name="SIG")
    findings = check(design.freeze(), board.item)
    finding = _only(findings, "NODE_WITHOUT_COMPONENT")
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (board.pin("1", "edge"),)
    assert "child item" in finding.message
    assert "footprint" in finding.message


def test_a_pin_of_an_item_without_a_footprint(new_design):
    design, board, part = _board_with(new_design, {"main": ("1", "2")})
    resistor = design.part("r", "SIM-R", "R", {"main": ("1",)}, footprint=("Lib", "R"))
    u1 = design.item(part, "jb1-u1", "U1", parent=board)
    r1 = design.item(resistor, "jb1-r1", "R1", parent=board)
    design.net("sig", (u1.pin("1"), r1.pin("1")), name="SIG")
    findings = check(design.freeze(), board.item)
    finding = _only(findings, "NODE_WITHOUT_COMPONENT")
    assert finding.subjects == (u1.pin("1"),)
    assert "no footprint" in finding.message
    assert "child item" not in finding.message


def test_a_pin_without_a_footprint_names_the_item_board_relative(new_design):
    """The message names the no-footprint item's ref board-relative (`U1`), not by its
    absolute designation (`JB1-U1`): `pin_of` must resolve it with `board`, not `None`.
    """
    design, board, part = _board_with(new_design, {"main": ("1", "2")})
    resistor = design.part("r", "SIM-R", "R", {"main": ("1",)}, footprint=("Lib", "R"))
    u1 = design.item(part, "jb1-u1", "U1", parent=board)
    r1 = design.item(resistor, "jb1-r1", "R1", parent=board)
    design.net("sig", (u1.pin("1"), r1.pin("1")), name="SIG")
    findings = check(design.freeze(), board.item)
    finding = _only(findings, "NODE_WITHOUT_COMPONENT")
    assert finding.message == (
        "pin U1:1 belongs to an item with no footprint, so it has no component "
        "in the netlist and KiCad drops it on import"
    )


def test_pins_that_all_have_components_raise_no_node_finding(demo_board):
    assert "NODE_WITHOUT_COMPONENT" not in _codes(check(demo_board.freeze(), demo_board.board.item))


def test_two_parts_with_one_reference_even_under_different_parents(demo_board):
    other = demo_board.design.item(
        demo_board.resistor_part, "jb1-h1-r1", "R1", parent=demo_board.standoff
    )
    findings = check(demo_board.freeze(), demo_board.board.item)
    finding = _only(findings, "REFERENCE_DUPLICATE")
    assert finding.severity is Severity.ERROR
    assert set(finding.subjects) == {demo_board.resistor_1.item, other.item}
    assert "R1" in finding.message


def test_a_footprinted_link_under_a_footprinted_holder_is_no_duplicate_reference(new_design):
    """A footprinted fuse link under the tagged holder `F11` is its own board part: after
    numbering it has a reference of its own, so `check` finds no `REFERENCE_DUPLICATE`.

    Fails on the base: the link is an accessory and prints the holder's `F11`.
    """
    design = new_design()
    board = design.item(design.part("board", "SIM-BOARD-DEMO", "A", board=True), "jb1", "JB1")
    footprint = ("FuseLib", "Fuse_Holder")
    holder = design.item(
        design.part("h", "SIM-H", "H", footprint=footprint), "jb1-f11", "F11", parent=board
    )
    design.item(
        design.part("f", "SIM-F", "F", footprint=footprint), "jb1-link", None, parent=holder
    )
    model, _ = number(design.freeze())
    assert "REFERENCE_DUPLICATE" not in _codes(check(model, board.item))


def test_distinct_references_are_not_duplicates(demo_board):
    assert "REFERENCE_DUPLICATE" not in _codes(check(demo_board.freeze(), demo_board.board.item))


def test_two_nets_with_one_name(demo_board):
    demo_board.design.net("vcc-again", (demo_board.header.pin("4"),), name="VCC")
    findings = check(demo_board.freeze(), demo_board.board.item)
    finding = _only(findings, "NET_NAME_DUPLICATE")
    assert finding.severity is Severity.ERROR
    assert set(finding.subjects) == {
        demo_board.header.pin("1"),
        demo_board.resistor_1.pin("1"),
        demo_board.header.pin("4"),
    }
    assert "VCC" in finding.message


def test_distinct_net_names_are_not_duplicates(demo_board):
    assert "NET_NAME_DUPLICATE" not in _codes(check(demo_board.freeze(), demo_board.board.item))


def test_one_port_in_two_nets_no_longer_reaches_this_check(demo_board):
    """`board_netlist` now merges a group holding two declared nets' ports into one row,
    under the smaller net name (decision model-0042): a port in `GND` and `GND2` is one pad
    in one net row, not two, so `PAD_ON_MULTIPLE_NETS` does not fire. Proven positively, not
    by absence alone: the merged row still carries `R2:2` under the one name `GND`, and
    `NET_SHORTED`, the model's own validator, reports the same two nets over the same model
    (the package README: what the model's validators already report is not repeated
    here)."""
    demo_board.design.net("gnd2", (demo_board.resistor_2.pin("2"),), name="GND2")
    model = demo_board.freeze()
    board = demo_board.board.item

    findings = check(model, board)
    assert "PAD_ON_MULTIPLE_NETS" not in _codes(findings)

    rows = board_netlist(model, board)
    merged = [net for net in rows.nets if demo_board.resistor_2.pin("2") in net.pins]
    assert len(merged) == 1
    assert merged[0].name == "GND"
    assert set(merged[0].pins) == {demo_board.resistor_2.pin("2"), demo_board.header.pin("3")}

    shorted = [f for f in check_connectivity(model) if f.code == NET_SHORTED]
    assert len(shorted) == 1
    assert shorted[0].severity is Severity.ERROR


def test_two_ports_with_one_pad_name_in_two_nets_is_a_pad_on_two_nets(new_design):
    design, board, part = _board_with(
        new_design, {"a": ("1",), "b": ("1",)}, footprint=("Lib", "U")
    )
    u1 = design.item(part, "jb1-u1", "U1", parent=board)
    design.net("one", (u1.pin("1", "a"),), name="ONE")
    design.net("two", (u1.pin("1", "b"),), name="TWO")
    finding = _only(check(design.freeze(), board.item), "PAD_ON_MULTIPLE_NETS")
    assert set(finding.subjects) == {u1.pin("1", "a"), u1.pin("1", "b")}
    assert "U1:1" in finding.message
    assert finding.severity is Severity.ERROR


def test_two_ports_with_one_pad_name_in_one_net_is_one_pad(new_design):
    design, board, part = _board_with(
        new_design, {"a": ("1",), "b": ("1",)}, footprint=("Lib", "U")
    )
    u1 = design.item(part, "jb1-u1", "U1", parent=board)
    design.net("both", (u1.pin("1", "a"), u1.pin("1", "b")), name="BOTH")
    codes = _codes(check(design.freeze(), board.item))
    assert "PAD_ON_MULTIPLE_NETS" not in codes
    assert "UNCONNECTED_PIN" not in codes


def test_a_pin_in_no_net(demo_board):
    finding = _only(check(demo_board.freeze(), demo_board.board.item), "UNCONNECTED_PIN")
    assert finding.subjects == (demo_board.header.pin("4"),)


def test_a_pad_shared_by_two_ports_is_connected_when_one_is_in_a_net(new_design):
    design, board, part = _board_with(
        new_design, {"a": ("1",), "b": ("1",)}, footprint=("Lib", "U")
    )
    u1 = design.item(part, "jb1-u1", "U1", parent=board)
    design.net("one", (u1.pin("1", "a"),), name="ONE")
    assert "UNCONNECTED_PIN" not in _codes(check(design.freeze(), board.item))


def test_every_pin_in_a_net_is_not_unconnected(new_design):
    design, board, part = _board_with(new_design, {"main": ("1", "2")}, footprint=("Lib", "R"))
    r1 = design.item(part, "jb1-r1", "R1", parent=board)
    r2 = design.item(part, "jb1-r2", "R2", parent=board)
    design.net("a", (r1.pin("1"), r2.pin("1")), name="A")
    design.net("b", (r1.pin("2"), r2.pin("2")), name="B")
    assert check(design.freeze(), board.item) == ()


def test_a_part_without_a_footprint_is_omitted_and_reported(demo_board):
    model = demo_board.freeze()
    finding = _only(check(model, demo_board.board.item), "PART_WITHOUT_FOOTPRINT")
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (demo_board.standoff.item,)
    assert "H1" in finding.message
    assert '"H1"' not in netlist(model, demo_board.board.item)


def test_a_part_without_a_footprint_and_without_a_designation_is_named_by_its_key(new_design):
    design, board, part = _board_with(new_design, {"main": ("1",)})
    stray = design.item(part, "jb1-stray", None, parent=board)
    finding = _only(check(design.freeze(), board.item), "PART_WITHOUT_FOOTPRINT")
    assert finding.subjects == (stray.item,)
    assert "jb1-stray" in finding.message


def test_a_numbered_untagged_part_without_a_footprint_is_named_by_its_number(new_design):
    """An item authored with no tag is named by the number the numbering pass gave it, not by
    its key; the same item before numbering is named by its key."""
    design, board, part = _board_with(new_design, {"main": ("1",)})
    stray = design.item(part, "jb1-stray", None, parent=board)
    unnumbered = design.freeze()
    assert item_label(unnumbered, items(unnumbered)[stray.item]) == "jb1-stray"

    model, _ = number(unnumbered)
    assert item_label(model, items(model)[stray.item]) == "U1"
    finding = _only(check(model, board.item), "PART_WITHOUT_FOOTPRINT")
    assert finding.subjects == (stray.item,)
    assert finding.message == "part U1 has no footprint, so the netlist omits it"


def test_parts_that_all_have_footprints_raise_no_footprint_finding(new_design):
    design, board, part = _board_with(new_design, {"main": ("1", "2")}, footprint=("Lib", "R"))
    design.item(part, "jb1-r1", "R1", parent=board)
    assert "PART_WITHOUT_FOOTPRINT" not in _codes(check(design.freeze(), board.item))
