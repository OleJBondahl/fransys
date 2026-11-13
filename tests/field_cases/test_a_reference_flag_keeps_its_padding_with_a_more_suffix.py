"""Field case: a reference flag's outline keeps its padding when its text ends in `+n`.
The bug: the set's reference box width ignored the ` +k` suffix, so a flag like `#11-p5:2B +4` ran 2.2 pt past its outline.
Fixed by the rule, no record named: the outline keeps `marker_padding` on both sides of every flag text."""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document

from electrical_symbols import LIBRARY
from fransys_layout.symbols import text_room_on, text_width_g
from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, layout_of, sheet_format_of, tuning_of

_TAG = "W" * 20


class _Io(NamedTuple):
    X1: Any


@fr.unit(
    "demo-flags",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Flags",
    number="F-1",
)
def _flags(d: Any) -> _Io:
    x1 = d.terminal_strip("X" + _TAG, "DEMO-TB-2.5", 8, interface=True)
    x2 = d.terminal_strip("Y" + _TAG, "DEMO-TB-2.5", 8)
    hub: Any = None
    ends: dict[Any, Any] = {}  # a terminal point takes one conductor (R1266): each point's wires chain from device pin to device pin
    for i in range(12):
        with d.function(f"C{i + 1:02d}", f"Circuit {i + 1}"):
            k = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            h = d.device(f"H{i + 1}", "DEMO-LAMP-24")
            d.series(ends.get(("x1", i % 6), x1[1 + i % 6].inner), k.coil["A1"], wire=("RD", 0.75))
            if hub is None:
                hub = k
            else:  # model-0220: a device star keeps its flags (a terminal hub is copied)
                d.series(hub.coil["A2"], k.coil["A2"], wire=("BK", 0.75))
            d.series(ends.get(("x2", i % 6), x2[1 + i % 6].inner), k.co_1["11"], wire=("RD", 0.75))
            d.series(k.co_1["14"], h.lamp[1], wire=("RD", 0.75))
            d.series(h.lamp[2], ends.get("lamp", x2[8].inner), wire=("BU", 0.75))
            ends[("x1", i % 6)], ends[("x2", i % 6)], ends["lamp"] = k.coil["A1"], k.co_1["11"], h.lamp[2]
    return _Io(x1)


def test_a_reference_flag_keeps_its_padding_with_a_more_suffix() -> None:
    d = fr.design("demo_parts")
    d.add(_flags, "U1")
    model = fr.build(d, unit_document("demo-flags")).model
    height = text_room_on(model, sheet_format_of(model, None), LIBRARY)
    padding = tuning_of(model).marker_padding
    flags = [(marker_text(model, m), m) for m in layout_of(model, LinkMarker).values()]
    suffixed = [(t, m) for t, m in flags if t.startswith("#") and " +" in t]
    assert suffixed, "the shape must print a flag with a ` +k` suffix"
    short = []
    for text, marker in suffixed:
        along = marker.width
        needed = max(text_width_g(LIBRARY.font, t, height=height) for t in text.split("\n")) + 2 * padding
        if along < needed:
            short.append((text, along, needed))
    assert short == []
