"""Field case: two boxes side by side in one row never touch.

The engineering shape: a contactor with a three-pole main contact and a wired NO auxiliary
contact. The main poles feed a motor box, the auxiliary contact feeds a lamp box. The motor
box stands under the poles and the lamp box under the auxiliary lane, in one row.

The bug: the lamp's lane lay inside the motor box's width, so the two boxes shared an edge and
read as one rectangle with two compartments (SYMBOL_OVERLAP). The lane offset of a box that
spans lanes (C12) ignored the box before it.
The fix (BOX-GAP): `place._keep_gap`, a row keeps the column gap between any two neighbours
after the lane offsets, the later box and its right-hand neighbours move right.
"""

import tempfile
from pathlib import Path
from typing import Any

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items


def _built():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.wire(q.aux["14"], lamp["1"], wire=blue)
    d.wire(psu.output["-"], lamp["2"], wire=blue)
    for pole, pin in enumerate("UVW"):
        d.wire(psu.output["+"], q.main[str(2 * pole + 1)], wire=blue)
        d.wire(q.main[str(2 * pole + 2)], motor.motor[pin], wire=blue)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    built = fr.build(d, doc)
    model = built.model
    return built.findings, model, stage_results(model, read_inputs(model))[0].layout


def _gaps(model, layout) -> dict[str, int]:
    """The x gap from the motor box to the lamp box: drawn outlines (body) and keep-outs."""
    by_tag = {one.key[-1]: one.id for one in items(model).values()}
    fn = {v.item: k for k, v in functions(model).items()}
    home: dict[Any, Any] = {}
    for one in layout.placed:
        home.setdefault(one.function, one)
    motor, lamp = home[fn[by_tag["M1"]]], home[fn[by_tag["P1"]]]

    def right(p, box):
        return p.at.x + box.x + box.width

    return {
        "body": lamp.at.x + lamp.geometry.body.x - right(motor, motor.geometry.body),
        "keepout": lamp.at.x + lamp.geometry.keepout.x - right(motor, motor.geometry.keepout),
    }


def test_neighbour_boxes_keep_a_gap() -> None:
    """No SYMBOL_OVERLAP, and the two drawn outlines and keep-outs have a positive gap."""
    findings, model, layout = _built()
    assert not [f for f in findings if f.code == "SYMBOL_OVERLAP"]
    gaps = _gaps(model, layout)
    assert gaps["body"] > 0
    assert gaps["keepout"] > 0
