"""Field case: a controller's supply, its lone analogue input and a relay coil share one bridged 0 V strip, one conductor per clamp.
The bug: PLACEMENT_PROBLEM on the input pin ("fits no pose clear of its surroundings"), an ERROR, so fr.write raises (order PLACEMENT-0223, N5c).
Fixed: an attached column under a card hangs below the card's grown footprint."""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from fransys.colours import BK, RD, WH

if TYPE_CHECKING:
    from pathlib import Path

_RELAY = "DEMO-RLY-4CO-24"


class _Io(NamedTuple):
    pass


@fr.unit("fc-placement", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _unit(d: fr.Design) -> _Io:
    strip = "DEMO-TB-2.5"
    x4 = d.terminal_strip("X4", strip, 6, description="+24 V")
    x7 = d.terminal_strip("X7", strip, 8, description="0 V", bridged=(2, 8))
    cu1 = d.device("CU1", "DEMO-CTRL-SUPPLY-2DO-1AI")
    psu = d.device("PSU", "DEMO-PSU-24")
    k1, k2, k4, q1, q2 = (d.device(tag, _RELAY) for tag in ("K1", "K2", "K4", "Q1", "Q2"))
    dc = d.dc_supply("24VDC", plus=psu.output["+"], minus=psu.output["-"], voltage=24, names=("24V", "GND"))
    d.series(dc.minus, x7[2], wire=(BK, 0.5))
    for pin, t in ((cu1.supply_control.S24V, 3), (k1.coil.A1, 4), (k2.coil.A1, 5)):
        d.series(x4[t].inner, pin, wire=(RD, 0.5))
    for load, terminal in ((cu1.supply_control, 3), (cu1.ai_6, 4), (q1.coil, 5), (q2.coil, 6), (k4.coil, 7)):
        d.series(load, x7[terminal], wire=(BK, 0.5))
    d.series(k1.coil, cu1.out_1, wire=(WH, 0.5))
    d.series(k2.coil, cu1.out_2, wire=(WH, 0.5))
    d.series((k1.co_1[11],), (q1.coil.A1,), wire=(WH, 0.5))
    d.series((k2.co_1[11],), (q2.coil.A1,), wire=(WH, 0.5))
    d.series(x4[6].inner, k4.coil.A1, wire=(RD, 0.5))
    return _Io()


def test_the_lone_input_on_the_shared_0v_terminal_finds_a_pose(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    (tmp_path / "cover.md").write_text("# cover\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "fc-placement", cover=tmp_path / "cover.md")
    errors = [f.code for f in fr.build(d, document).findings if f.severity.name == "ERROR"]
    assert errors == []
