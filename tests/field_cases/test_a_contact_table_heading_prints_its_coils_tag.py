"""Field case: a contact table's heading prints the same designation as its coil's tag.

The engineering shape: a unit holds a few relays, each in its own function, each coil fed from a
strip and from a pin of one external controller and each relay switching a lamp. Each coil
owns one contact table, placed at its corner (el-0049), keyed by the coil.

The bug: the coil is drawn "-K1" (shortest designation, the unit's own set), but the heading
beside its contact table read "-U1-K1", because the heading was built without the unit that the
coil's tag is built with.

The fix, decision model-0238: `coil_heading` takes the unit and both callers (layout, which
measures the heading, and `contact_heading`, which render prints) pass the unit of the set they
draw.
"""

import tempfile
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from _tables_on import TABLES_ON


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
        return fr.build(d, document, settings=TABLES_ON)


def test_a_headed_table_names_its_coil_as_the_coil_is_drawn() -> None:
    """Each coil owns one table head, keyed by its coil (el-0049); no long `-U1-K3` is printed.

    A table stands at its coil's corner, so the head carries no heading line. Its own coil's tag
    is drawn beside it, and no tag of the page reads the unit-long designation.
    """
    pages = drawn_pages(_built(4).model).values()
    drawn = {t.text for d in pages for t in d.texts if t.kind == "TAG"}
    heads = [s for d in pages for s in d.symbols if s.key == "contact-head"]
    assert len(heads) == 4
    assert len({s.id for s in heads}) == 4
    assert all(s.texts[0] == ("NO", "NC") and "heading" not in dict(s.slots) for s in heads)
    assert {"-K1", "-K2", "-K3", "-K4"} <= drawn
    assert not any("U1" in text for text in drawn)
