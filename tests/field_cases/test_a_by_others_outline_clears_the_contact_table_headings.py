"""Field case: a by-others outline and its note stay off the headings of contact tables.

The engineering shape: a unit holds relays in one column, each coil fed from a pin of one
external controller (a device by others), so the controller's dashed outline stands over the
column. The contact tables of the relays share the column foot, under the outline, and each is
headed by its coil.

The bug: the outline was sized from the controller's pins and labels and the tables were placed
beforehand, so the dashed bottom edge ran through the first row of headings and the "by others"
note sat on a heading.

The fix, decision layout-0238: the tables under an outline are pushed down until they clear the
outline and its note.
"""

import tempfile
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from _drawn_extent import body_g
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


def _clear(a, b) -> bool:
    """Whether the rectangles `a` and `b` (x, y, width, height) do not overlap."""
    return a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]


def _rect(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) as (x, y, width, height)."""
    return (box[0], box[1], box[2] - box[0], box[3] - box[1])


def _drawn(model) -> tuple[list, list, list]:
    """The headed tables, the by-others notes and the outlines the core drew, all pages."""
    tables, notes, outlines = [], [], []
    for d in drawn_pages(model).values():
        tables += [s for s in d.symbols if s.key == "contact-head"]
        notes += [_rect_of_text(t) for t in d.texts if t.kind == "external_note"]
        for o in d.outlines:
            xs, ys = [p[0] for p in o.points], [p[1] for p in o.points]
            outlines.append((min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))
    return tables, notes, outlines


def _rect_of_text(t) -> tuple[int, int, int, int]:
    return (t.box.x, t.box.y, t.box.w, t.box.h)


def test_a_by_others_outline_and_note_clear_every_contact_table_heading() -> None:
    """No headed table overlaps the controller's dashed outline or its "by others" note."""
    tables, notes, outlines = _drawn(_built(2).model)
    tables = [_rect(body_g(s)) for s in tables]
    assert len(tables) == 2
    assert len(notes) == 1
    assert len(outlines) == 1
    assert all(_clear(t, o) for t in tables for o in (*outlines, *notes))


def test_the_tables_of_a_band_move_down_together_and_keep_their_stagger() -> None:
    """Four tables stagger in two rows; the outline pushes them all by one distance (layout-0238).

    Only the first row meets the outline, but the second row moves with it, so the first row stays
    level (-K1 with -K3) and the second row stays level (-K2 with -K4).
    """
    tables = sorted(_drawn(_built(4).model)[0], key=lambda s: s.x)
    assert len(tables) == 4
    first, second, third, fourth = (s.y for s in tables)
    assert first == third
    assert second == fourth
    assert first != second
