"""Field case: a supply whose output has unwired pins, hidden, stands over the module it feeds.

The engineering shape: two 24 V supplies, each fed from its own pair of strip terminals, feed one
redundancy module with an input group per supply. A supply's output function has five pins and
only two are wired, one plus and one minus. The profile hides unused pins, so each supply draws
two output pins, over the module's two input pins.

The bug: pairing counted every port of a function, drawn or not, so a five-pin output never
matched a two-pin group. The supplies stood beside the module, bent around it, and on a full
cabinet landed on another page behind link markers. A two-pin output drew right.
The rule (decision layout-0128, amending layout-0122): pairing counts the ports each side draws.
"""

import tempfile
from pathlib import Path

import fransys as fr
from _drawn_facts import item_box
from fransys.colours import BN, BU

from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _built(mpn: str, plus: str, minus: str):
    """The built model: two supplies of `mpn` from terminals into one redundancy module."""
    d = fr.design("demo_parts", place="CAB")
    d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    ac = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    live, neutral = ac.run("L", 2, bridged=True), ac.run("N", 2, bridged=True)
    with d.function("G", "Supply"):
        m1 = d.device("M1", "DEMO-RED-2IN")
        psus = [d.device(f"G{n}", mpn) for n in (1, 2)]
    for n, psu in enumerate(psus, start=1):
        d.detail.wire(live[n].outer, psu.input["L"], wire=(BN, 1.5))
        d.detail.wire(neutral[n].outer, psu.input["N"], wire=(BU, 1.5))
        group = getattr(m1, f"in_{n}")
        d.detail.wire(psu.output[plus], group[f"{n}+"], wire=(BN, 1.5))
        d.detail.wire(psu.output[minus], group[f"{n}-"], wire=(BU, 1.5))
    rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    d.dc_supply("S", plus=m1.out["+"], minus=m1.out["-"], voltage=24)
    d.detail.wire(m1.out["+"], rail.run("P", 2, bridged=True)[1].outer, wire=(BN, 1.5))
    d.detail.wire(m1.out["-"], rail.run("M", 2, bridged=True)[1].outer, wire=(BU, 1.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _pin_x(box, name: str) -> int:
    return box.x + dict(box.offsets)[name]


def _check(model, plus: str, minus: str) -> None:
    """No marker to the module, the drawn output pins over the input pins, one page."""
    module = item_box(model, "M1")
    psus = {n: item_box(model, f"G{n}") for n in (1, 2)}
    boxed = {i.id for i in items(model).values() if i.key[-1].split("/")[-1] in ("M1", "G1", "G2")}
    fn_of = {pid: functions(model)[p.function] for pid, p in ports(model).items()}
    wires = [
        m
        for m in layout_of(model, LinkMarker).values()
        if fn_of[m.port].item in boxed and fn_of[m.port].key[-1] != "out"
    ]
    assert not wires, "a wire between a supply and the module is a link marker"
    for n, psu in psus.items():
        assert _pin_x(psu, f"output.{plus}") == _pin_x(module, f"in_{n}.{n}+")
        assert _pin_x(psu, f"output.{minus}") == _pin_x(module, f"in_{n}.{n}-")
    assert {module.page, *(psu.page for psu in psus.values())} == {module.page}


def test_two_pin_output_stands_over_the_module() -> None:
    """The control: a two-pin output pairs today."""
    model = _built("DEMO-PSU-24", "+", "-")
    _check(model, "+", "-")


def test_five_pin_output_with_two_wired_stands_over_the_module() -> None:
    """The three unwired pins are hidden, so the output draws two pins and pairs."""
    model = _built("DEMO-PSU-24-5OUT", "+1", "-1")
    _check(model, "+1", "-1")
