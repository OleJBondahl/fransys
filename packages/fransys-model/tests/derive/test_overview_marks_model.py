"""`diff_marks` (model-0197): which drawn box or line each `ListingDiff` row marks."""

import dataclasses
from collections import Counter

from overview_builders import item_id, unit_plant

from fransys_model.derive import OverviewLinkKind, baseline, diff_marks
from fransys_model.derive.baseline_designation import unit_designation


def _marks(**dropped: int):
    """The marks of the diff from the unit's listing less `dropped` rows to the full listing."""
    model, outer, nested = unit_plant()
    full = baseline.listing(model, outer)
    less = dataclasses.replace(
        full, **{name: getattr(full, name)[skip:] for name, skip in dropped.items()}
    )
    diff = baseline.diff(less, full)
    return model, outer, nested, diff, diff_marks(model, outer, diff)


def test_an_added_item_marks_the_box_holding_it() -> None:
    """A terminal's row marks its strip's box; K2's row marks K2."""
    model, outer, _ = unit_plant()
    full = baseline.listing(model, outer)
    wanted = {unit_designation(model, outer, item_id(key)): item_id(key) for key in ("k2", "x1")}
    rows = [r for r in full.items if r.designation in wanted]
    assert len(rows) == 2
    for row in rows:
        less = dataclasses.replace(full, items=tuple(r for r in full.items if r != row))
        diff = baseline.diff(less, full)
        (mark,) = diff_marks(model, outer, diff)
        assert mark.status == "added"
        assert mark.boxes == (wanted[row.designation],)


def test_each_added_conductor_marks_the_line_carrying_it() -> None:
    """Every conductor row marks its lifted line; the jumper inside the strip marks none."""
    model, outer, nested = unit_plant()
    full = baseline.listing(model, outer)
    marked = []
    for row in full.conductors:
        less = dataclasses.replace(full, conductors=tuple(r for r in full.conductors if r != row))
        (mark,) = diff_marks(model, outer, baseline.diff(less, full))
        assert mark.boxes == ()
        marked.append(frozenset(frozenset((ref.a, ref.b)) for ref in mark.lines))
    x1_k1 = frozenset({frozenset((item_id("x1"), item_id("k1")))})
    assert Counter(marked) == Counter(
        [
            x1_k1,
            x1_k1,
            frozenset({frozenset((item_id("x1"), item_id("k2")))}),
            frozenset({frozenset((item_id("k1"), nested))}),
            frozenset({frozenset((item_id("k1"), item_id("k2")))}),
            frozenset({frozenset((item_id("k1"), item_id("k2")))}),
            frozenset(),
        ]
    )


def test_an_added_mate_marks_the_mate_line_between_its_boxes() -> None:
    """The K1 to Z1 mate marks the mate line between K1 and the nested unit's box."""
    _, _, nested, _, marks = _marks(mates=1)
    (mark,) = marks
    (ref,) = mark.lines
    assert ref.kind is OverviewLinkKind.MATE
    assert {ref.a, ref.b} == {item_id("k1"), nested}


def test_a_removed_row_marks_nothing() -> None:
    """The new model holds nothing for a removed thing to point at."""
    model, outer, _ = unit_plant()
    full = baseline.listing(model, outer)
    more = dataclasses.replace(full, conductors=full.conductors[1:])
    diff = baseline.diff(full, more)
    (mark,) = diff_marks(model, outer, diff)
    assert (mark.status, mark.boxes, mark.lines) == ("removed", (), ())
