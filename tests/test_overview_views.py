"""The overview engine's folded views on the invented two-group unit (OVERVIEW-VIEWS P1).

Each test names what breaks it.
"""

import sys
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import fold_level, overview_levels, overview_view_rows
from fransys_model.layout import (
    OverviewBox,
    OverviewLine,
    OverviewMode,
    OverviewRef,
    OverviewRefKind,
    OverviewView,
    layout_of,
)

for _name in ("derive", "vocab"):
    _dir = str(Path(__file__).parent.parent / "packages" / "fransys-model" / "tests" / _name)
    if _dir not in sys.path:
        sys.path.append(_dir)  # `--import-mode=importlib` leaves test folders off `sys.path`

from fold_builders import CTL_BOX, SUP_BOX, fold_plant  # noqa: E402 -- needs the paths added above


@cache
def _laid() -> tuple[Any, Any, Any]:
    model, unit, _ = fold_plant()
    out, findings = lay_out_overview(model)
    return model, unit, (out, findings)


def _views(**where: Any) -> list[Any]:
    out = _laid()[2][0]
    found = layout_of(out, OverviewView).values()
    return sorted(
        (v for v in found if all(getattr(v, k) == w for k, w in where.items())),
        key=lambda v: v.key,
    )


def _parts(view: Any) -> tuple[list[Any], list[Any]]:
    out = _laid()[2][0]
    boxes = [b for b in layout_of(out, OverviewBox).values() if b.view == view.id]
    lines = [ln for ln in layout_of(out, OverviewLine).values() if ln.view == view.id]
    return boxes, lines


def test_the_two_group_unit_writes_no_finding_and_every_mode_view() -> None:
    """Breaks if a folded view fails the four checks (A2) or a mode view is not written."""
    _, unit, (_, findings) = _laid()
    assert findings == ()
    modes = {(v.mode, v.level is not None) for v in _views(unit=unit)}
    assert modes == {
        (OverviewMode.PLAIN, False),
        (OverviewMode.GROUPS, False),
        (OverviewMode.SEE_THROUGH, False),
        (OverviewMode.SEE_THROUGH, True),
        (OverviewMode.LANES, False),
    }


def test_the_groups_view_has_the_fold_boxes_and_one_box_per_far_end() -> None:
    """Breaks if a group box is dropped, or a far end is drawn twice or not at all."""
    model, unit, _ = _laid()
    (view,) = _views(unit=unit, mode=OverviewMode.GROUPS, open=None)
    fold = fold_level(model, unit)
    boxes, lines = _parts(view)
    level = [b for b in boxes if b.stub_of is None]
    assert level
    assert {b.ref for b in level} == {b.key for b in fold.boxes}
    stubs = [b for b in boxes if b.stub_of is not None]
    assert len({(b.stub_of, b.ref) for b in stubs}) == len(stubs)
    assert len(stubs) == len({(s.box, s.end) for s in fold.stubs})
    assert len(lines) == len(fold.lines) + len({(s.box, s.end, s.kind, s.via) for s in fold.stubs})


def test_each_group_level_draws_the_pass_through_line_with_its_strip() -> None:
    """Breaks if a pass-through line is dropped, or a group level is missing."""
    model, unit, _ = _laid()
    groups = _views(unit=unit, mode=OverviewMode.SEE_THROUGH)
    opened = [v for v in groups if v.level is not None and v.open is None]
    assert {v.level for v in opened} == {SUP_BOX, CTL_BOX, OverviewRef(kind=OverviewRefKind.STRIPS)}
    sup = next(v for v in opened if v.level == SUP_BOX)
    expected = fold_level(model, unit, SUP_BOX)
    _, lines = _parts(sup)
    assert {ln.strip for ln in lines if ln.strip} == {ln.strip for ln in expected.lines if ln.strip}
    assert any(ln.strip is not None for ln in lines)


def test_a_folded_stub_with_members_is_never_placed_open() -> None:
    """Breaks if a far-unit fold has a view of its own (B2): its members are rows of its box."""
    model, unit, _ = _laid()
    fold = fold_level(model, unit)
    folded = next(s for s in fold.stubs if s.members and s.end.kind is OverviewRefKind.UNIT)
    assert _views(unit=unit, mode=OverviewMode.GROUPS, open=folded.end) == []
    assert len(_views(unit=unit, mode=OverviewMode.GROUPS, open=None)) == 1
    (rows,) = (
        v
        for v in overview_view_rows(model, unit)
        if v.mode is OverviewMode.GROUPS and v.open is None
    )
    (box,) = [b for b in rows.boxes if b.key.ref == folded.end and b.key.at == folded.box]
    assert [m.ref for m in box.members] == [m.end for m in folded.members]
    assert isinstance(folded.end, OverviewRef)


@pytest.mark.parametrize("mode", [OverviewMode.GROUPS, OverviewMode.SEE_THROUGH])
def test_no_view_of_the_unit_has_a_line_off_its_boxes(mode: OverviewMode) -> None:
    """Breaks if a line names a box record that is not in its view."""
    _, unit, _ = _laid()
    for view in _views(unit=unit, mode=mode):
        boxes, lines = _parts(view)
        ids = {b.id for b in boxes}
        assert all(ln.a in ids and ln.b in ids for ln in lines)


def test_one_engine_run_derives_each_units_level_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Breaks if a view derives its unit's level again (A16, O25): the derive runs once per unit."""
    model, _, _ = fold_plant()
    calls: list[Any] = []
    real = overview_levels._unit_level
    monkeypatch.setattr(
        overview_levels, "_unit_level", lambda m, unit: (calls.append(unit), real(m, unit))[1]
    )
    overview_levels.overview_level.cache_clear()
    out, _ = lay_out_overview(model)
    laid = {v.unit for v in layout_of(out, OverviewView).values() if v.unit is not None}
    assert len(laid) >= 1
    assert sorted(calls) == sorted(laid)


def test_each_level_that_lists_a_strip_has_a_view_with_that_strip_open() -> None:
    """O5: a group level, the strips level and the all-devices level open every strip they list.

    Breaks if `_fold_views` drops the per-strip views. The groups view opens none.
    """
    model, unit, _ = _laid()
    strip_open = [v for v in _views(unit=unit) if v.open and v.open.kind is OverviewRefKind.ITEM]
    assert strip_open
    assert OverviewMode.GROUPS not in {v.mode for v in strip_open}
    sup = {v.open.item for v in strip_open if v.level == SUP_BOX}
    assert sup == {n.strip for n in fold_level(model, unit, SUP_BOX).strips}
    strips = OverviewRef(kind=OverviewRefKind.STRIPS)
    assert {v.open.item for v in strip_open if v.level == strips} == {
        n.strip for n in fold_level(model, unit, strips).strips
    }
    assert all(_parts(view)[0] for view in strip_open)
