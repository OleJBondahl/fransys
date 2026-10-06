import dataclasses
import uuid
from pathlib import Path

import pytest
from fransys_kicad import netlist

from fransys_model.derive import board_netlist
from fransys_model.derive.designation import own_designation_or_none
from fransys_model.kernel import SchemaError
from fransys_model.vocab.tables import functions, items, ports

GOLDEN = Path(__file__).resolve().parent / "golden" / "board.net"
GOLDEN_DNP = Path(__file__).resolve().parent / "golden" / "board_r2_dnp.net"


def _find(node, name):
    return [child for child in node if isinstance(child, list) and child[0] == name]


def _one(node, name):
    (found,) = _find(node, name)
    return found


def _comps(root):
    return _find(_one(root, "components"), "comp")


def _nets(root):
    return _find(_one(root, "nets"), "net")


def _nodes(net):
    return [(_one(node, "ref")[1], _one(node, "pin")[1]) for node in _find(net, "node")]


def _stamps(root):
    return {_one(comp, "ref")[1]: _one(comp, "tstamps")[1] for comp in _comps(root)}


def _pin_of(model, port):
    """The reference and pin `port` is expected to read as, straight from the tables."""
    record = ports(model)[port]
    item = items(model)[functions(model)[record.function].item]
    return own_designation_or_none(model, item), record.name


def test_header_and_sections(demo_board, sexpr):
    model = demo_board.freeze()
    root = sexpr(netlist(model, demo_board.board.item))
    assert root[0] == "export"
    assert [child[0] for child in root[1:]] == ["version", "design", "components", "nets"]
    assert _one(root, "version") == ["version", "E"]
    assert _one(root, "design") == ["design", ["source", "JB1"], ["tool", "fransys_kicad"]]


def test_components_match_the_rows(demo_board, sexpr):
    model = demo_board.freeze()
    rows = board_netlist(model, demo_board.board.item)
    comps = _comps(sexpr(netlist(model, demo_board.board.item)))
    assert [
        (_one(comp, "ref")[1], _one(comp, "value")[1], _one(comp, "footprint")[1]) for comp in comps
    ] == [
        (part.designation, part.mpn, f"{part.footprint_library}:{part.footprint_name}")
        for part in rows.parts
    ]
    assert [_one(comp, "ref")[1] for comp in comps] == ["J1", "R1", "R2"]
    assert all(
        _one(comp, "sheetpath") == ["sheetpath", ["names", "/"], ["tstamps", "/"]] for comp in comps
    )


def test_nets_match_the_rows(demo_board, sexpr):
    model = demo_board.freeze()
    rows = board_netlist(model, demo_board.board.item)
    nets = _nets(sexpr(netlist(model, demo_board.board.item)))
    assert [(_one(net, "code")[1], _one(net, "name")[1]) for net in nets] == [
        (str(code), net.name) for code, net in enumerate(rows.nets, start=1)
    ]
    assert [_nodes(net) for net in nets] == [
        [_pin_of(model, pin) for pin in net.pins] for net in rows.nets
    ]
    assert [_one(net, "name")[1] for net in nets] == ["GND", "SIG", "VCC"]


def test_golden_is_exact_bytes(demo_board):
    text = netlist(demo_board.freeze(), demo_board.board.item)
    assert GOLDEN.read_bytes() == text.encode("utf-8")
    assert b"\r" not in GOLDEN.read_bytes()
    assert text.endswith(")\n")


def _without_r2(demo_board, edit):
    """The demo board's model with `R2` not installed."""
    model = demo_board.freeze()
    r2 = items(model)[demo_board.resistor_2.item]
    return edit(model, dataclasses.replace(r2, installed=False))


def test_an_installed_part_carries_no_dnp_property(demo_board, sexpr):
    comps = _comps(sexpr(netlist(demo_board.freeze(), demo_board.board.item)))
    assert [_find(comp, "property") for comp in comps] == [[], [], []]


def test_a_part_not_installed_is_still_emitted_marked_dnp(demo_board, sexpr, edit):
    board = demo_board.board.item
    installed = sexpr(netlist(demo_board.freeze(), board))
    root = sexpr(netlist(_without_r2(demo_board, edit), board))
    comps = {_one(comp, "ref")[1]: comp for comp in _comps(root)}
    assert sorted(comps) == ["J1", "R1", "R2"]
    assert _find(comps["R2"], "property") == [["property", ["name", "dnp"]]]
    assert _find(comps["R1"], "property") == _find(comps["J1"], "property") == []
    assert [child[0] for child in comps["R2"][1:]] == [
        "ref",
        "value",
        "footprint",
        "property",
        "sheetpath",
        "tstamps",
    ]
    assert [_nodes(net) for net in _nets(root)] == [_nodes(net) for net in _nets(installed)]
    assert _stamps(root) == _stamps(installed)


def test_the_dnp_golden_is_exact_bytes(demo_board, edit):
    text = netlist(_without_r2(demo_board, edit), demo_board.board.item)
    assert GOLDEN_DNP.read_bytes() == text.encode("utf-8")
    assert text.count('(property (name "dnp"))') == 1


def test_tstamps_are_distinct_uuids(demo_board, sexpr):
    stamps = _stamps(sexpr(netlist(demo_board.freeze(), demo_board.board.item)))
    assert sorted(stamps) == ["J1", "R1", "R2"]
    assert len(set(stamps.values())) == 3
    assert all(str(uuid.UUID(stamp)) == stamp for stamp in stamps.values())


def test_tstamp_belongs_to_the_item_not_its_designation(demo_board, sexpr, edit):
    model = demo_board.freeze()
    board = demo_board.board.item
    before = _stamps(sexpr(netlist(model, board)))
    r1 = items(model)[demo_board.resistor_1.item]
    renumbered = edit(model, dataclasses.replace(r1, tag="R7"))
    after = _stamps(sexpr(netlist(renumbered, board)))
    assert after == {"J1": before["J1"], "R2": before["R2"], "R7": before["R1"]}


def test_tstamps_survive_a_new_part(demo_board, sexpr):
    before = _stamps(sexpr(netlist(demo_board.freeze(), demo_board.board.item)))
    demo_board.design.item(demo_board.resistor_part, "jb1-r3", "R3", parent=demo_board.board)
    after = _stamps(sexpr(netlist(demo_board.freeze(), demo_board.board.item)))
    assert after.pop("R3") not in before.values()
    assert after == before


def test_escaping_round_trips(new_design, sexpr):
    awkward_mpn = 'SIM "Q" \\ back é 日本\nnext line'
    awkward_pin = "1 A"
    awkward_net = 'N"1\\2 é'
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", board=True)
    part = design.part(
        "odd", awkward_mpn, "X", {"main": (awkward_pin, "2")}, footprint=("Lib \\ é", 'Name "x"')
    )
    board = design.item(board_part, "jb1", "JB1")
    odd = design.item(part, "jb1-x1", 'X "1" \\ é', parent=board)
    design.net("odd", (odd.pin(awkward_pin), odd.pin("2")), name=awkward_net)
    model = design.freeze()
    root = sexpr(netlist(model, board.item))
    (comp,) = _comps(root)
    assert _one(comp, "ref")[1] == 'X "1" \\ é'
    assert _one(comp, "value")[1] == awkward_mpn
    assert _one(comp, "footprint")[1] == 'Lib \\ é:Name "x"'
    (net,) = _nets(root)
    assert _one(net, "name")[1] == awkward_net
    assert sorted(_nodes(net)) == [('X "1" \\ é', awkward_pin), ('X "1" \\ é', "2")]
    assert 'N\\"1\\\\2' in netlist(model, board.item)
    assert "\\n" in netlist(model, board.item)


def test_same_model_gives_same_bytes(demo_board):
    model = demo_board.freeze()
    board = demo_board.board.item
    assert netlist(model, board) == netlist(model, board)


@pytest.mark.parametrize("seed", range(6))
def test_insertion_order_does_not_change_the_bytes(demo_board, seed):
    board = demo_board.board.item
    assert netlist(demo_board.freeze(seed), board) == netlist(demo_board.freeze(), board)


def test_an_empty_board_has_empty_sections(new_design, sexpr):
    design = new_design()
    board = design.item(design.part("board", "SIM-BOARD-DEMO", "A", board=True), "jb1", "JB1")
    text = netlist(design.freeze(), board.item)
    root = sexpr(text)
    assert _one(root, "components") == ["components"]
    assert _one(root, "nets") == ["nets"]
    assert text.endswith("  (components)\n  (nets))\n")


def test_a_pin_without_a_component_is_still_a_node(new_design, sexpr):
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", {"edge": ("1",)}, board=True)
    resistor = design.part("r", "SIM-R-0603", "R", {"main": ("1",)}, footprint=("Lib", "R"))
    board = design.item(board_part, "jb1", "JB1")
    r1 = design.item(resistor, "jb1-r1", "R1", parent=board)
    design.net("sig", (board.pin("1", "edge"), r1.pin("1")), name="SIG")
    root = sexpr(netlist(design.freeze(), board.item))
    assert [_one(comp, "ref")[1] for comp in _comps(root)] == ["R1"]
    (net,) = _nets(root)
    assert sorted(_nodes(net)) == [("JB1", "1"), ("R1", "1")]


def test_a_no_footprint_item_s_node_reads_the_board_relative_reference(new_design, sexpr):
    """The node for an item with no footprint names it board-relative (`U1`), not by its
    absolute designation (`JB1-U1`): `pin_of` must resolve it with `board`, not `None`.
    """
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", board=True)
    part = design.part("u", "SIM-U", "U", {"main": ("1",)})
    resistor = design.part("r", "SIM-R-0603", "R", {"main": ("1",)}, footprint=("Lib", "R"))
    board = design.item(board_part, "jb1", "JB1")
    u1 = design.item(part, "jb1-u1", "U1", parent=board)
    r1 = design.item(resistor, "jb1-r1", "R1", parent=board)
    design.net("sig", (u1.pin("1"), r1.pin("1")), name="SIG")
    (net,) = _nets(sexpr(netlist(design.freeze(), board.item)))
    assert sorted(_nodes(net)) == [("R1", "1"), ("U1", "1")]


def test_a_port_name_repeated_across_functions_stays_two_nodes(new_design, sexpr):
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", board=True)
    dual = design.part("dual", "SIM-DUAL", "U", {"a": ("1",), "b": ("1",)}, footprint=("Lib", "D"))
    board = design.item(board_part, "jb1", "JB1")
    u1 = design.item(dual, "jb1-u1", "U1", parent=board)
    design.net("one", (u1.pin("1", "a"),), name="ONE")
    design.net("two", (u1.pin("1", "b"),), name="TWO")
    nets = _nets(sexpr(netlist(design.freeze(), board.item)))
    assert [_nodes(net) for net in nets] == [[("U1", "1")], [("U1", "1")]]


def test_a_non_item_is_refused(demo_board):
    with pytest.raises(SchemaError):
        netlist(demo_board.freeze(), demo_board.header.pin("1"))
