"""Tests for a unit instance's BOM-line `designations` (units spec U5, amended 2026-09-24)."""

from typing import TYPE_CHECKING

from plant import Plant
from query_builders import make_node, make_part, make_placement

from fransys_model.derive import TOP_LEVEL, BomLine, bom_lines
from fransys_model.derive.bom import _part_designations
from fransys_model.derive.designation import location_designation, product_designation
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.templates import Part


def _place(plant: Plant, item: Id[Item], node: AspectNode) -> None:
    plant.add(make_placement(f"p-{item.value}", item, node.id))


def _locations(plant: Plant) -> dict[str, AspectNode]:
    """Location nodes `+C1`, `+C2` at the root and `+C1+SUB` under `C1`."""
    nodes = {"c1": make_node("c1", None), "c2": make_node("c2", None)}
    nodes["sub"] = make_node("sub", nodes["c1"].id)
    plant.add(*nodes.values())
    return nodes


def _line(plant: Plant) -> BomLine:
    """The one top-level unit line, which must be the `cabinet` one."""
    (line,) = [ln for ln in bom_lines(plant.model(), TOP_LEVEL) if ln.part is None]
    assert line.mpn == "cabinet"
    return line


def _external_item(plant: Plant, key: str, *, part: Id[Part], designation: str) -> Id[Item]:
    """An item flagged `external=True` (decision model-0045); `Plant.item` has no such option."""
    item = Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=part,
        parent=None,
        position=None,
        tag=designation,
        description="Invented",
        installed=True,
        unit=None,
        external=True,
    )
    plant.add(item)
    return item.id


def test_a_unit_instance_with_several_root_items_lists_its_location() -> None:
    """Three root items all at `+C1`: the line says `("+C1",)`, not the three items."""
    plant = Plant()
    nodes = _locations(plant)
    unit = plant.unit("cab", name="cabinet")
    part = make_part(plant, "relay", "R-1")
    for key, designation in (("k1", "K1"), ("k2", "K2"), ("k3", "K3")):
        item = plant.item(key, part=part, designation=designation, unit=unit)
        _place(plant, item, nodes["c1"])
    line = _line(plant)
    assert line.designations == ("+C1",)
    assert line.count == 1


def test_a_board_unit_keeps_its_one_root_items_designation_even_when_placed() -> None:
    """One root item (the board, with a child in the unit): its `printed_designation`, no `+C1`."""
    plant = Plant()
    nodes = _locations(plant)
    unit = plant.unit("cab", name="cabinet")
    board = plant.item("board", part=make_part(plant, "board", "B-1"), designation="U2", unit=unit)
    plant.item(
        "k1", parent=board, part=make_part(plant, "relay", "R-1"), designation="K1", unit=unit
    )
    _place(plant, board, nodes["c1"])
    assert _line(plant).designations == ("-U2",)


def test_a_unit_with_no_location_and_several_roots_lists_the_roots() -> None:
    """Nothing placed, two roots: the roots' designations, sorted, as before."""
    plant = Plant()
    unit = plant.unit("cab", name="cabinet")
    part = make_part(plant, "relay", "R-1")
    plant.item("k2", part=part, designation="K2", unit=unit)
    plant.item("k1", part=part, designation="K1", unit=unit)
    assert _line(plant).designations == ("-K1", "-K2")


def test_an_unplaced_root_adds_nothing_beside_a_placed_one() -> None:
    """Two roots, one at `+C1`, one unplaced: the location stands for the instance."""
    plant = Plant()
    nodes = _locations(plant)
    unit = plant.unit("cab", name="cabinet")
    part = make_part(plant, "relay", "R-1")
    placed = plant.item("k1", part=part, designation="K1", unit=unit)
    plant.item("k2", part=part, designation="K2", unit=unit)
    _place(plant, placed, nodes["c1"])
    assert _line(plant).designations == ("+C1",)


def test_roots_in_two_locations_give_two_sorted_entries_and_nested_text() -> None:
    """Roots at `+C2`, `+C1+SUB` and `+C2` again: distinct, sorted, nested text as rendered."""
    plant = Plant()
    nodes = _locations(plant)
    unit = plant.unit("cab", name="cabinet")
    part = make_part(plant, "relay", "R-1")
    for key, designation, node in (
        ("k1", "K1", "c2"),
        ("k2", "K2", "sub"),
        ("k3", "K3", "c2"),
    ):
        item = plant.item(key, part=part, designation=designation, unit=unit)
        _place(plant, item, nodes[node])
    assert _line(plant).designations == ("+C1+SUB", "+C2")


def test_two_instances_at_one_location_print_it_twice() -> None:
    """Entries of all instances of a `(name, revision)` group are concatenated, one per instance."""
    plant = Plant()
    nodes = _locations(plant)
    part = make_part(plant, "relay", "R-1")
    for key, node in (("cab-a", "c1"), ("cab-b", "c1"), ("cab-c", "c2")):
        unit = plant.unit(key, name="cabinet")
        for suffix in ("x", "y"):
            item = plant.item(f"{key}-{suffix}", part=part, designation=suffix.upper(), unit=unit)
            _place(plant, item, nodes[node])
    line = _line(plant)
    assert (line.count, line.designations) == (3, ("+C1", "+C1", "+C2"))


def test_location_designation_is_none_without_a_location_placement() -> None:
    """`None` for an unplaced item; `product_designation` keeps its bare `-K1` fallback."""
    plant = Plant()
    nodes = _locations(plant)
    part = make_part(plant, "relay", "R-1")
    bare = plant.item("bare", part=part, designation="K1")
    placed = plant.item("placed", part=part, designation="K2")
    _place(plant, placed, nodes["sub"])
    model = plant.model()
    assert location_designation(model, bare) is None
    assert product_designation(model, bare) == "-K1"
    assert location_designation(model, placed) == "+C1+SUB"
    assert product_designation(model, placed) == "+C1+SUB-K2"


def test_external_and_uninstalled_items_have_no_bom_line() -> None:
    """An external item, or an uninstalled one, prints no line for its part (external-items Y1)."""
    plant = Plant()
    external_part = make_part(plant, "ext-relay", "R-EXT")
    uninstalled_part = make_part(plant, "uninst-relay", "R-UNINST")
    normal_part = make_part(plant, "relay", "R-1")
    _external_item(plant, "ext", part=external_part, designation="K1")
    plant.item("uninst", installed=False, part=uninstalled_part, designation="K2")
    plant.item("normal", part=normal_part, designation="K3")
    parts_on_lines = {line.part for line in bom_lines(plant.model(), None)}
    assert external_part not in parts_on_lines
    assert uninstalled_part not in parts_on_lines
    assert normal_part in parts_on_lines  # a plain installed, non-external item still gets a line


def test_top_level_scope_gives_a_summary_line_the_whole_model_does_not() -> None:
    """TOP_LEVEL adds a top-level unit's own line; `None` counts its items directly (U5, U6)."""
    plant = Plant()
    unit = plant.unit("cab", name="cabinet")
    part = make_part(plant, "relay", "R-1")
    plant.item("k1", part=part, designation="K1", unit=unit)

    top_level = bom_lines(plant.model(), TOP_LEVEL)
    whole_model = bom_lines(plant.model(), None)

    assert part not in {line.part for line in top_level}
    assert part in {line.part for line in whole_model}
    (unit_line,) = [line for line in top_level if line.part is None]
    assert unit_line.mpn == "cabinet"
    assert not [line for line in whole_model if line.part is None]


def test_an_accessorys_holder_text_prints_once_not_twice() -> None:
    """An accessory sharing its holder's part contributes no second designation, in either order."""
    plant = Plant()
    part = make_part(plant, "relay", "R-1")
    holder = plant.item("holder", part=part, designation="K1")
    accessory = plant.item("accessory", part=part, parent=holder)
    model = plant.model()
    assert _part_designations(model, [holder, accessory], None) == ("-K1",)
    assert _part_designations(model, [accessory, holder], None) == ("-K1",)
    (line,) = [ln for ln in bom_lines(model, None) if ln.part == part]
    assert line.count == 2


def test_an_own_unit_root_skips_only_itself_not_the_rest_of_the_line() -> None:
    """The own-root's skip is per item, not a loop stop: a later item on the line still prints."""
    plant = Plant()
    unit = plant.unit("u")
    root = plant.item("root", part=make_part(plant, "relay", "R-1"), designation="K1", unit=unit)
    other = plant.item("other", part=make_part(plant, "fuse", "F-1"), designation="F1")
    model = plant.model()
    assert _part_designations(model, [root, other], unit) == ("-F1",)


def test_a_holder_skipped_via_accessory_does_not_stop_a_later_items_own_text() -> None:
    """The via-accessory skip is per item too: an unrelated item after the holder still prints."""
    plant = Plant()
    part = make_part(plant, "relay", "R-1")
    holder = plant.item("holder", part=part, designation="K1")
    accessory = plant.item("accessory", part=part, parent=holder)
    other = plant.item("other", part=make_part(plant, "fuse", "F-1"), designation="F1")
    model = plant.model()
    assert _part_designations(model, [accessory, holder, other], None) == ("-K1", "-F1")
