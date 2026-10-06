from fransys_kicad._pins import pin_of

from fransys_model.derive import board_netlist


def _designations(model, board):
    return {part.item: part.designation for part in board_netlist(model, board).parts}


def test_a_component_pin_is_its_row_designation_and_port_name(demo_board):
    model = demo_board.freeze()
    designations = _designations(model, demo_board.board.item)
    board = demo_board.board.item
    assert pin_of(model, designations, demo_board.resistor_1.pin("2"), board) == ("R1", "2")
    assert pin_of(model, designations, demo_board.header.pin("4"), board) == ("J1", "4")


def test_a_pin_of_an_item_without_a_component_names_its_item(new_design):
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", {"edge": ("7",)}, board=True)
    board = design.item(board_part, "jb1", "JB1")
    model = design.freeze()
    assert pin_of(model, {}, board.pin("7", "edge"), board.item) == ("JB1", "7")


def test_the_reference_is_never_taken_from_the_designation_text(new_design):
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", board=True)
    odd = design.part("odd", "SIM-ODD", "X", {"a": ("1:2",)}, footprint=("Lib", "X"))
    board = design.item(board_part, "jb1", "JB1")
    x1 = design.item(odd, "jb1-x1", "X:1.A", parent=board)
    model = design.freeze()
    designations = _designations(model, board.item)
    assert pin_of(model, designations, x1.pin("1:2", "a"), board.item) == ("X:1.A", "1:2")
