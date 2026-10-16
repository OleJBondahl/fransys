"""The listing's item order ends on the unit-local key, so a tie is build-path free (model-0309)."""

import dataclasses

from fransys_model.derive.baseline_codec import differing_sections, dumps, matches
from fransys_model.derive.baseline_item_order import item_order
from fransys_model.derive.rows_baseline import BaselineItem, BaselineUnit, Listing


def _row() -> BaselineItem:
    return BaselineItem(
        designation="-X1:bar",
        mpn="M",
        manufacturer="Demo",
        installed=True,
        external=False,
        position=None,
        parent="-X1",
    )


def test_rows_tied_on_every_field_order_by_key_whatever_the_input_order() -> None:
    """Breaks if the key is dropped from the sort: the input order would then survive."""
    a, b = (_row(), "x1/bar a"), (_row(), "x1/bar b")
    assert sorted([b, a], key=item_order) == [a, b]
    assert sorted([a, b], key=item_order) == [a, b]


def _listing(*rows: BaselineItem) -> Listing:
    unit = BaselineUnit(name="u", version=1, revision=1, interface="")
    return Listing(unit=unit, items=rows, units=(), boundary=(), conductors=(), mates=(), nets=())


def _keyed(key: str, mpn: str = "M") -> BaselineItem:
    return dataclasses.replace(_row(), key=key, mpn=mpn)


def test_stored_ties_in_non_key_order_compare_equal() -> None:
    """Breaks if the compare keeps the stored order: the swapped tie would then differ."""
    fresh = _listing(_keyed("x1/bar a"), _keyed("x1/bar b"))
    stored = _listing(_keyed("x1/bar b"), _keyed("x1/bar a"))
    assert differing_sections(stored, fresh) == ()
    assert matches(dumps(stored), fresh)


def test_a_real_item_difference_still_differs() -> None:
    fresh = _listing(_keyed("x1/bar a"), _keyed("x1/bar b"))
    stored = _listing(_keyed("x1/bar b", mpn="OTHER"), _keyed("x1/bar a"))
    assert differing_sections(stored, fresh) == ("items",)
