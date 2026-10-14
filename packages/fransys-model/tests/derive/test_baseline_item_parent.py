"""A listed item names its parent (model-0212): written only when set, and the diff ignores it."""

import dataclasses

from fransys_model.derive.baseline import diff
from fransys_model.derive.baseline_codec import dumps, loads
from fransys_model.derive.rows import BaselineItem, BaselineUnit, Listing


def _row(designation: str, parent: str | None) -> BaselineItem:
    return BaselineItem(
        designation=designation,
        mpn="M",
        manufacturer="Demo",
        installed=True,
        external=False,
        position=None,
        parent=parent,
    )


def _listing(*rows: BaselineItem) -> Listing:
    unit = BaselineUnit(name="u", version=1, revision=1, interface="i")
    return Listing(unit=unit, items=rows, units=(), boundary=(), conductors=(), mates=(), nets=())


def test_a_parent_round_trips_and_a_root_writes_no_key() -> None:
    """Breaks if `parent` is lost on load, or written for a root (an older listing's bytes move)."""
    listing = _listing(_row("-X1", None), _row("-X1:1", "-X1"))
    text = dumps(listing)
    assert text.count('"parent"') == 1
    assert loads(text) == listing
    assert dumps(loads(text)) == text


def test_a_listing_without_the_key_loads_with_no_parent() -> None:
    """Breaks if `loads` requires the key an older listing never wrote."""
    text = dumps(_listing(_row("-X1", None)))
    assert '"parent"' not in text
    assert loads(text).items[0].parent is None


def test_the_diff_never_reports_a_parent_change() -> None:
    """Breaks if `parent` joins the compared item fields ."""
    before = _listing(_row("-X1:1", "-X1"))
    after = _listing(dataclasses.replace(before.items[0], parent="-X2"))
    assert diff(before, after).changes == ()


def test_a_moved_item_is_one_removed_and_one_added_row() -> None:
    """Breaks if a move to another parent reports anything but its changed designation."""
    before = _listing(_row("-X1:1", "-X1"))
    after = _listing(_row("-X2:1", "-X2"))
    assert [(c.change, c.subject, c.field) for c in diff(before, after).changes] == [
        ("removed", "-X1:1", ""),
        ("added", "-X2:1", ""),
    ]


def test_a_removed_item_lists_its_parents_then_the_listed_unit() -> None:
    """Breaks if the chain is out of order, skips a level, or leaves out the listed unit."""
    before = _listing(_row("-A", None), _row("-A:B", "-A"), _row("-A:B:1", "-A:B"))
    after = _listing(_row("-A", None))
    ancestry = diff(before, after).ancestry
    assert [(a.change, a.ancestors) for a in ancestry] == [
        (0, ("-A", "u 1.1")),
        (1, ("-A:B", "-A", "u 1.1")),
    ]


def test_a_root_a_missing_parent_and_a_loop_end_the_chain_safely() -> None:
    """Breaks if a root skips the listed unit, or a dangling parent or a loop raises or spins."""
    before = _listing(_row("-R", None), _row("-D", "-gone"), _row("-L1", "-L2"), _row("-L2", "-L1"))
    after = _listing()
    result = diff(before, after)
    found = {result.changes[a.change].subject: a.ancestors for a in result.ancestry}
    assert found == {
        "-R": ("u 1.1",),
        "-D": ("u 1.1",),
        "-L1": ("-L2", "u 1.1"),
        "-L2": ("-L1", "u 1.1"),
    }
