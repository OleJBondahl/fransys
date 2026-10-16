from fransys_model.derive import board_pins


def _ref_pad(model, board, port):
    """`(ref, pad)` of `port` among the resolved pins, in nets or open."""
    pins = board_pins(model, board)
    (found,) = {
        (pin.ref, pin.pad)
        for pin in (*(p for net in pins.nets for p in net.pins), *pins.unconnected)
        if pin.port == port
    }
    return found


def test_a_component_pin_is_its_row_designation_and_port_name(demo_board):
    model = demo_board.freeze()
    board = demo_board.board.item
    assert _ref_pad(model, board, demo_board.resistor_1.pin("2")) == ("R1", "2")
    assert _ref_pad(model, board, demo_board.header.pin("4")) == ("J1", "4")


def test_a_pin_of_an_item_without_a_component_names_its_item(new_design):
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", {"edge": ("7",)}, board=True)
    board = design.item(board_part, "jb1", "JB1")
    design.net("n", (board.pin("7", "edge"),), name="N")
    model = design.freeze()
    assert _ref_pad(model, board.item, board.pin("7", "edge")) == ("JB1", "7")


def test_the_reference_is_never_taken_from_the_designation_text(new_design):
    design = new_design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", board=True)
    odd = design.part("odd", "SIM-ODD", "X", {"a": ("1:2",)}, footprint=("Lib", "X"))
    board = design.item(board_part, "jb1", "JB1")
    x1 = design.item(odd, "jb1-x1", "X:1.A", parent=board)
    model = design.freeze()
    assert _ref_pad(model, board.item, x1.pin("1:2", "a")) == ("X:1.A", "1:2")
