"""The parts tree is the containment tree: units, then items, strips last (O12)."""

from fold_builders import fold_plant
from overview_builders import item_id

from fransys_model.derive import overview_tree
from fransys_model.derive.instance_tag import unit_tag
from fransys_model.derive.lookups import unit_chain
from fransys_model.vocab.tables import units


def _children(rows, parent):
    return [r for r in rows if r.parent == parent]


def test_units_come_before_items_and_strips_last_under_a_unit() -> None:
    """Under -U1: the nested unit -U2, then the devices, then the strips -X1, -X2, -X9."""
    model, outer, _far = fold_plant()
    rows = overview_tree(model)
    top = next(i for i, r in enumerate(rows) if r.unit == outer)
    kids = _children(rows, top)
    labels = [r.label for r in kids]
    assert kids[0].unit is not None
    assert labels[-3:] == ["-X1", "-X2", "-X9"]
    assert {"-D1", "-K1", "-K2", "-P1"} <= set(labels[1:-3])


def test_a_terminal_hangs_under_its_strip_and_rows_print_relative_to_their_unit() -> None:
    """-X1:L:1 under -X1 under -U1; the item of -U2 reads -Z1, not -U1-U2-Z1."""
    model, outer, _far = fold_plant()
    rows = overview_tree(model)
    by_label = {r.label: (i, r) for i, r in enumerate(rows) if r.item is not None}
    x1 = by_label["-X1"][0]
    assert {r.label for r in _children(rows, x1)} == {"-X1:L:1", "-X1:L:2", "-X1:L:3"}
    up = by_label["-Z1"][1].parent
    assert up is not None
    assert rows[up].unit is not None
    assert rows[up].unit != outer


def test_every_item_has_one_row_and_no_row_starts_with_an_opened_units_tag() -> None:
    """A3 for the tree: breaks if a row prints the absolute name of its unit's items."""
    model, _outer, _far = fold_plant()
    rows = overview_tree(model)
    items_seen = [r.item for r in rows if r.item is not None]
    assert len(items_seen) == len(set(items_seen))
    assert item_id("k1") in items_seen
    for i, row in enumerate(rows):
        opened, at = [], row.parent
        while at is not None:
            held = rows[at].unit
            if held is not None:
                opened += [unit_tag(model, u) for u in unit_chain(model, held)]
            at = rows[at].parent
        wrong = [t for t in opened if t and row.label.startswith(f"-{t}-")]
        assert not wrong, (i, row.label)
    assert units(model)
