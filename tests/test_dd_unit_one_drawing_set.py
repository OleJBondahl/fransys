"""Per layout-0081, a unit is one drawing set, whatever locations it stands in.

One unit `u1` holds seven connectors `panel<i>` at an area FIELD, each wired to a connector `peer<i>`
at an area CAB. The unit's own items stand in two locations, so `partition` used to file them under
"""

from typing import Any

import fransys as fr
import fransys_parts
from _model_build_cover import cabinet_document, layout_trigger_document
from fransys_author.design import Design

from fransys_model.kernel import Severity
from fransys_model.layout import DrawingSet, Page, layout_of

_PROJECT: dict[str, Any] = {
    "title": "Unit drawing",
    "number": "P-1012",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_PAIRS = 60


def _build(*, in_unit: bool, nested: bool):
    """`_PAIRS` panel/peer pairs, panels at FIELD and peers at CAB; the pairs are the items of
    unit `u1` when `in_unit`, else top-level items. FIELD and CAB stand under a location BOX when
    `nested`, else they are two top-level siblings."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
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
    documents = (layout_trigger_document("u1"),) if in_unit else (cabinet_document(field), cabinet_document(cab))
    return fr.build(parts, d.draft(), *documents)


def _errors(result) -> list[str]:
    return [f.code for f in result.findings if f.severity is Severity.ERROR]


def _numbers(model, one: DrawingSet) -> list[int]:
    """The page numbers of the drawing set `one`, sorted."""
    return sorted(p.number for p in layout_of(model, Page).values() if p.drawing_set == one.id)


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
