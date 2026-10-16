"""overview-0011: a diff row marks the nearest drawn box or the line it names; the rest is listed.

The system listing of the invented unit has item -B1, the nested unit `cab` and one conductor
from -B1 to the strip inside it. The views are built by hand: the boxes the case needs.
"""

import dataclasses

from overview_builders import item_id, unit_plant

from fransys_model.derive import (
    DiffMark,
    DiffRest,
    ViewBox,
    ViewLine,
    ViewRows,
    baseline,
    diff_marks,
    diff_rest,
)
from fransys_model.derive.baseline_listing import listing
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef, OverviewRefKind

_GHOST = "-ZZ9"


def _key(*key: str) -> BoxKey:
    return BoxKey(ref=OverviewRef(kind=OverviewRefKind.ITEM, item=item_id(*key)))


def _view(*keys: BoxKey, lines: tuple[ViewLine, ...] = ()) -> ViewRows:
    boxes = tuple(ViewBox(key=k, lines=(str(n),), dashed=False) for n, k in enumerate(keys))
    return ViewRows(
        unit=None, level=None, mode=OverviewMode.PLAIN, open=None, boxes=boxes, lines=lines
    )


def _full():
    model, _outer, _nested = unit_plant(project=True)
    return model, listing(model, None)


def test_an_added_item_marks_its_box_as_added() -> None:
    """Breaks if the row marks another box, or its kind is not the row's."""
    model, full = _full()
    less = dataclasses.replace(full, items=())
    view = diff_marks(model, _view(_key("k1"), _key("b1")), baseline.diff(less, full))
    assert view.marks == (DiffMark(on_line=False, at=1, status="added"),)
    assert view.shown == (0,)


def test_a_conductor_marks_the_line_joining_its_ends_and_no_box() -> None:
    """Breaks if the row marks a box, or a line that does not join its two ends."""
    model, full = _full()
    less = dataclasses.replace(full, conductors=())
    keys = (_key("b1"), _key("x1"))
    line = ViewLine(a=keys[0], b=keys[1], kind="wire", via=None, strip=None, text="")
    view = diff_marks(model, _view(*keys, lines=(line,)), baseline.diff(less, full))
    assert view.marks == (DiffMark(on_line=True, at=0, status="added"),)


def _removed(model_full):
    model, full = model_full
    ghost = dataclasses.replace(full.items[0], designation=_GHOST, parent="-B1", key="ghost")
    old = dataclasses.replace(full, items=(*full.items, ghost))
    return model, baseline.diff(old, full)


def test_a_removed_item_marks_its_first_drawn_ancestor_as_changed() -> None:
    """Breaks if a removed row marks nothing, or marks its ancestor as removed (overview-0005)."""
    model, diff = _removed(_full())
    view = diff_marks(model, _view(_key("b1")), diff)
    assert view.marks == (DiffMark(on_line=False, at=0, status="changed"),)
    assert diff_rest(diff, [view]) == ()


def test_a_removed_item_with_no_drawn_ancestor_is_listed() -> None:
    """Breaks if the row is dropped when no view draws an ancestor."""
    model, diff = _removed(_full())
    view = diff_marks(model, _view(_key("k1")), diff)
    assert view.marks == ()
    assert diff_rest(diff, [view]) == (DiffRest(status="removed", text=_GHOST),)


def test_the_rest_lists_removed_then_added_then_changed_once_each() -> None:
    """Breaks if the kinds are not in that order, or a repeated row is printed twice."""
    _model, full = _full()
    item = full.items[0]
    changed = dataclasses.replace(item, mpn="NEW")
    ghost = dataclasses.replace(item, designation=_GHOST, key="ghost")
    old = dataclasses.replace(full, items=(item, ghost), units=(), conductors=())
    new = dataclasses.replace(full, items=(changed,))
    diff = baseline.diff(old, new)
    order = {"removed": 0, "added": 1, "changed": 2}
    kinds = [r.status for r in diff_rest(diff, [])]
    assert kinds == sorted(kinds, key=order.__getitem__)
    assert set(kinds) == set(order)
