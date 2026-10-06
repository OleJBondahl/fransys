"""S20 M3 (ADDENDUM 19 fix 4): a box's lines never overprint, each target has its own line.

A marker box is one text height wide per line (a vertical box) or high per line. Where several
markers stand at one pin, one box holds all their lines (`stand.joined_box`): sized for the sum,
never for one marker's own. Built through the `fransys` facade on `test_dd_star_per_set`'s PE
net (three terminals of two strips, the hub wired to the others), whose unit set draws two
markers at one pin: read from `layout.*` records and `marker_text`.
"""

import importlib.util
from collections import defaultdict
from pathlib import Path

import pytest

from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, layout_of, profile_of


def _star_per_set():
    """`test_dd_star_per_set`, loaded by path (root tests are not a package)."""
    name = "test_dd_star_per_set"
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pins(model):
    """The markers by pin: `(page, x, y, stub_extra)` to the markers standing there."""
    found = defaultdict(list)
    for marker in layout_of(model, LinkMarker).values():
        found[marker.page, marker.x, marker.y, marker.stub_extra].append(marker)
    return found


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_a_box_holds_a_line_for_every_target_at_its_pin(fill: int) -> None:
    """Each lead's text has as many lines as its box is wide for, and a pin's lines are all of
    its markers' own: no box is drawn narrower than the targets it names, so none overprints.
    With `fill` 1 M12 draws the PE net as wires, so the unit's set has only one-marker pins
    (the boxes of the fixture's blue nets) and no pin to share; `fill` 3 puts two markers at
    three pins."""
    # UNDO: stages/texts/stand.py `joined_box`: `sum(b.width for b in boxes) - trim`
    #     -> `first.width` (other-page)
    fixture = _star_per_set()
    model, _ = fixture._build(fixture._APART, fill=fill)
    height = profile_of(model).text_height
    shared = 0
    assert _pins(model)
    for markers in _pins(model).values():
        (lead,) = [m for m in markers if m.lead]
        lines = marker_text(model, lead).split("\n")
        assert len(lines) * height <= (lead.width if lead.vertical else lead.height)
        if len(markers) > 1:
            shared += 1
            assert {(m.width, m.height) for m in markers} == {(lead.width, lead.height)}
            assert len(lines) >= len(markers)
    if fill != 1:
        assert shared, "the fixture has no pin with two markers"
