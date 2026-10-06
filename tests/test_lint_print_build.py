"""Decision parts-0003 / model-0071: the demo part `DEMO-IO-CLAMPS` builds with no duplicate print.

The part has a clamp strip `clamps` (no label) and three labelled plug sockets `x1`, `x2`, `x4`,
all with a pin `1`. The part lint accepts it (`test_lint_checks`, and the library lint of
`demo_parts`) because the pins print `-A1:1`, `-A1-X1:1`, `-A1-X2:1` and `-A1-X4:1`: one text
each. This test builds an item of it through the facade, wires one pin `1` of each function, and
asserts the model-side `PORT_DESIGNATION_DUPLICATE` check agrees with the lint: no finding at all.

Can-fail: with `connector_segments` (`fransys_model.derive.designation`) returning `""` for
every function, the four pins all print `-A1:1`; the lint shares that rule, so loading the library
raises `PartLibraryError` inside `_build`: a FAILED test id, not a collection error.
"""

import functools
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts

from fransys_model.derive import item_designation, port_designation
from fransys_model.kernel import Severity
from fransys_model.vocab.tables import functions, items, ports

_PROJECT: dict[str, Any] = {
    "title": "Clamps and sockets",
    "number": "P-1072",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_CODE = "PORT_DESIGNATION_DUPLICATE"


@functools.cache
def _build():
    """The build result; cached so the tests share one build, called inside each test."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    cabinet, field = d.location("A", "Cabinet"), d.location("B", "Field")
    group = d.group("G", "Pump")
    a1 = d.item("DEMO-IO-CLAMPS", tag="A1", at=field, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", tag="W1")
    for core, function in enumerate(("clamps", "x1", "x2", "x4"), start=1):
        plug = d.item("DEMO-CONN-2P", tag=f"P{core}", at=cabinet, group=group)
        cable.core(core, plug["1"], a1.fn(function)["1"])
    return fr.build(parts, d.draft())


def test_the_item_builds_with_no_port_designation_duplicate_and_no_error() -> None:
    """The four pins `1` print four different texts: no `PORT_DESIGNATION_DUPLICATE`, no ERROR."""
    # UNDO: fransys_model/derive/designation.py: `connector_segments` final `return
    #   tuple(...)` -> `return ("",) * len(given)` (the lint and the model share the rule, so the
    #   library load raises `PartLibraryError` on the four `1` pins before any build)
    result = _build()
    assert _CODE not in {f.code for f in result.findings}
    assert Severity.ERROR not in {f.severity for f in result.findings}


def test_the_four_pins_1_of_the_item_print_the_four_texts_the_lint_reasons_about() -> None:
    """`clamps` prints under the item, each socket behind its label."""
    model = _build().model
    a1 = next(i for i in items(model).values() if item_designation(model, i.id) == "A1")
    pins_1 = [
        port_designation(model, p.id)
        for p in ports(model).values()
        if p.name == "1" and functions(model)[p.function].item == a1.id
    ]
    assert sorted(pins_1) == ["-A1-X1:1", "-A1-X2:1", "-A1-X4:1", "-A1:1"]
