"""Tests: an accessory item prints its parent's designation (model-0058).

An accessory is a part-bearing, untagged, function-less, non-terminal child of a designated
part-bearing holder. After numbering it has no `designation`, and everything that prints it
prints the holder's.
"""

from typing import TYPE_CHECKING

import pytest
from plant import Plant

from fransys_model.derive import (
    board_netlist,
    bom_lines,
    designation_list,
    item_designation,
    takes_parents_designation,
)
from fransys_model.derive.designation import own_designation_or_none, terminal_designation
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import make_id
from fransys_model.vocab.facets.pcb import FootprintFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import items, parts

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item
    from fransys_model.vocab.templates import Part


def _fuse_line_designations(model: Model) -> tuple[int, tuple[str, ...]]:
    """The `count` and `designations` of the BOM line of the fuse-link part (mpn `EXAMPLE-F`)."""
    (part,) = (p.id for p in parts(model).values() if p.mpn == "EXAMPLE-F")
    (line,) = [ln for ln in bom_lines(model) if ln.part == part]
    return line.count, line.designations


def _holders(plant: Plant, *, parent: Id[Item] | None = None) -> list[Id[Item]]:
    """Two tagged holders, `F11` and `F21`, each with three fuse-link children; the links."""
    holder_part, link_part = plant.part("H"), plant.part("F")
    links = []
    for tag in ("F11", "F21"):
        holder = plant.item(f"holder-{tag}", part=holder_part, designation=tag, parent=parent)
        links.extend(
            plant.item(f"link-{tag}-{n}", part=link_part, parent=holder) for n in (1, 2, 3)
        )
    return links


def test_a_child_prints_its_tagged_holders_designation() -> None:
    """After numbering, the child's `item_designation` is the holder's `F11`."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    link = plant.item("link", part=plant.part("F"), parent=holder)
    model, _ = number(plant.model())
    assert item_designation(model, link) == "F11"


def test_a_child_prints_its_untagged_holders_numbered_designation() -> None:
    """The holder has only a class code, so numbering tags it `H1`; the child prints `H1`."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"))
    link = plant.item("link", part=plant.part("F"), parent=holder)
    model, _ = number(plant.model())
    assert item_designation(model, link) == "H1"


def test_a_child_inside_a_board_prints_the_boards_designation_in_front() -> None:
    """A holder inside board `A1` prints `A1-F11`, and so does its child."""
    plant = Plant()
    board = plant.item("board", part=plant.board_part())
    holder = plant.item("holder", part=plant.part("H"), designation="F11", parent=board)
    link = plant.item("link", part=plant.part("F"), parent=holder)
    model, _ = number(plant.model())
    assert item_designation(model, holder) == "A1-F11"
    assert item_designation(model, link) == "A1-F11"


def test_the_designation_list_has_a_row_for_the_holder_and_none_for_its_children() -> None:
    """One row per designated item: the holder's; the accessory children have none."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    links = [plant.item(f"link-{n}", part=plant.part("F"), parent=holder) for n in (1, 2, 3)]
    model, _ = number(plant.model())
    rows = designation_list(model)
    assert [row.item for row in rows] == [holder]
    assert all(row.item not in links for row in rows)


def test_the_bom_counts_the_children_and_lists_each_holders_designation_once() -> None:
    """Three fuse links in `F11` and three in `F21`: `count == 6`, two designations."""
    plant = Plant()
    _holders(plant)
    model, _ = number(plant.model())
    assert _fuse_line_designations(model) == (6, ("-F11", "-F21"))


def test_the_bom_lists_the_holders_designation_once_for_a_holder_inside_a_board() -> None:
    """The same in a board: the printed text carries the board's `A1-` in front."""
    plant = Plant()
    board = plant.item("board", part=plant.board_part())
    _holders(plant, parent=board)
    model, _ = number(plant.model())
    assert _fuse_line_designations(model) == (6, ("-A1-F11", "-A1-F21"))


def test_a_child_with_an_authored_tag_lists_its_own_designation_in_the_bom() -> None:
    """The authored `F5` is no accessory: the link's line lists `-F5` (the holder is on another
    BOM line).

    Expected to pass on the base as well: the child keeps its authored tag either way.
    """
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    plant.item("tagged", part=plant.part("F"), parent=holder, designation="F5")
    model, _ = number(plant.model())
    assert _fuse_line_designations(model) == (1, ("-F5",))


def test_a_repeated_text_of_an_item_that_is_no_accessory_stays_in_the_bom() -> None:
    """Two items in two unit instances both authored `K1` print `-K1` twice: only an accessory's
    repeated text is dropped.

    Expected to pass on the base as well: nothing is an accessory there.
    """
    plant = Plant()
    part = plant.part("F")
    plant.item("a", part=part, designation="K1", unit=plant.unit("cab-a"))
    plant.item("b", part=part, designation="K1", unit=plant.unit("cab-b"))
    model, _ = number(plant.model())
    assert _fuse_line_designations(model) == (2, ("-K1", "-K1"))


def test_two_unit_instances_with_one_holder_text_each_keep_both_in_the_bom() -> None:
    """Two units each hold an authored `F11` holder with two links: the dedupe is per holder,
    not per text, so the line keeps one `-F11` for each holder."""
    plant = Plant()
    holder_part, link_part = plant.part("H"), plant.part("F")
    for name in ("cab-a", "cab-b"):
        unit = plant.unit(name)
        holder = plant.item(f"holder-{name}", part=holder_part, designation="F11", unit=unit)
        for n in (1, 2):
            plant.item(f"link-{name}-{n}", part=link_part, parent=holder, unit=unit)
    model, _ = number(plant.model())
    assert _fuse_line_designations(model) == (4, ("-F11", "-F11"))


def test_a_child_of_an_accessory_prints_the_holders_designation() -> None:
    """`sub` under `link` under the tagged holder `F11` prints `F11`: the chain walks to the top."""
    plant = Plant()
    holder = plant.item("holder", part=plant.part("H"), designation="F11")
    link = plant.item("link", part=plant.part("F"), parent=holder)
    sub = plant.item("sub", part=plant.part("Q"), parent=link)
    model, _ = number(plant.model())
    assert item_designation(model, sub) == "F11"


def test_a_component_of_a_board_under_a_designated_device_prints() -> None:
    """The board `card` under the tagged device `A5` numbers `A1`, so its relay prints `A1-K1`
    instead of raising for a board with no designation."""
    plant = Plant()
    device = plant.item("device", part=plant.part("D"), designation="A5")
    card = plant.item("card", part=plant.board_part(), parent=device)
    relay = plant.item("relay", part=plant.part("K"), parent=card)
    model, _ = number(plant.model())
    assert item_designation(model, relay) == "A1-K1"


def test_a_terminal_child_of_a_designated_device_is_no_accessory() -> None:
    """A terminal (a part-bearing child of the tagged strip `X1`) keeps its terminal text."""
    plant = Plant()
    strip = plant.item("strip", part=plant.part("X"), designation="X1")
    terminal = plant.item("terminal", part=plant.part("Z"), parent=strip)
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("t", "terminal")),
            key=("t", "terminal"),
            subject=terminal,
            group="L1",
            index=1,
        )
    )
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, terminal)
    assert terminal_designation(model, terminal) == "-X1:L1:1"


def _footprint(plant: Plant, part: Id[Part]) -> None:
    """A `FootprintFacet` on `part`, keyed by the part's own key."""
    key = ("footprint", *plant._key_of(part))
    plant.add(
        FootprintFacet(
            id=make_id(FootprintFacet, key),
            key=key,
            subject=part,
            library="ExampleLib",
            name="Fuse_Holder",
        )
    )


def _board_with_a_footprinted_holder_and_link(plant: Plant) -> tuple[Id[Item], Id[Item], Id[Item]]:
    """Board, holder `F11` (footprinted part) and a function-less footprinted link under it."""
    holder_part, link_part = plant.part("H"), plant.part("F")
    _footprint(plant, holder_part)
    _footprint(plant, link_part)
    board = plant.item("board", part=plant.board_part())
    holder = plant.item("holder", part=holder_part, designation="F11", parent=board)
    link = plant.item("link", part=link_part, parent=holder)
    return board, holder, link


def test_an_item_whose_part_has_a_footprint_is_no_accessory_and_is_numbered() -> None:
    """A footprinted link is a part of its own on the board: `takes_parents_designation` is
    False and numbering gives it a designation of its own.

    Fails on the base: the footprint is not looked at, so the link is an accessory (True) and
    stays without a designation.
    """
    plant = Plant()
    _, _, link = _board_with_a_footprinted_holder_and_link(plant)
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, link)
    assert own_designation_or_none(model, items(model)[link]) is not None


def test_a_footprinted_holder_and_link_are_two_board_parts_with_distinct_designations() -> None:
    """`board_netlist` lists the holder `F11` and the link (its own number) as two parts.

    Fails on the base: the link is an accessory, prints the holder's `F11`, and the two parts
    collide.
    """
    plant = Plant()
    board, holder, link = _board_with_a_footprinted_holder_and_link(plant)
    model, _ = number(plant.model())
    listed = {part.item: part.designation for part in board_netlist(model, board).parts}
    assert set(listed) == {holder, link}
    assert listed[holder] == "F11"
    assert listed[link] != "F11"


def test_an_item_with_a_function_in_its_subtree_is_no_accessory() -> None:
    """A part-bearing strip with no tag and no function of its own, holding a terminal that
    carries a function, is no accessory of `U1`: it numbers `X1` and its terminal prints
    `-X1:L1:1`, not `-U1:L1:1`.

    Fails on the base: only the strip's own functions count, so it is an accessory of `U1`.
    """
    plant = Plant()
    holder = plant.item("holder", part=plant.part("U"), designation="U1")
    strip = plant.item("strip", part=plant.part("X"), parent=holder)
    terminal = plant.item("t1", part=plant.part("Z"), parent=strip)
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("t", "t1")),
            key=("t", "t1"),
            subject=terminal,
            group="L1",
            index=1,
        )
    )
    plant.function(terminal, "p")
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, strip)
    assert item_designation(model, strip) == "X1"
    assert terminal_designation(model, terminal) == "-X1:L1:1"


def test_an_item_with_a_function_two_levels_below_it_is_no_accessory() -> None:
    """A function nested two levels below the checked item -- through a plain intermediate
    item that carries no function of its own -- still makes it no accessory: `holder` sits
    above `intermediate` (no function), which sits above the terminal that carries the
    function. Proves the has-a-function-below set is transitive across two or more levels,
    not just a direct-children shortcut (model-0103 B10).
    """
    plant = Plant()
    top = plant.item("top", part=plant.part("U"), designation="U1")
    holder = plant.item("holder", part=plant.part("H"), parent=top)
    intermediate = plant.item("intermediate", part=plant.part("Y"), parent=holder)
    terminal = plant.item("t1", part=plant.part("Z"), parent=intermediate)
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, ("t", "t1")),
            key=("t", "t1"),
            subject=terminal,
            group="L1",
            index=1,
        )
    )
    plant.function(terminal, "p")
    model, _ = number(plant.model())
    assert not takes_parents_designation(model, holder)


@pytest.mark.parametrize("link_key", ["a-link", "z-link"])
@pytest.mark.parametrize("links", [1, 2])
def test_a_holder_and_its_accessories_of_one_part_list_the_holder_once(
    link_key: str, links: int
) -> None:
    """One part `F` for the holder `F11` and its `links` accessories: `count == 1 + links`,
    the designations are `("-F11",)`, whichever of the authoring keys sorts first (the link's
    key `a-link` before the holder's `m-holder`, or `z-link` after it).

    Fails on the base: the holder is no accessory, so its own `-F11` is listed besides the one
    the accessories' holder gets.
    """
    plant = Plant()
    part = plant.part("F")
    holder = plant.item("m-holder", part=part, designation="F11")
    for n in range(links):
        plant.item(f"{link_key}-{n}", part=part, parent=holder)
    model, _ = number(plant.model())
    assert _fuse_line_designations(model) == (1 + links, ("-F11",))
