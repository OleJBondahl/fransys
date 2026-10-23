"""A cable block's `<text>` elements are emitted row by row, so its PDF text layer reads so.

One strip `X1`, a motor `M1`, one three-core cable `W1` (`demo_parts`). Typst keeps the SVG's
element order in the PDF, so extraction follows it. Before the fix the cores came out in record
order (`3 GY`, `1 BN`, `2 BK`; `pdftotext -raw` on a turned page read "2 BK21 BK13 BK3"), and
every shape and text was interleaved. The rows read top to bottom, each left to right (render-0011).
"""

import functools
import re
import shutil
from pathlib import Path

import fransys as fr
import fransys_author
from _model_build_cover import _COVER
from fransys_render import cable_blocks

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_cables
from fransys_model.vocab import DocumentPreset

_TEXT = re.compile(r"<text [^>]*>([^<]*)</text>")


@functools.cache
def _svg() -> str:
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Cable", number="DEMO-5", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    loc = d.location("C1", "Demo cabinet")
    grp = d.group("SUP", "Supply")
    strip = d.strip("X1", at=loc)
    terminals = [strip.terminal("DEMO-TB-2.5", group=grp) for _ in range(3)]
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=loc, group=grp)
    cable = d.cable("DEMO-CBL-4G1.5", tag="W1", length_mm=5000)
    for n, (terminal, pin) in enumerate(zip(terminals, "UVW", strict=True), 1):
        cable.core(n, terminal.outer, motor[pin])
    built = fr.build(parts, d.draft(), fr.document(DocumentPreset.SYSTEM, None, cover=_COVER))
    (svg,) = dict(cable_blocks(lay_out_cables(built.model)[0], LIBRARY)).values()
    return svg


def test_texts_read_row_by_row_left_to_right():
    """Probe: `Ink.body` returns its texts in the order they were added (the old emission)."""
    texts = _TEXT.findall(_svg())
    assert texts == [
        "+C1-M1", "U", "V", "W",
        "-W1, 5000 mm",
        "1 BN", "2 BK", "3 GY",
        "1", "2", "3", "+C1-X1",
    ]  # fmt: skip


def test_every_shape_is_emitted_before_the_first_text():
    """The texts follow all outlines and wires; nothing is filled, so the paint is unchanged."""
    body = _svg()
    last_shape = max(body.rfind(tag) for tag in ("<rect", "<line", "<polyline"))
    assert last_shape < body.index("<text")


_BK_CABLE = """\
schema = 1

[part]
mpn = "DEMO-CBL-3BK"
manufacturer = "Demo"
description = "Control cable, 3 black cores"
category = "cable"
class_code = "W"

[rating]
voltage_ac_v = "500"

[cable_product]
core_count = 3
core_colours = ["BK", "BK", "BK"]
gauge_mm2 = "1.5"
shielded = false
"""


def test_equal_colours_read_number_then_colour_in_core_order(tmp_path_factory, monkeypatch):
    """Three cores all BK read "1 BK", "2 BK", "3 BK": number, then colour, in core order."""
    import demo_parts

    root = tmp_path_factory.mktemp("bk")
    shutil.copytree(Path(demo_parts.__file__).parent, root / "bk_parts")
    (root / "bk_parts" / "parts" / "cable-3bk.toml").write_text(_BK_CABLE)
    monkeypatch.syspath_prepend(str(root))
    parts = fr.parts("bk_parts")
    d = fransys_author.Design(parts)
    d.project(title="Cable", number="DEMO-5", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    loc = d.location("C1", "Demo cabinet")
    grp = d.group("SUP", "Supply")
    strip = d.strip("X1", at=loc)
    terminals = [strip.terminal("DEMO-TB-2.5", group=grp) for _ in range(3)]
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=loc, group=grp)
    cable = d.cable("DEMO-CBL-3BK", tag="W1", length_mm=5000)
    for n, (terminal, pin) in enumerate(zip(terminals, "UVW", strict=True), 1):
        cable.core(n, terminal.outer, motor[pin])
    built = fr.build(parts, d.draft(), fr.document(DocumentPreset.SYSTEM, None, cover=_COVER))
    (svg,) = dict(cable_blocks(lay_out_cables(built.model)[0], LIBRARY)).values()
    texts = _TEXT.findall(svg)
    assert texts[texts.index("-W1, 5000 mm") + 1 : -4] == ["1 BK", "2 BK", "3 BK"]
