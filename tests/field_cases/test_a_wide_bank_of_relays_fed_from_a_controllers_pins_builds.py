"""Field case: a bank of relays wider than the page, fed from one controller's pins, builds.

The engineering shape: one unit holds sixteen relays, each in its own function. Every coil is
fed from an interface strip and from its own pin of one external controller; each relay switches
a lamp whose return runs to a second strip. The sheet has a coarse module (`module_mm=3.0`), so
the coil bundle is one column wider than the content box and layout cuts it between its lanes.

The bug: the controller's pins are moved into the bundle's column as cells hosted on the
controller's box, and the strip's copies are hosted on those pin cells. The cut found a cell's
lane through its host in one step, so a host that was itself hosted raised `KeyError` in
`lane_of` and the build crashed.

The fix, decision layout-0232: a hosted cell takes the lane of the first cell up its host chain
that has one.
"""

import tempfile
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import fransys as fr

from fransys_model.layout import Page, layout_of


class _Io(NamedTuple):
    feed: fr.TerminalStrip


_PINS = tuple(f"CH{j:02d}-" for j in range(1, 17))
_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
}


def _bank(count: int):
    @fr.unit("demo-bank", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def bank(u: fr.Design) -> _Io:
        sheet = u.layout.sheet("S3", **_SHEET, module_mm=Decimal("3.0"))
        u.layout.profile(sheet=sheet)
        feed = u.terminal_strip("X1", "DEMO-TB-2.5", 8, interface=True)
        back = u.terminal_strip("X2", "DEMO-TB-2.5", 8)
        with u.function("PLC", "Controller"):
            controller = u.device("A1", None, pins=_PINS, external=True)
        for i in range(count):
            with u.function(f"R{i + 1}", f"Relay {i + 1}"):
                relay = u.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
                u.detail.wire(feed[1 + i % 4], relay.coil["A1"], wire=("WH", 0.75))
                u.detail.wire(controller[_PINS[i % 16]], relay.coil["A2"], wire=("BU", 0.75))
                lamp = u.device(f"P{i + 1}", "DEMO-LAMP-24")
                u.detail.wire(relay.co_1["14"], lamp.lamp[1], wire=("WH", 0.75))
                u.detail.wire(back[1 + i % 6], relay.co_1["11"], wire=("WH", 0.75))
                u.detail.wire(lamp.lamp[2], back[7], wire=("BU", 0.75))
        return _Io(feed)

    return bank


def _built(count: int) -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Bank\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.add(_bank(count), "U1")
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-bank", cover=cover)
        return fr.build(d, document)


def test_sixteen_relays_fed_from_one_controller_build_and_take_several_pages() -> None:
    """The build returns, the bank takes more than one page, and nothing is off the page."""
    built = _built(16)
    assert len(layout_of(built.model, Page)) > 1
    assert [f.code for f in fr.check(built)].count("OUT_OF_CONTENT_BOX") == 0
