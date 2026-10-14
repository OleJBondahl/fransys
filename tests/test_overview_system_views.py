"""The system level's location view and field-device view on the units example (OVERVIEW O9).

Each test names what breaks it.
"""

import sys
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_parts
from _model_build_cover import system_document

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _system_design

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive import field_devices, field_fold, location_fold, overview_view_rows
from fransys_model.layout import (
    OverviewBox,
    OverviewLine,
    OverviewMode,
    OverviewRefKind,
    OverviewView,
    layout_of,
)
from fransys_model.vocab.tables import items


@cache
def _laid() -> tuple[Any, Any]:
    parts = fransys_parts.load("demo_parts")
    design, _field1, _field2 = _system_design(parts)
    model = fr.build(parts, design.draft(), system_document()).model
    out, findings = lay_out_overview(model)
    return model, (out, findings)


def _views(mode: OverviewMode) -> list[Any]:
    out = _laid()[1][0]
    found = (v for v in layout_of(out, OverviewView).values() if v.unit is None and v.mode is mode)
    return sorted(found, key=lambda v: v.key)


def _boxes(view: Any) -> list[Any]:
    return [b for b in layout_of(_laid()[1][0], OverviewBox).values() if b.view == view.id]


def _lines(view: Any) -> list[Any]:
    return [ln for ln in layout_of(_laid()[1][0], OverviewLine).values() if ln.view == view.id]


def test_the_system_folds_write_no_finding() -> None:
    """Breaks if a fold view has a line through a box or an overlap (A2)."""
    assert _laid()[1][1] == ()


def test_the_location_view_has_a_box_per_place_and_a_line_per_pair_and_never_opens() -> None:
    """Breaks if a place box is missing or extra, or a place box opens (O9)."""
    fold = location_fold(_laid()[0])
    assert fold is not None
    (view,) = _views(OverviewMode.LOCATION)
    assert view.open is None
    boxes = _boxes(view)
    assert {b.ref.kind for b in boxes} == {OverviewRefKind.PLACE}
    assert sorted(b.ref.node.value if b.ref.node else "" for b in boxes) == sorted(
        b.place.value if b.place else "" for b in fold.boxes
    )
    assert len(_lines(view)) == len(fold.lines)


def test_the_field_view_folds_every_field_device_and_each_box_lists_its_devices() -> None:
    """A15: breaks if a device stays a box, a fold lacks member rows or a fold is placed open.

    The data of an open fold holds its member rows and no positions: the view has no open
    variant, and a member row is a reference and text only.
    """
    model = _laid()[0]
    devices = set(field_devices(model))
    folds = field_fold(model)
    (shut,) = _views(OverviewMode.FIELDS)
    assert shut.open is None
    shut_refs = {(b.ref.kind, b.ref.unit, b.ref.item) for b in _boxes(shut)}
    assert {i for _, _, i in shut_refs} & devices == set()
    assert {u for k, u, _ in shut_refs if k is OverviewRefKind.FIELDS} == {f.unit for f in folds}
    rows = {
        b.key.ref.unit: b.members
        for b in next(
            v for v in overview_view_rows(model, None) if v.mode is OverviewMode.FIELDS
        ).boxes
        if b.key.ref.kind is OverviewRefKind.FIELDS
    }
    for fold in folds:
        assert {m.ref.item for m in rows[fold.unit]} == set(fold.devices)
        assert all(m.lines for m in rows[fold.unit])


def test_the_field_fold_is_off_in_the_plain_system_view() -> None:
    """Breaks if the field-device fold is on by default (O9: off by default)."""
    model = _laid()[0]
    (plain,) = _views(OverviewMode.PLAIN)
    held = {b.ref.item for b in _boxes(plain)}
    assert set(field_devices(model)) <= held
    assert OverviewRefKind.FIELDS not in {b.ref.kind for b in _boxes(plain)}


def test_a_stub_names_the_root_item_of_its_far_end() -> None:
    """Breaks if a far terminal draws its own stub box instead of standing as its strip."""
    model, (out, _) = _laid()
    stubs = [b for b in layout_of(out, OverviewBox).values() if b.stub_of is not None]
    far = [b.ref.item for b in stubs if b.ref.item is not None]
    assert far
    assert all(items(model)[item].parent is None for item in far)
    ends = [(b.view, b.stub_of, b.ref) for b in stubs]
    assert len(ends) == len(set(ends))
