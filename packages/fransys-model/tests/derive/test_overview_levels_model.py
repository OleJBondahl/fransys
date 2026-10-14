"""`overview_level` and `strip_view` (model-0197) on a small unit: fold, lift, stub, strip order."""

from overview_builders import item_id, unit_plant

from fransys_model.derive import ItemKind, open_strips, overview_level, strip_stubs, strip_view


def test_a_strip_and_a_nested_unit_fold_into_one_box_each() -> None:
    """Terminals fold into their strip with a count; Z1 folds into the nested unit's box."""
    model, outer, nested = unit_plant()
    boxes = {b.box: b for b in overview_level(model, outer).boxes}
    assert set(boxes) == {item_id("x1"), item_id("k1"), item_id("k2"), nested}
    assert (boxes[item_id("x1")].kind, boxes[item_id("x1")].terminals) == (ItemKind.STRIP, 2)
    assert boxes[nested].kind is None
    assert boxes[item_id("k1")].kind is ItemKind.DEVICE


def test_lines_are_lifted_with_the_count_of_connections() -> None:
    """K1's two wires to the strip are one line of count 2; the jumper inside the strip is none; the
    mate K1 to the nested unit is its own line beside the wire."""
    model, outer, nested = unit_plant()
    level = overview_level(model, outer)
    counts = {
        (frozenset((line.ref.a, line.ref.b)), line.ref.kind.value): line.count
        for line in level.lines
    }
    assert counts == {
        (frozenset((item_id("x1"), item_id("k1"))), "wire"): 2,
        (frozenset((item_id("x1"), item_id("k2"))), "wire"): 1,
        (frozenset((item_id("k1"), item_id("k2"))), "wire"): 2,
        (frozenset((item_id("k1"), nested)), "wire"): 1,
        (frozenset((item_id("k1"), nested)), "mate"): 1,
    }
    (pair,) = (
        one for one in level.lines if {one.ref.a, one.ref.b} == {item_id("x1"), item_id("k1")}
    )
    assert len(pair.conductors) == 2


def test_a_connection_to_an_outside_item_is_a_stub_at_the_inside_box() -> None:
    """X1's external wire to B1 leaves the level: one stub on the strip, named by its far end."""
    model, outer, _ = unit_plant()
    (stub,) = overview_level(model, outer).stubs
    assert (stub.box, stub.count) == (item_id("x1"), 1)
    assert "B1" in stub.far


def test_an_open_strip_lists_terminals_in_strip_order_with_their_lines() -> None:
    """L1 then L2; L2 reaches K1 and K2, L1 reaches K1, and neither lists the outside wire."""
    model, outer, _ = unit_plant()
    view = strip_view(model, item_id("x1"), outer)
    assert [t.item for t in view.terminals] == [item_id("x1", "t1"), item_id("x1", "t2")]
    ends = [sorted(str(one.ref.b.value) for one in t.lines) for t in view.terminals]
    assert [len(e) for e in ends] == [1, 2]


def test_an_open_strip_keeps_the_stubs_its_terminals_wire_to() -> None:
    """L1's external wire to B1 is a stub at L1; L2, wired inside the unit only, has none."""
    model, outer, _ = unit_plant()
    by_terminal = {t.terminal: t.stubs for t in strip_stubs(model, item_id("x1"), outer)}
    assert list(by_terminal) == [item_id("x1", "t1"), item_id("x1", "t2")]
    (stub,) = by_terminal[item_id("x1", "t1")]
    assert (stub.box, stub.count) == (item_id("x1", "t1"), 1)
    assert "B1" in stub.far
    assert by_terminal[item_id("x1", "t2")] == ()


def test_open_strips_are_the_strip_boxes_that_hold_terminals() -> None:
    """The one strip of the plant holds two terminals; no device or unit box opens."""
    model, outer, _ = unit_plant()
    assert open_strips(overview_level(model, outer)) == (item_id("x1"),)
