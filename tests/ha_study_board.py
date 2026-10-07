"""The study board of acceptance 12: one unit with five interfaces, each on a harness.

`build(hint=True)` adds the side hint that fixes `bus_in` on top. Built from `demo_parts` only.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK, BN, BU, GY, RD, VT, WH, YE


class _Io(NamedTuple):
    pwr_estop: fr.Device
    plc_io: fr.Device
    bus_in: fr.Device
    sensor: fr.Device
    contactors: fr.Device


@fr.unit("demo-study", revision=1, interface_version=1, date="2026-10-07", text="t", by="XX")
def _board(d: fr.Design) -> _Io:
    tags = {"pwr_estop": "J1", "plc_io": "J2", "bus_in": "J3", "sensor": "J5", "contactors": "J7"}
    j = {
        n: d.device(t, "DEMO-HSG-4F", interface=True, contacts="DEMO-CRIMP-F")
        for n, t in tags.items()
    }
    lamps = [d.device(f"H{n}", "DEMO-LAMP-24") for n in range(1, 10)]
    ends = [
        (j["pwr_estop"], 1, 3),
        (j["pwr_estop"], 2, 4),
        (j["sensor"], 1, 4),
        (j["sensor"], 2, 3),
        (j["contactors"], 1, 2),
    ]
    for lamp, (conn, a, b) in zip(lamps, ends, strict=False):
        d.wire(conn[a], lamp["1"], wire=(BK, 0.5))
        d.wire(conn[b], lamp["2"], wire=(BK, 0.5))
    for lamp, pin in zip(lamps[6:8], (1, 2), strict=True):  # a lamp chains J2 to J3
        d.wire(j["plc_io"][pin], lamp["1"], wire=(BK, 0.5))
        d.wire(j["bus_in"][pin], lamp["2"], wire=(BK, 0.5))
    for lamp, pin in zip(lamps[5:6] + lamps[8:9], (3, 4), strict=True):  # and J7 to J3
        d.wire(j["contactors"][pin], lamp["1"], wire=(BK, 0.5))
        d.wire(j["bus_in"][pin], lamp["2"], wire=(BK, 0.5))
    return _Io(*(j[n] for n in _Io._fields))


def build(*, hint: bool = False) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    d.dc_supply("S", psu)
    io = d.add(_board, "U1")
    if hint:
        d.layout.side(io.bus_in, fr.ABOVE)
    x = d.terminal_strip("X1", "DEMO-TB-2.5", 14)

    def plug(w: Any, tag: str, face: Any) -> Any:  # a device; `fr` types no pin indexing
        p = d.device(tag, "DEMO-HSG-4M", parent=w, contacts="DEMO-CRIMP-M")
        d.mate(p, face)
        return p

    def wires(p: Any, ends: dict[int, tuple[Any, str]]) -> None:
        for pin, (far, colour) in ends.items():
            d.wire(p[pin], far, wire=(colour, 0.5))

    # terminals 1-2: 24 V, 3-4: 0 V, 5-8: e-stop and sensor signals, 9-10: bus, 11: aux feed
    d.wire(psu.output["+"], x[1].outer, wire=(RD, 0.5))
    d.wire(psu.output["-"], x[3].outer, wire=(BU, 0.5))
    d.wire(x[1].outer, x[2].outer, wire=(RD, 0.5))
    d.wire(x[1].outer, x[11].outer, wire=(RD, 0.5))
    d.wire(x[3].outer, x[4].outer, wire=(BU, 0.5))
    wires(
        plug(d.harness("W11"), "P11", io.pwr_estop),
        {1: (x[1].inner, RD), 2: (x[3].inner, BU), 3: (x[5].inner, YE), 4: (x[6].inner, YE)},
    )
    wires(
        plug(d.harness("W15"), "P15", io.sensor),
        {1: (x[2].inner, BN), 2: (x[4].inner, BU), 3: (x[7].inner, WH), 4: (x[8].inner, GY)},
    )
    wires(plug(d.harness("W13"), "P13", io.bus_in), {1: (x[9].inner, VT), 2: (x[10].inner, VT)})
    k1 = d.device("K1", "DEMO-CTR-LEADS")
    j10 = d.device(
        "J10",
        "DEMO-HSG-4F",
        parent=k1,
        contacts="DEMO-CRIMP-F",
        joins={"1": k1.coil["A1"], "2": k1.coil["A2"], "3": k1.aux["13"], "4": k1.aux["14"]},
    )
    w17 = d.harness("W17")
    pa, pb = plug(w17, "P17", io.contactors), plug(w17, "P18", j10)
    for pin in (1, 2, 3, 4):
        d.wire(pa[pin], pb[pin], wire=(BK, 0.5))
    d.wire(pa[1], x[11].inner, wire=(RD, 0.5))
    a1 = d.device("A1", "DEMO-PLC-DI-2")
    a2 = d.device("A2", "DEMO-PLC-DO-2")
    wires(plug(d.harness("W12"), "P12", io.plc_io), {1: (a1.di_1["1"], GY), 2: (a2.do_1["1"], WH)})
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
