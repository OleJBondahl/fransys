"""Tests for `bom_lines(model, scope)`: an item subtree, a location node or a unit
(design/derive-queries.md)."""

import pytest
from plant import Plant
from query_builders import make_part, make_placement, make_tree, reversed_tables

from fransys_model.derive import TOP_LEVEL, BomLine, bom_lines
from fransys_model.derive.bom import _bom_line_key
from fransys_model.derive.designation import printed_designation
from fransys_model.derive.structure import items_at
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.templates import Part


def _counts(lines: tuple[BomLine, ...]) -> dict[str, tuple[str, ...]]:
    return {line.mpn: line.designations for line in lines}


def _cabinet() -> Plant:
    """`A1` (part `CAB`) holds `k1` (relay) which holds `k2` (relay); `k3` and `f1` are outside."""
    plant = Plant()
    relay = make_part(plant, "relay", "R-1")
    fuse = make_part(plant, "fuse", "F-1")
    cabinet = plant.item("cab", part=make_part(plant, "cab", "CAB"), designation="A1")
    k1 = plant.item("k1", parent=cabinet, part=relay, designation="K1")
    plant.item("k2", parent=k1, part=relay, designation="K2")
    plant.item("k3", part=relay, designation="K3")
    plant.item("f1", parent=cabinet, part=fuse, designation="F1")
    plant.item("f2", parent=cabinet, part=fuse, designation="F2", installed=False)
    return plant


def test_no_scope_counts_the_whole_model_as_before() -> None:
    """`scope=None` is the unscoped count."""
    model = _cabinet().model()
    assert bom_lines(model, None) == bom_lines(model)
    assert _counts(bom_lines(model)) == {
        "CAB": ("-A1",),
        "F-1": ("-F1",),
        "R-1": ("-K1", "-K2", "-K3"),
    }


def test_an_item_scope_counts_the_item_and_its_descendants_only() -> None:
    """`A1` covers itself, `K1`, `K2` and `F1`; `K3` (no parent) is outside."""
    model = _cabinet().model()
    lines = bom_lines(model, make_id(Item, ("cab",)))
    assert _counts(lines) == {"CAB": ("-A1",), "F-1": ("-F1",), "R-1": ("-K1", "-K2")}
    assert [line.count for line in lines] == [1, 1, 2]


def test_an_item_scope_deeper_in_the_tree_leaves_its_parent_out() -> None:
    """`K1` covers `K1` and `K2`, not the cabinet holding them."""
    model = _cabinet().model()
    assert _counts(bom_lines(model, make_id(Item, ("k1",)))) == {"R-1": ("-K1", "-K2")}


def test_an_uninstalled_item_in_scope_is_not_counted() -> None:
    """`F2` sits under `A1` but is not installed: the fuse line counts `F1` only."""
    model = _cabinet().model()
    (fuse,) = [line for line in bom_lines(model, make_id(Item, ("cab",))) if line.mpn == "F-1"]
    assert (fuse.count, fuse.designations) == (1, ("-F1",))


def test_a_node_scope_counts_the_items_placed_at_the_node_or_below() -> None:
    """`left` covers what is placed at `left` and at its child `leaf`; `lone` covers its own."""
    plant = _cabinet()
    ids = make_tree(plant)
    for key, node in (("k1", "left"), ("k2", "leaf"), ("k3", "lone")):
        plant.add(make_placement(f"p-{key}", make_id(Item, (key,)), ids[node]))
    model = plant.model()
    assert _counts(bom_lines(model, ids["left"])) == {"R-1": ("-K1", "-K2")}
    assert _counts(bom_lines(model, ids["leaf"])) == {"R-1": ("-K2",)}
    assert _counts(bom_lines(model, ids["lone"])) == {"R-1": ("-K3",)}


def test_a_node_with_nothing_placed_gives_no_lines() -> None:
    """A part none of whose items is in scope has no line."""
    plant = _cabinet()
    ids = make_tree(plant)
    assert bom_lines(plant.model(), ids["root"]) == ()


def test_a_scope_that_is_neither_an_item_nor_a_node_raises() -> None:
    """A port id, an item id the model lacks and a node id the model lacks all raise."""
    plant = _cabinet()
    make_tree(plant)
    model = plant.model()
    for scope in (
        Id(kind="port", value="1" * 32),
        Id(kind="item", value="9" * 32),
        Id(kind="aspect_node", value="9" * 32),
    ):
        with pytest.raises(SchemaError):
            bom_lines(model, scope)


def test_an_unknown_item_scope_raises_naming_itself() -> None:
    """An `Id[Item]` scope absent from the model raises `SchemaError(kind="item")` on itself."""
    model = _cabinet().model()
    scope = Id(kind="item", value="9" * 32)
    with pytest.raises(SchemaError) as excinfo:
        bom_lines(model, scope)
    assert excinfo.value.kind == "item"
    assert excinfo.value.record_id == scope


def test_an_aspect_node_scope_matches_items_at() -> None:
    """The node scope's printed designations are exactly `items_at`'s items, printed."""
    plant = _cabinet()
    ids = make_tree(plant)
    for key, node in (("k1", "left"), ("k2", "leaf"), ("k3", "lone")):
        plant.add(make_placement(f"p-{key}", make_id(Item, (key,)), ids[node]))
    model = plant.model()
    for node_key in ("left", "leaf", "lone"):
        node = ids[node_key]
        expected = {printed_designation(model, item) for item in items_at(model, node)}
        got = {text for line in bom_lines(model, node) for text in line.designations}
        assert got == expected


def test_a_scope_that_is_neither_item_nor_node_raises_its_own_kind() -> None:
    """A `Function` scope raises with `kind="function"`, not the item branch's hardcoded text."""
    model = _cabinet().model()
    scope = Id(kind="function", value="1" * 32)
    with pytest.raises(SchemaError) as excinfo:
        bom_lines(model, scope)
    assert excinfo.value.kind == "function"
    assert excinfo.value.record_id == scope


def test_the_scoped_lines_do_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same lines for both scope kinds."""
    plant = _cabinet()
    ids = make_tree(plant)
    plant.add(make_placement("p-k1", make_id(Item, ("k1",)), ids["left"]))
    model = plant.model()
    for scope in (make_id(Item, ("cab",)), ids["left"]):
        assert bom_lines(reversed_tables(model), scope) == bom_lines(model, scope)


# ---- units spec U5: a unit's own scope, TOP_LEVEL, and unit BOM lines -------------------


def _two_level() -> tuple[Plant, Id[Unit], Id[Unit]]:
    """`top` (a unit) directly holds `psu`; `top` nests `board`, which holds `board`/`k1`.

    `board` (the item) is `board`-unit's own root item (no parent); `k1` is `board`-unit's
    too, but parented under `board`, so it has a parent *inside* its own unit and is not a
    root item. A loose item with no unit at all sits outside both.
    """
    plant = Plant()
    top = plant.unit("top", name="pump-cabinet", revision=1)
    plant.revision(top)
    board_unit = plant.unit("board-unit", name="relay-board", revision=1, parent=top)
    plant.revision(board_unit)
    plant.item("psu", part=make_part(plant, "psu", "PSU-1"), designation="G1", unit=top)
    board_item = plant.item(
        "board", part=make_part(plant, "board", "BOARD-1"), designation="A2", unit=board_unit
    )
    plant.item(
        "k1",
        parent=board_item,
        part=make_part(plant, "relay", "RELAY-1"),
        designation="K1",
        unit=board_unit,
    )
    plant.item("loose", part=make_part(plant, "loose", "LOOSE-1"), designation="X9")
    return plant, top, board_unit


def test_a_units_own_scope_gives_one_line_for_a_direct_nested_unit() -> None:
    """`bom_lines(model, top)`: one line for `board-unit`, count asserted 1, not "at least 1"."""
    plant, top, _board_unit = _two_level()
    model = plant.model()
    lines = bom_lines(model, top)
    unit_lines = [line for line in lines if line.part is None]
    assert len(unit_lines) == 1
    (unit_line,) = unit_lines
    assert (unit_line.mpn, unit_line.revision, unit_line.count) == ("relay-board", "1.1", 1)
    assert unit_line.manufacturer == ""
    assert unit_line.designations == ("-A2",)
    # can-fail probe (spec's own): a nested item's part must never sneak into the parent scope
    assert "BOARD-1" not in {line.mpn for line in lines}
    assert "RELAY-1" not in {line.mpn for line in lines}


def test_a_units_own_scope_still_counts_its_own_direct_items() -> None:
    """The same call also gives the ordinary part lines for `top`'s own direct items.

    `psu` alone would be `top`'s sole root, silent in its own scope (UNIT-ID I4); the second root,
    `fan`, makes it a several-root unit, so both keep their designations.
    """
    plant, top, _board_unit = _two_level()
    plant.item("fan", part=make_part(plant, "fan", "FAN-1"), designation="M1", unit=top)
    model = plant.model()
    lines = bom_lines(model, top)
    part_lines = {line.mpn: line for line in lines if line.part is not None}
    assert set(part_lines) == {"PSU-1", "FAN-1"}
    assert part_lines["PSU-1"].designations == ("-G1",)
    assert part_lines["FAN-1"].designations == ("-M1",)
    assert part_lines["PSU-1"].revision == ""


def test_top_level_scope_gives_unowned_items_plus_one_line_per_top_level_unit() -> None:
    """`TOP_LEVEL`: the loose item's own line, and one line for `top`, not for `board-unit`."""
    plant, _top, _board_unit = _two_level()
    model = plant.model()
    lines = bom_lines(model, TOP_LEVEL)
    part_lines = {line.mpn: line for line in lines if line.part is not None}
    unit_lines = {line.mpn: line for line in lines if line.part is None}
    # examined: the loose item (unit=None) is really outside any unit
    assert set(part_lines) == {"LOOSE-1"}
    assert set(unit_lines) == {"pump-cabinet"}
    assert unit_lines["pump-cabinet"].designations == ("-G1",)
    assert "relay-board" not in unit_lines


def test_a_leaf_units_own_scope_gives_its_items_and_no_unit_line() -> None:
    """`bom_lines(model, board_unit)`: its own two part lines; no unit line (no children)."""
    plant, _top, board_unit = _two_level()
    model = plant.model()
    lines = bom_lines(model, board_unit)
    part_mpns = {line.mpn for line in lines if line.part is not None}
    unit_lines = [line for line in lines if line.part is None]
    assert part_mpns == {"BOARD-1", "RELAY-1"}
    assert unit_lines == []


def test_an_unknown_unit_scope_raises() -> None:
    """A unit id the model does not hold is refused, the same `require`-based pattern."""
    plant, _top, _board_unit = _two_level()
    model = plant.model()
    with pytest.raises(SchemaError):
        bom_lines(model, Id(kind="unit", value="9" * 32))


def test_the_unit_scoped_lines_do_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same lines for the unit scope."""
    plant, top, _board_unit = _two_level()
    model = plant.model()
    for scope in (top, TOP_LEVEL):
        lines = bom_lines(model, scope)
        # examined: each scope really has both a part line and a unit line to compare
        assert any(line.part is not None for line in lines)
        assert any(line.part is None for line in lines)
        assert bom_lines(reversed_tables(model), scope) == lines


def test_a_model_with_no_unit_gives_byte_equal_bom_lines() -> None:
    """`scope=None` on a model with no `Unit` at all is unchanged: no unit line, ever."""
    model = _cabinet().model()
    lines = bom_lines(model, None)
    assert lines
    assert all(line.part is not None for line in lines)
    assert all(line.revision == "" for line in lines)


def _two_level_multi() -> tuple[Plant, Id[Unit]]:
    """`top` nests two `relay-board` revision 1 instances and one revision 2 instance."""
    plant = Plant()
    top = plant.unit("top", name="pump-cabinet", revision=1)
    plant.revision(top)
    board_a = plant.unit("board-a", name="relay-board", revision=1, parent=top)
    plant.revision(board_a)
    board_b = plant.unit("board-b", name="relay-board", revision=1, parent=top)
    plant.revision(board_b)
    board_c = plant.unit("board-c", name="relay-board", revision=2, parent=top)
    plant.revision(board_c, 2)
    board_part = make_part(plant, "board", "BOARD-1")
    plant.item("board-a-item", part=board_part, designation="A2", unit=board_a)
    plant.item("board-b-item", part=board_part, designation="A3", unit=board_b)
    plant.item("board-c-item", part=board_part, designation="A4", unit=board_c)
    return plant, top


def test_direct_child_units_group_by_name_and_revision() -> None:
    """Two `relay-board` revision 1 instances are one line, `count=2`, designations merged."""
    plant, top = _two_level_multi()
    model = plant.model()
    lines = bom_lines(model, top)
    unit_lines = {(line.mpn, line.revision): line for line in lines if line.part is None}
    assert len(unit_lines) == 2
    rev01 = unit_lines[("relay-board", "1.1")]
    assert (rev01.count, rev01.designations) == (2, ("-A2", "-A3"))
    rev02 = unit_lines[("relay-board", "1.2")]
    assert (rev02.count, rev02.designations) == (1, ("-A4",))


def _board_cabinet(releases: list[tuple[int, int]]) -> tuple[Plant, Id[Unit]]:
    """`cab` nests one `demo-io-board` instance per `(version, revision)` of `releases`."""
    plant = Plant()
    cab = plant.unit("cab", name="demo-cabinet")
    plant.revision(cab)
    board_part = make_part(plant, "board", "BOARD-1")
    for n, (version, revision) in enumerate(releases, start=1):
        board = plant.unit(
            f"board-{n}", name="demo-io-board", version=version, revision=revision, parent=cab
        )
        plant.item(f"board-{n}-item", part=board_part, designation=f"A{n}", unit=board)
    return plant, cab


def _unit_revisions(plant: Plant, cab: Id[Unit]) -> list[tuple[str, int]]:
    lines = bom_lines(plant.model(), cab)
    return [(line.revision, line.count) for line in lines if line.part is None]


def test_two_versions_of_one_board_name_are_two_unit_lines() -> None:
    """FD acceptance 7b: `demo-io-board` at 1.1 and at 2.1 in one cabinet, two lines, not one."""
    plant, cab = _board_cabinet([(1, 1), (2, 1)])
    assert _unit_revisions(plant, cab) == [("1.1", 1), ("2.1", 1)]


def test_two_instances_of_one_release_are_one_unit_line_of_count_two() -> None:
    """The grouping key is `(name, version, revision)`: two instances of 2.1 are one line."""
    plant, cab = _board_cabinet([(2, 1), (2, 1)])
    assert _unit_revisions(plant, cab) == [("2.1", 2)]


def test_unit_lines_of_one_name_sort_by_release_order_not_by_printed_text() -> None:
    """1.2, 1.10, 2.1 come in that order, whatever order the instances were added in.

    A sort on the printed text puts `"1.10"` before `"1.2"`.
    """
    plant, cab = _board_cabinet([(2, 1), (1, 10), (1, 2)])
    texts = [text for text, _count in _unit_revisions(plant, cab)]
    assert texts == ["1.2", "1.10", "2.1"]
    assert texts != sorted(texts)


def test_the_sort_key_never_compares_none_to_an_id() -> None:
    """A unit line and a part line tied on `(mpn, order)` still compare, no `TypeError`.

    Real data can no longer make this tie: a part line's order is `(0, 0)` and a unit line's is
    a release's, `>= (1, 1)`, so the two differ at the second position before the `part`
    positions are reached. The guard in `_bom_line_key` is therefore tested directly, on
    hand-made lines given one order, one with `part=None` and one with an `Id`.
    """
    part = make_id(Part, ("shared",))
    unit_line = BomLine(
        part=None,
        mpn="SHARED",
        manufacturer="",
        description="",
        count=1,
        designations=(),
        revision="1.1",
    )
    part_line = BomLine(
        part=part,
        mpn="SHARED",
        manufacturer="Example Co",
        description="",
        count=1,
        designations=(),
        revision="1.1",
    )
    tied = (1, 1)

    def key(line: BomLine) -> tuple[str, tuple[int, int], bool, Id[Part] | None]:
        return _bom_line_key(line, tied)

    assert key(unit_line)[:2] == key(part_line)[:2]
    assert sorted([part_line, unit_line], key=key) == [part_line, unit_line]
    assert sorted([unit_line, part_line], key=key) == [part_line, unit_line]
    # a part line's real order `(0, 0)` is below any release's: it sorts first without the guard
    assert _bom_line_key(part_line, (0, 0))[:2] < _bom_line_key(unit_line, (1, 1))[:2]
