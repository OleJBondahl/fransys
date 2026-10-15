"""A wire from a terminal strip to a stacked run is drawn although a 24V supply text is near it.

Engineering shape: an interface strip of 15 terminals, a one-terminal run (17) stacked beside it
whose outer port carries a 24V supply symbol, and a signal net over four lamps in their own
functions (its marker prints a " +k" count, which makes every reference box taller).

The bug: the taller box grew a terminal's keep-out until the "24V" text found a place one grid
below it, on the lane the wire leaves by. The router holds a text as an unowned box, which has no
exempt lane, so the wire was sealed in: ROUTE_FAILED and CONNECTION_NOT_DRAWN.

Fixed by layout-0196: no text stands on a port's exit lane, and the power placer is given the lanes.
"""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr


class _Io(NamedTuple):
    x1: fr.TerminalStrip


@fr.unit(
    "shape", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
    title="Shape", number="S-1",
)  # fmt: skip
def _shape(d):
    psu = d.device("T1", "DEMO-PSU-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("24V", psu)
    rail = d.terminal_strip("X3", "DEMO-TB-2.5").run("24V", 2, bridged=True)
    d.detail.wire(psu.output["+"], rail[1], wire=("RD", 0.75))
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 15, interface=True)
    r17 = d.terminal_strip("X2", "DEMO-TB-2.5").run("17", 1)
    with d.function("IN", "Inputs"):
        plc = d.device("K1", "DEMO-PLC-DI-16")
    for t, ch in ((9, 1), (6, 2), (3, 3), (12, 4), (15, 6), (2, 7)):
        d.detail.wire(x1[t].inner, plc[str(ch)], wire=("BK", 0.75))
    for t in (1, 4, 7, 10, 13):
        d.detail.wire(x1[t].inner, r17[1].inner, wire=("BK", 0.75))
    d.detail.wire(r17[1].outer, rail[2], wire=("RD", 0.75))
    for i in range(4):
        with d.function(f"S{i}", f"Sig {i}"):
            h = d.device(f"Q{i}", "DEMO-LAMP-24")
        d.detail.wire(x1[5].outer, h.lamp[1], wire=("BK", 0.75))
    return _Io(x1)


def test_the_wire_is_drawn_and_no_route_fails() -> None:
    """UNDO: stages/texts/power.py, `with_power_labels`: drop `lanes=port_lanes(placed)`."""
    d = fr.design("demo_parts")
    d.add(_shape, "U1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Shape\n", encoding="utf-8")
    built = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "shape", cover=cover))
    codes = {str(f.code) for f in built.findings}
    assert "ROUTE_FAILED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes
