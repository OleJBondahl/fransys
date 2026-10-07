"""DD-REPLICA-SET (layout-0076): a terminal replica never leaves its terminal's drawing set.

A strip terminal `T` in group GA at location FIELD, a connector `k` in group GB at location CAB,
wired `k.1` to `T.inner`, and `T` wired elsewhere too (a cable core from a device at a third
location to `T.external`). FIELD and CAB are under one top location BOX. `replicate_terminals` used
to ask for a replica of `T` beside `k` (another drawing set), so the wire was drawn there, `links`
cut nothing, and `T`'s home in its own set kept an inner port that nothing covered:
`CONNECTION_NOT_DRAWN`. Now nothing is asked across locations and `links` draws the wire with a
marker pair. With FIELD and CAB at the top level (C21) it is a pair of off stubs.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity
from fransys_model.layout import LinkMarker, StarKind, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Terminal across locations",
    "number": "P-1010",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build(*, under_box: bool):
    """The design of the module docstring; FIELD and CAB under location BOX when `under_box`,
    else two top-level locations."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    scope = d.scope("in", at=d.location("BOX", "Box")) if under_box else d.scope("in")
    field, cab = scope.location("FIELD", "Field side"), scope.location("CAB", "Interior")
    terminal = scope.strip("X1", at=field).terminal("DEMO-TB-2.5", group=d.group("GA", "Group A"))
    k = scope.item("DEMO-CONN-2P", name="k", at=cab, group=d.group("GB", "Group B"))
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(k.fn("x1")["1"], terminal.inner)
    frame = d.location("FRAME", "Frame")
    dev = d.item("DEMO-CONN-2P", name="dev", at=frame).fn("x1")
    d.cable("DEMO-CBL-4G1.5", tag="W1", length_mm=5000, at=frame).core(
        1, dev["1"], terminal.function["external"]
    )
    return fr.build(parts, d.draft(), layout_trigger_document())


def _ends_of_the_wire(model) -> list[LinkMarker]:
    """The markers on `T.inner` and on `k`'s pin 1: the two ends of the wire between them."""
    found = []
    for marker in layout_of(model, LinkMarker).values():
        port = ports(model)[marker.port]
        function = functions(model)[port.function]
        if (function.key[-2:] == ("fn", "terminal") and port.name == "internal") or (
            function.name == "x1" and port.name == "1" and "k" in function.key
        ):
            found.append(marker)
    return found


def test_a_terminal_wired_across_two_leaf_locations_gets_a_marker_pair_and_no_replica() -> None:
    """0 ERROR; the terminal stands once in its own set; the wire k.1 - T.inner ends in a pair of
    markers that name each other, no star kind on either."""
    # UNDO: stages/replicate.py, `replicate_terminals`: `served.drawing_set_key !=
    #     terminal_home.drawing_set_key` -> `served.unit != terminal_home.unit` (the replica
    #     comes back beside k, and T's inner port in its own set has no cover)
    result = _build(under_box=True)
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    model = result.model
    terminals = [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if functions(model)[p.function].key[-2:] == ("fn", "terminal")
    ]
    assert len(terminals) == 1
    first, second = _ends_of_the_wire(model)
    assert (first.partner, second.partner) == (second.id, first.id)
    assert first.star is None
    assert second.star is None
    assert first.page != second.page


def test_the_same_wire_across_top_level_locations_is_a_pair_of_off_stubs() -> None:
    """Control (C21): two top-level locations draw the wire with off stubs, and it builds."""
    # No UNDO: a control that passes on the base.
    result = _build(under_box=False)
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    ends = _ends_of_the_wire(result.model)
    assert len(ends) == 2
    assert {m.star for m in ends} == {StarKind.OFF}
