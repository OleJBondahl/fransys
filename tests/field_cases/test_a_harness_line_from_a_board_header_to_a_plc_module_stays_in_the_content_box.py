"""Field case: a cabinet unit nests a board unit with two interface headers; two harnesses of
single wires, W4 and W5, each a plug mated to one header. W4's plug wires to a PLC rack module
and W5's plug wires to a terminal and a pump block. The cabinet's document adds the harness
drawing pages, and the cabinet has an outside system (feed terminal, motor cable).

The bug: W4's harness line runs from the module at the foot of the page, under it to the page
foot, and back up to the header box. Its ink leaves the content box (OUT_OF_CONTENT_BOX) and its
label finds no free place beside it (LABEL_UNPLACED), both on the `-W4` subject. Found in a
consumer's example build, reduced to demo parts (2026-10-16): the harness family still routes
and places a line with a plug at a header box as if it were a free wire.

The fix: the harness family switch (work order UNIT-MATE-SCOPE part A). This case asserts the
right outcome and stays a strict xfail until that switch lands.
"""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
from fransys.colours import BK, RD, WH

_CODES = {"OUT_OF_CONTENT_BOX", "LABEL_UNPLACED"}


class _Headers(NamedTuple):
    J1: fr.Device
    J2: fr.Device


class _Points(NamedTuple):
    feed: tuple[fr.Run, ...]
    motor: tuple[fr.Run, ...]


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-16", text="first", by="XX")
def _board(u: fr.Design) -> _Headers:
    pcb = u.device("U9", "DEMO-PCB-IO")
    k1 = u.device("K1", "DEMO-RLY-2CO-24", parent=pcb)
    k2 = u.device("K2", "DEMO-RLY-2CO-24", parent=pcb)
    j1 = u.device("J1", "DEMO-CONN-4P", parent=pcb, interface=True)
    j2 = u.device("J2", "DEMO-CONN-4P", parent=pcb, interface=True)
    u.detail.wire(j1["1"], k1.coil["A1"], wire=(WH, 0.5))
    u.detail.wire(j1["2"], k2.coil["A1"], wire=(WH, 0.5))
    u.detail.wire(j1["3"], k1.coil["A2"], wire=(WH, 0.5))
    u.detail.wire(j1["3"], k2.coil["A2"], wire=(WH, 0.5))
    u.detail.wire(j2["1"], k1.co_1["11"], wire=(WH, 0.5))
    u.detail.wire(j2["1"], k2.co_1["11"], wire=(WH, 0.5))
    u.detail.wire(j2["2"], k1.co_1["14"], wire=(WH, 0.5))
    u.detail.wire(j2["3"], k2.co_1["14"], wire=(WH, 0.5))
    return _Headers(j1, j2)


@fr.unit("demo-cabinet", revision=1, interface_version=1, date="2026-10-16", text="first", by="XX")
def _cabinet(u: fr.Design) -> _Points:
    with u.function("SUP", "Incoming supply"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
        feed = tuple(x1.run(kind, 1) for kind in ("L1", "L2", "L3", "N", "PE"))
        u.device("Q1", "DEMO-MCB-3P")
        x01 = u.terminal_strip("X01", "DEMO-TB-2.5")
        for kind in ("L1", "L2", "L3"):
            x01.run(kind, 4, bridged=True)
    with u.function("CTL", "Control supply"):
        u.device("F01", "DEMO-MCB-2P")
        u.device("T1", "DEMO-PSU-24")
        x2 = u.terminal_strip("X2", "DEMO-TB-2.5")
        v24, gnd = x2.run("24V", 10, bridged=True), x2.run("GND", 7, bridged=True)
        u.dc_supply("24V", plus=v24[1], minus=gnd[1], voltage=24, names=("24V", "GND"))
    with u.function("PLC", "PLC"):
        rack = u.rack("U1")
        cpu = u.device("C1", "DEMO-PLC-CPU", name="cpu", position=1, parent=rack)
        di = u.device("DI1", "DEMO-PLC-DI-4P", name="di", position=2, parent=rack)
        io = u.device("DO1", "DEMO-PLC-DI-4P", name="io", position=3, parent=rack)
        u.detail.wire(gnd[3], cpu.power["0V"], wire=(BK, 1.5))
        for module in (di, io):
            u.detail.busbar(cpu.power["0V"], module.power["0V"])
        board = u.add(_board, "U2")
        w4, w5 = u.harness("W4"), u.harness("W5")
        p4 = u.device("J1", "DEMO-CONN-4P", parent=w4)
        p5 = u.device("J2", "DEMO-CONN-4P", parent=w5)
        u.mate(p4, board.J1)
        u.mate(p5, board.J2)
        u.detail.wire(p4["2"], io.di_2["2"], wire=(WH, 0.5))
        u.detail.wire(p4["3"], io.power["0V"], wire=(WH, 0.5))
        u.detail.wire(v24[4], p5["1"], wire=(RD, 0.5))
    x3 = u.terminal_strip("X3", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
    motor = tuple(x3.run(kind, 2) for kind in ("U", "V", "W", "PE"))
    with u.function("P1", "Pump 1"):
        contactor = u.device("Q11", "DEMO-CTR-3P-24")
        overload = u.device("B12", "DEMO-OVERLOAD-3P", mounted_on=contactor.main)
        u.detail.wire(p5["2"], overload.aux["95"], wire=(WH, 1.5))
        u.detail.wire(overload.aux["96"], contactor.coil["A1"], wire=(WH, 1.5))
        u.detail.wire(contactor.coil["A2"], gnd[4], wire=(BK, 1.5))
    return _Points(feed, motor)


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_cabinet, "U1", place=None)
    with d.function("SUP", "Incoming supply"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", external=True)
        upstream = [x0.run(kind, 1) for kind in ("L1", "L2", "L3", "N", "PE")]
        w1 = d.cable("W1", "DEMO-CBL-8G0.75", length_m=10)
        for core, (outside, inside) in enumerate(zip(upstream, cab.feed, strict=True), start=1):
            w1.core(core, outside[1], inside[1])
    for n in (1, 2):
        with d.function(f"P{n}", f"Pump {n}"):
            motor = d.device(f"M{n}", "DEMO-MOTOR-4KW")
            cable = d.cable(f"W{n}1", "DEMO-CBL-4G1.5", length_m=15)
            for core, (run, pin) in enumerate(
                zip(cab.motor, ("U", "V", "W", "PE"), strict=True), start=1
            ):
                cable.core(core, run[n], motor[pin])
    ranks = {"SUP": 0, "CTL": 1, "PLC": 2, "P1": 3, "P2": 4}
    d.layout.profile(group_ranks=ranks, hide_unused_pins=True)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        "demo-cabinet",
        cover=cover,
        add=(fr.PageKind.HARNESS_DRAWING,),
    )
    return fr.build(d, doc)


def test_a_harness_line_to_a_plc_module_stays_in_the_content_box(tmp_path: Path) -> None:
    result = _build(tmp_path)
    found = [
        (f.code, f.message) for f in fr.check(result) if f.code in _CODES and "-W4" in f.message
    ]
    assert found == []
