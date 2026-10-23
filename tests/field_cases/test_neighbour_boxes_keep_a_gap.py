"""Field case: two boxes side by side in one row never touch.

The engineering shape: a contactor with a three-pole main contact and a wired NO auxiliary
contact. The main poles feed a motor box, the auxiliary contact feeds a lamp box. The motor
box stands under the poles and the lamp box under the auxiliary lane, in one row.

The bug: the lamp's lane lay inside the motor box's width, so the two boxes shared an edge and
read as one rectangle with two compartments (SYMBOL_OVERLAP). The lane offset of a box that
spans lanes ignored the box before it.
The fix: `place._keep_gap`, a row keeps the column gap between any two neighbours
after the lane offsets, the later box and its right-hand neighbours move right.
"""

import tempfile
from pathlib import Path

import fransys as fr
from _drawn_facts import symbol_subjects
from fransys.colours import BU

from electrical_symbols import LIBRARY
from fransys_layout.symbols import library_symbol, symbol_shape


def _built():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.detail.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.detail.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.detail.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.detail.wire(q.aux["14"], lamp["1"], wire=blue)
    d.detail.wire(psu.output["-"], lamp["2"], wire=blue)
    for pole, pin in enumerate("UVW"):
        d.detail.wire(psu.output["+"], q.main[str(2 * pole + 1)], wire=blue)
        d.detail.wire(q.main[str(2 * pole + 2)], motor.motor[pin], wire=blue)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    built = fr.build(d, doc)
    return built.findings, built.model


def _clearance(model, first: str, second: str) -> int:
    """The clear space between the drawn outlines of the symbols of items `first` and `second`.

    The larger of the x gap and the y gap: positive when the two boxes share no edge or area.
    """
    outline = {}
    for one in symbol_subjects(model):
        tag = one.tag
        if tag in (first, second):
            body = symbol_shape(library_symbol(LIBRARY, one.key), LIBRARY).body
            outline[tag] = (one.x + body.x, one.y + body.y, body.w, body.h)
    (ax, ay, aw, ah), (bx, by, bw, bh) = outline[first], outline[second]
    return max(bx - (ax + aw), ax - (bx + bw), by - (ay + ah), ay - (by + bh))


def test_neighbour_boxes_keep_a_gap() -> None:
    """No SYMBOL_OVERLAP, and the motor's and the lamp's drawn outlines have a positive gap."""
    findings, model = _built()
    assert not [f for f in findings if f.code == "SYMBOL_OVERLAP"]
    assert _clearance(model, "M1", "P1") > 0
