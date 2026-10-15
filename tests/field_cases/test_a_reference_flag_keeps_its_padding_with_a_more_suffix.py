"""Field case: a reference flag's outline keeps its padding when its text ends in `+n`.

The engineering shape: a unit of twelve relay circuits, each fed from one of two long-tagged
strips, so most nets cross pages and their flags read `#n-p<page>:<cell>`. A net reaching more
than two cells prints the first target and ` +k` for the others (decision model-0139).

The bug: the set's one reference box width is sized from the widest `#99-...` text without
the ` +k` suffix, so a flag whose text carries a suffix (`#11-p5:2B +4`) is wider than its
outline allows: the text runs past the pentagon by 2.2 pt in the consumer's drawing.

The rule: the outline keeps `marker_padding` on both sides of the text, for every flag text.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_model.derive.drawing_text import marker_text
from fransys_model.derive.text_width import text_width
from fransys_model.layout import LinkMarker, default_profile, layout_of

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
    for i in range(12):
        with d.function(f"C{i + 1:02d}", f"Circuit {i + 1}"):
            k = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            h = d.device(f"H{i + 1}", "DEMO-LAMP-24")
            d.detail.wire(x1[1 + i % 6], k.coil["A1"], wire=("RD", 0.75))
            if hub is None:
                hub = k
            else:  # model-0220: a device star keeps its flags (a terminal hub is copied)
                d.detail.wire(hub.coil["A2"], k.coil["A2"], wire=("BK", 0.75))
            d.detail.wire(x2[1 + i % 6], k.co_1["11"], wire=("RD", 0.75))
            d.detail.wire(k.co_1["14"], h.lamp[1], wire=("RD", 0.75))
            d.detail.wire(h.lamp[2], x2[8], wire=("BU", 0.75))
    return _Io(x1)


def test_a_reference_flag_keeps_its_padding_with_a_more_suffix() -> None:
    d = fr.design("demo_parts")
    d.add(_flags, "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-flags", cover=cover)
    ).model
    height = DEFAULT_PROFILE.text_height
    padding = default_profile().marker_padding
    flags = [(marker_text(model, m), m) for m in layout_of(model, LinkMarker).values()]
    suffixed = [(t, m) for t, m in flags if t.startswith("#") and " +" in t]
    assert suffixed, "the shape must print a flag with a ` +k` suffix"
    short = []
    for text, marker in suffixed:
        along = marker.height if marker.vertical else marker.width  # a turned box's length
        needed = max(text_width(t, height=height) for t in text.split("\n")) + 2 * padding
        if along < needed:
            short.append((text, along, needed))
    assert short == []
