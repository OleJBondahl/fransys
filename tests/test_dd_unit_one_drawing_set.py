"""DD-UNIT-SET (layout-0081, LD6): a unit is one drawing set, whatever locations it stands in.

One unit `u1` holds six connectors `panel<i>` at an area FIELD, each wired to a connector `peer<i>`
at an area CAB. The unit's own items stand in two locations, so `partition` used to file them under
`(unit, FIELD)` and `(unit, CAB)`: two drawing sets, page numbers restarting at 1, and a wire
between them a marker pair with a `+CAB` prefix. Now the unit is ONE `layout.drawing_set`, its
pages are numbered straight through, and a wire cut between two of its pages is a marker pair
with the plain `/page.column` text. The set's location is `derive.designation.unit_location`: the
common parent BOX when FIELD and CAB are nested under it, none when they are two top-level
siblings built alone. The control puts the same items at the top level (no unit): locations still
split the drawing sets there.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

import re
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import system_document

from fransys_model.derive import unit_release
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import Severity
from fransys_model.layout import DrawingSet, LinkMarker, Page, layout_of
from fransys_model.vocab.tables import aspect_nodes, units

_PROJECT: dict[str, Any] = {
    "title": "Unit drawing",
    "number": "P-1012",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_PAIRS = 6
_PLAIN_POSITION = re.compile(r"#\d+-p\d+:\d+[A-Z]")


def _build(*, in_unit: bool, nested: bool):
    """`_PAIRS` panel/peer pairs, panels at FIELD and peers at CAB; the pairs are the items of
    unit `u1` when `in_unit`, else top-level items. FIELD and CAB stand under a location BOX when
    `nested`, else they are two top-level siblings."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    scope = d.scope("s", at=d.location("BOX", "Box")) if nested else d.scope("s")
    if in_unit:
        scope = scope.unit("u1", revision=1, interface="1")
        scope.revision(1, date="2026-01-01", text="First release", created="XX")
    field, cab = scope.location("FIELD", "Field side"), scope.location("CAB", "Interior")
    wire = d.wiring(colour="BU", gauge="0.5")
    for i in range(_PAIRS):
        panel = scope.item("DEMO-CONN-2P", name=f"panel{i}", at=field)
        peer = scope.item("DEMO-CONN-2P", name=f"peer{i}", at=cab)
        wire(panel.fn("x1")["1"], peer.fn("x1")["1"])
    return fr.build(parts, d.draft(), system_document())


def _errors(result) -> list[str]:
    return [f.code for f in result.findings if f.severity is Severity.ERROR]


def _numbers(model, one: DrawingSet) -> list[int]:
    """The page numbers of the drawing set `one`, sorted."""
    return sorted(p.number for p in layout_of(model, Page).values() if p.drawing_set == one.id)


@pytest.mark.parametrize("nested", [True, False])
def test_a_unit_in_two_locations_is_one_drawing_set_with_straight_page_numbers(nested) -> None:
    """Exactly one `layout.drawing_set` has `unit == u1`, and its pages run 1..n with no restart,
    n > 1 so a restart could show. Its location is the unit's own: BOX when the two areas are
    nested under it, none when they are top-level siblings."""
    # UNDO: stages/types.py, `Column.drawing_set_key`: the unit branch returns
    #     `(self.unit, self.location)` again (two sets of u1, numbers restart at 1)
    result = _build(in_unit=True, nested=nested)
    assert _errors(result) == []
    model = result.model
    (u1,) = (unit.id for unit in units(model).values() if unit_release(model, unit.id).name == "u1")
    own = [s for s in layout_of(model, DrawingSet).values() if s.unit == u1]
    assert len(own) == 1
    numbers = _numbers(model, own[0])
    assert len(numbers) > 1
    assert numbers == list(range(1, len(numbers) + 1))
    box = [n.id for n in aspect_nodes(model).values() if n.label == "BOX"]
    assert own[0].location == (box[0] if nested else None)


def test_a_cut_wire_inside_a_unit_has_plain_marker_text_and_no_unlocated_warning() -> None:
    """Layout-0078's cut stands between two pages of the unit's one set: `#n-p<page>:<col><row>`,
    no `+location` prefix, and `LINK_PARTNER_UNLOCATED` is not raised. (Two top-level sibling
    areas of one unit draw no off stub between them either: `offstubs.crosses_location`
    compares drawing-set keys, `tests/test_dd_cut_end.py` v3.)"""
    # UNDO: as above
    result = _build(in_unit=True, nested=True)
    model = result.model
    markers = layout_of(model, LinkMarker).values()
    assert markers
    assert all(_PLAIN_POSITION.fullmatch(marker_text(model, m)) for m in markers)
    assert "LINK_PARTNER_UNLOCATED" not in {f.code for f in result.findings}


def test_the_same_items_at_the_top_level_are_still_one_drawing_set_per_location() -> None:
    """Control: no unit, so FIELD and CAB are two drawing sets, each numbering from 1."""
    # No UNDO: a control that passes on the base.
    result = _build(in_unit=False, nested=True)
    assert _errors(result) == []
    model = result.model
    sets = layout_of(model, DrawingSet)
    assert {s.unit for s in sets.values()} == {None}
    assert len(sets) == 2  # FIELD and CAB
    for one in sets.values():
        numbers = _numbers(model, one)
        assert numbers == list(range(1, len(numbers) + 1))
