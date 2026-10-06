"""D13: a label's width and height are the box the stage measured once.

`Label.width` and `Label.height` are written from the placed label's box, and render draws from
them and measures nothing. Text kinds are measured from the text render prints (`label_text`).
"""

from functools import cache
from typing import TYPE_CHECKING

import pytest
from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.write_keys import write_keys
from fransys_layout.engines.schematic.write import write_layout
from fransys_layout.geometry import text_width
from fransys_layout.stages import pagerun
from fransys_layout.stages.sizing import label_boxes
from fransys_model.derive.drawing_text import label_text
from fransys_model.kernel import freeze
from fransys_model.layout import Label, LabelKind, default_profile, layout_of

if TYPE_CHECKING:
    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_model.kernel import Model

_PROFILE = default_profile()
_ONE_LINE = (LabelKind.TAG, LabelKind.MARKING)


@cache
def _run() -> tuple[Model, StageResults, list[dict]]:
    """The laid-out cabinet, its stage results and what `label_boxes` measured per page."""
    model = freeze(build_cabinet())
    inputs = read_inputs(model)
    measured: list[dict] = []
    original = pagerun._place_page

    def spy(page, **joins):
        measured.append(label_boxes(page.drawn, page.requests, page.inputs.profile))
        return original(page, **joins)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pagerun, "_place_page", spy)
        results, _ = stage_results(model, inputs)
    return write_layout(model, results, write_keys(model)), results, measured


def _labels() -> list[Label]:
    return list(layout_of(_run()[0], Label).values())


def test_the_cabinet_has_every_kind_the_check_covers() -> None:
    """The text kinds are present, and a contact image too (C19)."""
    kinds = {label.kind for label in _labels()}
    assert {LabelKind.TAG, LabelKind.MARKING} <= kinds
    assert any(label.slot == "contacts" for label in _labels())


def test_every_label_has_a_positive_box() -> None:
    assert _labels()
    for label in _labels():
        assert label.width > 0, label.key
        assert label.height > 0, label.key


def test_a_label_carries_no_ext_size() -> None:
    """The keys `Label.width` and `Label.height` replace are no longer written."""
    for label in _labels():
        assert "w" not in label.ext, label.key
        assert "h" not in label.ext, label.key


def test_a_one_line_text_label_is_one_text_height_tall() -> None:
    lines = [label for label in _labels() if label.kind in _ONE_LINE]
    assert lines
    for label in lines:
        assert label.height == _PROFILE.text_height, label.key


# The cabinet has no VALUE label, so VALUE is not listed (a listed kind that skips proves nothing).
_PRINTED = (LabelKind.TAG, LabelKind.MARKING, LabelKind.CROSS_REFERENCE)


@pytest.mark.parametrize("kind", _PRINTED, ids=lambda kind: kind.name)
def test_a_text_label_is_as_wide_as_the_text_render_prints(kind: LabelKind) -> None:
    model = _run()[0]
    # a contact image (slot "contacts") is a two-column table sized by its own rule (C19)
    found = [label for label in _labels() if label.kind is kind and label.slot != "contacts"]
    if not found:
        pytest.skip(f"the cabinet has no {kind.name} label")
    for label in found:
        printed = label_text(model, label)
        assert label.width == text_width(printed, height=_PROFILE.text_height), (
            label.key,
            printed,
        )


def test_label_boxes_agree_with_the_written_label_widths() -> None:
    """Each (function, slot) box `label_boxes` measured is some written label's width there."""
    model, results, measured = _run()
    owner = {port.port: one.function for one in results.drawn for port in one.ports}
    written: dict = {}
    for label in layout_of(model, Label).values():
        if label.kind is LabelKind.TAG:
            key = (label.function, label.slot)
        elif label.kind is LabelKind.MARKING:
            assert label.port is not None
            key = (owner[label.port], label.slot)
        else:
            continue
        written.setdefault(key, set()).add(label.width)
    entries = [
        (function, slot, box)
        for boxes in measured
        for function, slots in boxes.items()
        for slot, box in slots
    ]
    assert entries
    for function, slot, box in entries:
        assert box.width in written.get((function, slot), set()), (function, slot, box.width)
