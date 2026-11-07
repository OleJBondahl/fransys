"""Field case: one cabinet unit with 28 ordered groups; its sensor page holds two valve-feedback groups on a bridged 29-terminal fused strip,
the analog module group (two 4-channel current and two 2-channel RTD modules) and the pressure and RTD sensor groups wired to it.
The bug (v0.22.6): WIDER_THAN_PAGE, PAGE_OVERFLOW and WIRE_THROUGH_BODY on that page. Open."""

from contextlib import nullcontext
from functools import cache
from typing import Any

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BK, BN, BU

from fransys_model.kernel import Severity, id_namespace

SALTS = ("-", "a", "b", "c", "d", "e")


def _filler(d: Any, order: list[Any], tag: str, name: str, rails: Any) -> None:
    n = 2
    x24, x0 = rails
    with d.function(tag, name) as g:
        for k in range(n):
            lamp = d.device(f"{tag}H{k + 1}", "DEMO-LAMP-24")
            t = len(order) * 8 + 2 + k
            d.series(x24[t].inner, lamp.lamp, x0[t].inner, wire=(BU, 0.5))
    order.append(g)


def _design(*, hide: bool = False) -> tuple[Any, Any]:  # noqa: PLR0915, C901  one linear repro shape
    d = fr.design("demo_parts", "intake_parts", "measure_parts", place="CAB")
    d.project(title="Skid", number="P-2", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-11-06", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    rack = d.rack("U1")
    order: list[Any] = []
    # 3 supply
    with d.function("S1", "Supply 1") as g:
        psu = d.device("T1", "DEMO-PSU-24")
        d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
        dc = d.dc_supply("S", psu)
        x24 = d.terminal_strip("X24", "DEMO-TB-FUSE-2.5", 29, bridged=True)
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 29, bridged=True)
        d.series(dc.plus, x24[1].inner, wire=(BU, 0.5))
        d.series(dc.minus, x0[1].inner, wire=(BU, 0.5))
    f24 = d.terminal_strip("XF24", "DEMO-TB-2.5", 300, bridged=True)
    f0 = d.terminal_strip("XF0", "DEMO-TB-2.5", 300, bridged=True)
    d.series(x24[27].inner, f24[1].inner, wire=(BU, 0.5))
    d.series(x0[27].inner, f0[1].inner, wire=(BU, 0.5))
    rails = (f24, f0)
    order.append(g)
    for t in ("S2", "S3"):
        _filler(d, order, t, "Supply " + t[1], rails)
    # 3 motor circuits, 1 valve feed
    for t in ("M1", "M2", "M3"):
        _filler(d, order, t, "Motor " + t[1], rails)
    _filler(d, order, "VF", "Valve feed", rails)
    # 3 valve power, each with an 8-core cable and an actuator
    acts, cables = [], []
    for k in (1, 2, 3):
        with d.function(f"VP{k}", f"Valve power {k}") as g:
            act = d.device(f"V{k}", "DEMO-ACT-4P-2SW")
            w = d.cable(f"W{k}", "DEMO-CBL-8G0.75", length_m=10)
            d.series(x24[8 + k].outer, w, act.power, w, x0[8 + k].outer)
            d.series(x24[11 + k].outer, w, act.drive, w, x0[11 + k].outer)
        order.append(g)
        acts.append(act)
        cables.append(w)
    # 5 control
    for k in range(1, 6):
        _filler(d, order, f"C{k}", f"Control {k}", rails)
    # modules
    di = [d.device(f"A{k}", "DEMO-PLC-DI-4P", parent=rack) for k in (1, 2)]
    with d.function("AM", "Analog modules") as am:
        ai_a = d.device("A3", "DEMO-PLC-AI-4", parent=rack)
        ai_b = d.device("A4", "DEMO-PLC-AI-4", parent=rack)
        rtd_a = d.device("A5", "DEMO-PLC-RTD-2", parent=rack)
        rtd_b = d.device("A6", "DEMO-PLC-RTD-2", parent=rack)
    # 3 valve feedback: groups 1 and 2 land on the shared strip
    for k in (1, 2, 3):
        with d.function(f"VB{k}", f"Valve feedback {k}"):
            for s, core_pair in ((acts[k - 1].sw_1, 0), (acts[k - 1].sw_2, 1)):
                t = 2 * k + core_pair if k < 3 else 6 + core_pair
                d.series(x24[t].outer, cables[k - 1], s, cables[k - 1], di[0 if k < 3 else 1])
    # 1 gas inputs
    _filler(d, order, "GI", "Gas inputs", rails)
    # 2 pressure sensors on module A, 3 RTD sensors, 1 fan-current sensor, 1 current transmitter
    for k in (1, 2):
        with d.function(f"PT{k}", f"Pressure {k}") as g:
            s = d.device(f"B{k}", "DEMO-SENSOR-2W")
            w = d.cable(f"WP{k}", "DEMO-CBL-3X0.34", length_m=10)
            ch = getattr(ai_a, f"ai_{k}")
            w.core(BN, x24[22 + k].outer, s.sig["1"])
            w.core(BU, s.sig["2"], ch["1" if k == 1 else "5"])
            w.core(BK, ch["2" if k == 1 else "6"], x0[22 + k].outer)
        order.append(g)
    for k, (mod, ch) in enumerate(((rtd_a, 1), (rtd_a, 2), (rtd_b, 1)), 1):
        with d.function(f"RT{k}", f"Temperature {k}") as g:
            s = d.device(f"B{k + 2}", "DEMO-LOOP-4P")
            w = d.cable(f"WR{k}", "DEMO-CBL-4G1.5", length_m=10)
            f = getattr(mod, f"rtd_{ch}")
            for pin in ("1", "2", "3"):
                mp = str(int(pin) + 4 * (ch - 1))
                d.pair(f[mp], w, s.loop["2" if pin == "3" else pin])
            w.spare()
        order.append(g)
    with d.function("CT", "Fan current and transmitter") as g:
        fan = d.device("B6", "DEMO-SENSOR-2W")
        d.series(x24[21].inner, fan.sig["1"], wire=(BU, 0.5))
        d.series(fan.sig["2"], x0[21].inner, wire=(BU, 0.5))
        s = d.device("B7", "DEMO-SENSOR-2W")
        w = d.cable("WT", "DEMO-CBL-3X0.34", length_m=10)
        d.pair(ai_b.ai_1, w, s.sig)
    order.append(g)
    # 1 PLC controller, 1 analog module group, 1 digital output group
    with d.function("PLC", "Controller") as g:
        cpu = d.device("A0", "DEMO-PLC-CPU", parent=rack)
        d.series(x24[20].inner, cpu.power["24V"], wire=(BU, 0.5))
        d.series(cpu.power["0V"], x0[20].inner, wire=(BU, 0.5))
    order.append(g)
    order.append(am)
    with d.function("DO", "Digital outputs") as g:
        do = d.device("A7", "DEMO-PLC-DO-2", parent=rack)
        lamp = d.device("HO", "DEMO-LAMP-24")
        d.series(do.do_1["1"], lamp.lamp["1"], wire=(BU, 0.5))
        d.series(lamp.lamp["2"], x0[22].inner, wire=(BU, 0.5))
    order.append(g)
    d.layout.order(*order)
    if hide:
        d.layout.profile(hide_unused_pins=True)
    return d, cab


@cache
def _built(salt: str, *, hide: bool = False) -> fr.BuildResult:
    with id_namespace(salt) if salt != "-" else nullcontext():
        d, cab = _design(hide=hide)
        return fr.build(d, cabinet_document(cab))


@pytest.mark.parametrize("salt", SALTS)
def test_the_page_builds_with_no_error(salt: str) -> None:
    """The engineer's result: no ERROR (the consumer's WIDER_THAN_PAGE, PAGE_OVERFLOW, WIRE_THROUGH_BODY and DRAWING_SHORTS_NETS included)."""
    errors = sorted(f.code for f in fr.check(_built(salt)) if f.severity is Severity.ERROR)
    assert errors == []


@pytest.mark.parametrize("salt", SALTS)
def test_a_pin_leaves_its_box_on_its_own_side_with_unused_pins_hidden(salt: str) -> None:
    """KI-776: with `hide_unused_pins` the box is smaller and a stem leaves the nearest footprint edge, through the body (WIRE_THROUGH_BODY)."""
    codes = [f.code for f in fr.check(_built(salt, hide=True))]
    assert "WIRE_THROUGH_BODY" not in codes
