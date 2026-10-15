"""Field case: a contact table's heading prints the same designation as its coil's tag.

The engineering shape: a unit holds a few relays, each in its own function, each coil fed from a
strip and from a pin of one external controller and each relay switching a lamp. The relays
stand in one column, so their contact tables share a column foot and each table is headed by
its coil.

The bug: the coil is drawn "-K1" (shortest designation, the unit's own set), but the heading
above its contact table read "-U1-K1", because the heading was built without the unit that the
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

from fransys_model.derive.drawing_text import CONTACTS_HEADED, label_text
from fransys_model.layout import Label, LabelKind, layout_of


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


def test_a_headed_table_names_its_coil_as_the_coil_is_drawn() -> None:
    """Each heading line is a coil's drawn tag (`-K3`), never the long `-U1-K3`."""
    model = _built(4).model
    labels = layout_of(model, Label).values()
    drawn = {label_text(model, r) for r in labels if r.kind is LabelKind.TAG}
    heads = [label_text(model, r).split("\n")[0] for r in labels if r.slot == CONTACTS_HEADED]
    assert len(heads) == 4
    assert all(head in drawn for head in heads)
    assert not any("U1" in head for head in heads)
