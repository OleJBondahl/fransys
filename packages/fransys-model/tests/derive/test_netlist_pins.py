"""`board_pins` and `pin_text` (model-0275): a board's pins resolved once."""

from plant import Plant

from fransys_model.derive import board_netlist, board_pins, item_designation, pin_text
from fransys_model.kernel import make_id
from fransys_model.vocab.facets.pcb import FootprintFacet
from fransys_model.vocab.tables import ports


def _plant_board():
    plant = Plant()
    part = plant.part("U")
    key = ("footprint", *plant._key_of(part))
    plant.add(
        FootprintFacet(
            id=make_id(FootprintFacet, key), key=key, subject=part, library="Lib", name="U"
        )
    )
    board = plant.item("board", part=plant.board_part(), designation="A1")
    u1 = plant.item("u1", part=part, designation="U1", parent=board)
    u2 = plant.item("u2", part=part, designation="U2", parent=board)
    return plant, board, u1, u2


def test_the_nets_are_the_netlist_nets_with_every_pin_resolved() -> None:
    plant, board, u1, u2 = _plant_board()
    a1 = plant.port(plant.function(u1, "main"), "1")
    b1 = plant.port(plant.function(u2, "main"), "1")
    edge = plant.port(plant.function(board, "edge"), "7")
    plant.net("n", (a1, b1, edge), name="N")
    model = plant.model()
    rows = board_netlist(model, board)
    pins = board_pins(model, board)
    assert [(n.name, tuple(p.port for p in n.pins)) for n in pins.nets] == [
        (n.name, n.pins) for n in rows.nets
    ]
    for pin in (p for n in pins.nets for p in n.pins):
        assert pin.pad == ports(model)[pin.port].name
        assert pin.ref == item_designation(model, pin.item, relative_to=board)


def test_pin_text_is_the_reference_a_colon_and_the_pad() -> None:
    plant, board, u1, u2 = _plant_board()
    a1 = plant.port(plant.function(u1, "main"), "1")
    b2 = plant.port(plant.function(u2, "main"), "2")
    plant.net("n", (a1, b2), name="N")
    (net,) = board_pins(plant.model(), board).nets
    assert sorted(pin_text(p) for p in net.pins) == ["U1:1", "U2:2"]


def test_a_pin_of_a_part_in_no_net_is_unconnected_and_one_in_a_net_is_not() -> None:
    plant, board, u1, u2 = _plant_board()
    a1 = plant.port(plant.function(u1, "main"), "1")
    plant.port(plant.function(u1, "main"), "2")
    b1 = plant.port(plant.function(u2, "main"), "1")
    plant.net("n", (a1, b1), name="N")
    pins = board_pins(plant.model(), board)
    assert [(pin_text(p), p.item) for p in pins.unconnected] == [("U1:2", u1)]


def test_a_pin_of_an_item_without_a_part_row_takes_its_board_relative_designation() -> None:
    plant, board, u1, _ = _plant_board()
    a1 = plant.port(plant.function(u1, "main"), "1")
    edge = plant.port(plant.function(board, "edge"), "7")
    plant.net("n", (a1, edge), name="N")
    (net,) = board_pins(plant.model(), board).nets
    assert sorted(pin_text(p) for p in net.pins) == ["A1:7", "U1:1"]
