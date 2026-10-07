"""Decision model-0071, part 2 spec acceptance 3: a device with connectors X1 and X2, end to end.

The demo part `DEMO-IO-2X` has two connector functions `x1` and `x2`, marked `X1` and `X2`. The
item `A1` at `+B` is wired from two plugs `P1` and `P2` at `+A` by one cable `-W1`, core 1 to
`A1`'s `X1` pin 1 and core 2 to its `X2` pin 1. Before the rule both pins printed `-A1:1`, the two
off stubs on the `+A` side read one text for two different far ends, and the layout raised
`LayoutError`. Every test reads the text the pipeline prints (connector list, drawn pin tags, stub
texts), never a private name.

Can-fail: with `connector_segment` (`fransys_model.derive.designation`) returning `""`, the
build raises `LayoutError` ("the off stub text ... names two different far ends or carriers")
inside `_build`, and every test here fails on that line: a test id, not a collection error.
"""

import functools
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document
from fransys_reports import connectors_csv

from fransys_model.derive import item_designation
from fransys_model.derive.drawing_text import label_text, marker_text
from fransys_model.derive.queries import connector_rows
from fransys_model.kernel import Severity
from fransys_model.layout import Label, LabelKind, LinkMarker, StarKind, layout_of
from fransys_model.vocab.tables import functions, items, ports

_PROJECT: dict[str, Any] = {
    "title": "Two connectors",
    "number": "P-1071",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_ARROW = "\N{RIGHTWARDS ARROW}"


@functools.cache
def _build():
    """The build result; cached so the four tests share one build, called inside each test."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    cabinet, field = d.location("A", "Cabinet"), d.location("B", "Field")
    group = d.group("G", "Pump")
    a1 = d.item("DEMO-IO-2X", tag="A1", at=field, group=group)
    p1 = d.item("DEMO-CONN-2P", tag="P1", at=cabinet, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", at=cabinet, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", tag="W1")
    cable.core(1, p1["1"], a1.fn("x1")["1"])
    cable.core(2, p2["1"], a1.fn("x2")["1"])
    return fr.build(parts, d.draft(), layout_trigger_document())


def _a1(model):
    return next(i for i in items(model).values() if item_designation(model, i.id) == "A1")


def test_the_build_completes_and_carries_no_error_finding() -> None:
    """(a) The two connectors of one device build: no `LayoutError`, no ERROR finding."""
    # UNDO: fransys_model/derive/designation.py: `connector_segment` `return f"-{label}"` ->
    #   `return ""` (the build raises `LayoutError` on the colliding off stubs, inside `_build`)
    result = _build()
    severities = {finding.severity for finding in result.findings}
    assert Severity.ERROR not in severities
    assert severities <= {Severity.WARNING, Severity.INFO}
    assert len(layout_of(result.model, LinkMarker)) == 4  # one off stub per plug pin and per A1 pin


def test_the_connector_list_names_each_connector_of_the_device_behind_its_tag() -> None:
    """(b) `connector_rows` and the CSV of the connector list print `-A1-X1` and `-A1-X2`."""
    # UNDO: fransys_model/derive/designation.py: `connector_designation` `return
    #   printed_designation(model, item, unit=unit) + segment` -> `return printed_designation(model,
    #   item, unit=unit)` (both rows read `-A1`)
    model = _build().model
    rows = connector_rows(model, _a1(model).id)
    assert [row.designation for row in rows] == ["-A1-X1", "-A1-X2"]
    assert [(row.style, row.pincount) for row in rows] == [("header-2p", 2)] * 2
    assert [[pin.marking for pin in row.pins] for row in rows] == [["1", "2"], ["1", "2"]]
    lines = connectors_csv(model, _a1(model).id).splitlines()
    assert [line.split(",")[0] for line in lines[1:]] == ["-A1-X1", "-A1-X1", "-A1-X2", "-A1-X2"]


def test_the_drawn_pin_tags_of_the_device_name_the_connector() -> None:
    """(c) The pin views of `A1` are tagged `-A1-X1:1` and `-A1-X2:1`; no pin reads `-A1:1`."""
    # UNDO: fransys_model/derive/designation.py: `port_designation` `return
    #   f"{connector_designation(model, record.function, unit=unit)}:{record.name}"` -> the
    #   pre-rule `f"-{item_designation(model, owner.id, unit=unit)}:{record.name}"` (both pins
    #   read `-A1:1`; the stub texts come from `stub_far_end`, so the build still completes)
    model = _build().model
    tags = {
        label_text(model, label)
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.TAG and label.slot.startswith("tag.pin.")
    }
    assert tags == {"-A1-X1:1", "-A1-X2:1", "-P1:1", "-P2:1"}
    assert "-A1:1" not in tags


def test_the_two_stubs_on_the_cabinet_side_name_different_connectors_of_the_far_device() -> None:
    """(d) The stubs at `P1` and `P2` read `-W1 -> +B-A1-X1:1` and `-W1 -> +B-A1-X2:1`."""
    # UNDO: fransys_model/derive/drawing_text.py: `stub_far_end` `if segment:` -> `if False:`
    #   (the far end falls back to the item's own form, `+B-A1:1` for both: the build raises)
    model = _build().model
    stubs = sorted(
        (
            item_designation(model, functions(model)[ports(model)[m.port].function].item),
            marker_text(model, m).replace("\N{LEFTWARDS ARROW}", _ARROW),
        )
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF
    )
    assert stubs == [
        ("A1", f"-W1 {_ARROW} +A-P1:1"),
        ("A1", f"-W1 {_ARROW} +A-P2:1"),
        ("P1", f"-W1 {_ARROW} +B-A1-X1:1"),
        ("P2", f"-W1 {_ARROW} +B-A1-X2:1"),
    ]
    assert stubs[2][1] != stubs[3][1]
