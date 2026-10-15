"""A box's lines never overprint, each target has its own line.

A marker box is one text height wide per line (a vertical box) or high per line. Where several
markers stand at one pin, one box holds all their lines (`stand.joined_box`): sized for the sum,
never for one marker's own. Built through the `fransys` facade on `test_dd_star_per_set`'s PE
net (three terminals of two strips, the hub wired to the others) and, for the shared pin, on a
relay hub with two far ends in another location: read from `layout.*` records and `marker_text`.
"""

import importlib.util
from collections import defaultdict
from pathlib import Path

import fransys as fr
import pytest
from _model_build_cover import layout_trigger_document

from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, layout_of


def _sibling(name: str):
    """The root test module `name`, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _star_per_set():
    """`test_dd_star_per_set`, loaded by path."""
    return _sibling("test_dd_star_per_set")


def _pins(model):
    """The markers by pin: `(page, x, y, stub_extra)` to the markers standing there."""
    found = defaultdict(list)
    for marker in layout_of(model, LinkMarker).values():
        found[marker.page, marker.x, marker.y, marker.stub_extra].append(marker)
    return found


def _device_hub():
    """Relay K0's A1 wired to K4-K6 here and to K1, K2 in another location: its pin holds the
    reference and one stub per far end (model-0220: a terminal hub is drawn as copies, so the
    shared pin comes from a device hub)."""
    gap = _sibling("test_dd_gap_rules")
    parts, d, c1, grp = gap._design()
    wire = d.wiring(colour="BU", gauge="0.5")
    hub = d.item(gap._RELAY, tag="K0", at=c1, group=grp).fn("coil")["A1"]
    for tag, pin in (("K4", "A1"), ("K5", "A1"), ("K6", "A2")):
        wire(hub, d.item(gap._RELAY, tag=tag, at=c1, group=grp).fn("coil")[pin])
    far = d.location("FLD", "Field")
    for tag in ("K1", "K2"):
        wire(hub, d.item(gap._RELAY, tag=tag, at=far, group=grp).fn("coil")["A1"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_a_box_holds_a_line_for_every_target_at_its_pin(fill: int) -> None:
    """Each lead's text has as many lines as its box is wide for, and a pin's lines are all of
    its markers' own: no box is drawn narrower than the targets it names, so none overprints.
    With `fill` 1 the PE net is drawn as wires, so the unit's set has only one-marker pins
    (the boxes of the fixture's blue nets) and no pin to share; `fill` 3 uses a relay hub whose
    pin holds a reference and two stubs (model-0220: a terminal hub is copies, with no marker)."""
    # UNDO: stages/texts/stand.py `joined_box`: `sum(b.width for b in boxes) - trim`
    #     -> `first.width` (other-page)
    if fill == 1:
        fixture = _star_per_set()
        model, _ = fixture._build(fixture._APART, fill=fill)
    else:
        model = _device_hub()
    height = profile_and_sheet(model)[0].text_height
    shared = 0
    assert _pins(model)
    for markers in _pins(model).values():
        if not any(m.lead for m in markers):
            continue  # a far end's stub in the box of the reference's run (its pin holds no lead)
        (lead,) = [m for m in markers if m.lead]
        lines = marker_text(model, lead).split("\n")
        assert len(lines) * height <= (lead.width if lead.vertical else lead.height)
        if len(markers) > 1:
            shared += 1
            assert {(m.width, m.height) for m in markers} == {(lead.width, lead.height)}
            assert len(lines) >= len(markers)
    if fill != 1:
        assert shared, "the fixture has no pin with two markers"
