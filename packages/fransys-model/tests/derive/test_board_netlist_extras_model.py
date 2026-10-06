"""Tests for `BoardNetlist.without_footprint` and `NetlistPart.installed`.

See design/derive-queries-structure.md.
"""

from plant import Plant
from query_builders import make_footprint, make_part, reversed_tables

from fransys_model.derive import board_netlist
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item


def _board() -> Plant:
    """`A1` holds `r1` (footprint), `j1` and a child `j2` under `sub` (parts without one)."""
    plant = Plant()
    board = plant.item("board", designation="A1", part=make_part(plant, "board", "BRD"))
    footprinted = make_footprint(plant, "r", "R_0603")
    bare = make_part(plant, "conn", "CONN")
    plant.item("r1", parent=board, part=footprinted, designation="R1")
    plant.item("j1", parent=board, part=bare, designation="J1")
    sub = plant.item("sub", parent=board, designation="S1")
    plant.item("j2", parent=sub, part=bare, designation="J2")
    plant.item("partless", parent=board, designation="P1")
    plant.item("outside", part=bare, designation="O1")
    return plant


def test_without_footprint_lists_the_descendants_whose_part_has_none_sorted_by_id() -> None:
    """A child and a grandchild count; a footprinted one, a part-less one, the board and a
    foreign item do not."""
    plant = _board()
    netlist = board_netlist(plant.model(), make_id(Item, ("board",)))
    assert netlist.without_footprint == tuple(sorted(make_id(Item, (key,)) for key in ("j1", "j2")))
    assert [part.designation for part in netlist.parts] == ["R1"]


def test_a_board_with_only_footprinted_parts_has_none_without() -> None:
    """The tuple is empty, not missing."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    plant.item("r1", parent=board, part=make_footprint(plant, "r", "R_0603"), designation="R1")
    assert board_netlist(plant.model(), board).without_footprint == ()


def test_an_unnumbered_item_without_a_footprint_is_listed_and_raises_nothing() -> None:
    """No designation is read for it, so an unnumbered connector is a listing, not an error."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    plant.item("j1", parent=board, part=make_part(plant, "conn", "CONN"))
    assert board_netlist(plant.model(), board).without_footprint == (make_id(Item, ("j1",)),)


def test_a_part_carries_the_installed_flag_of_its_item() -> None:
    """An uninstalled part stays listed with `installed=False`; the others say `True`."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    footprint = make_footprint(plant, "r", "R_0603")
    plant.item("r1", parent=board, part=footprint, designation="R1")
    plant.item("r2", parent=board, part=footprint, designation="R2", installed=False)
    parts = board_netlist(plant.model(), board).parts
    assert [(part.designation, part.installed) for part in parts] == [("R1", True), ("R2", False)]


def test_an_uninstalled_item_without_a_footprint_is_still_listed() -> None:
    """`installed` filters nothing here: the output decides."""
    plant = Plant()
    board = plant.item("board", designation="A1")
    plant.item("j1", parent=board, part=make_part(plant, "conn", "CONN"), installed=False)
    assert board_netlist(plant.model(), board).without_footprint == (make_id(Item, ("j1",)),)


def test_a_parent_cycle_through_the_board_never_lists_the_board() -> None:
    """The board reached again through its own child is not its own part, footprint or not."""
    plant = Plant()
    bare = make_part(plant, "conn", "CONN")
    board = plant.item("board", designation="A1", part=bare, parent=make_id(Item, ("child",)))
    plant.item("child", parent=board, part=bare, designation="J1")
    netlist = board_netlist(plant.model(), board)
    assert netlist.without_footprint == (make_id(Item, ("child",)),)


def test_the_extra_fields_do_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same netlist."""
    plant = _board()
    model = plant.model()
    board = make_id(Item, ("board",))
    assert board_netlist(reversed_tables(model), board) == board_netlist(model, board)
