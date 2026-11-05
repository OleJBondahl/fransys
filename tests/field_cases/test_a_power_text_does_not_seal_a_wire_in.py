"""Field case: a 15-terminal interface strip with a stacked one-terminal run whose port carries a 24V supply symbol, beside a signal net.
The bug: the taller box grew a keep-out until the "24V" text sat on the lane the wire leaves by, and the router sealed the wire in.
Fixed by layout-0196, no text stands on a port's exit lane, and the power placer is given the lanes (CONNECTION_NOT_DRAWN)."""

from typing import NamedTuple

import fransys as fr
from _model_build_cover import unit_document


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
    rail = d.terminal_strip("X3", "DEMO-TB-2.5").run("24V", 2, bridged=True, rail=True)
    d.series(psu.output["+"], rail[1], wire=("RD", 0.75))
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 15, interface=True)
    r17 = d.terminal_strip("X2", "DEMO-TB-2.5-TWIN").run("17", 3, bridged=True)
    with d.function("IN", "Inputs"):
        plc = d.device("K1", "DEMO-PLC-DI-16")
    for t, ch in ((9, 1), (6, 2), (3, 3), (12, 4), (15, 6), (2, 7)):
        d.series(x1[t].inner, plc[str(ch)], wire=("BK", 0.75))
    for t, n in ((1, 1), (4, 1), (7, 2), (10, 2), (13, 3)):
        d.series(x1[t].inner, r17[n].inner, wire=("BK", 0.75))
    d.series(r17[1].outer, rail[2], wire=("RD", 0.75))
    prev = x1[5].outer
    for i in range(4):
        with d.function(f"S{i}", f"Sig {i}"):
            h = d.device(f"Q{i}", "DEMO-LAMP-24")
        d.series(prev, h.lamp[1], wire=("BK", 0.75))
        prev = h.lamp[1]
        d.series(h.lamp[2], d.device(f"G{i}", None, external=True, pins=("P",)).P, wire=("BK", 0.75))
    return _Io(x1)


def test_the_wire_is_drawn_and_no_route_fails() -> None:
    """UNDO: stages/texts/power.py, `with_power_labels`: drop `lanes=port_lanes(placed)`."""
    d = fr.design("demo_parts")
    d.add(_shape, "U1")
    built = fr.build(d, unit_document("shape"))
    codes = {str(f.code) for f in built.findings}
    assert "CONNECTION_NOT_DRAWN" not in codes
