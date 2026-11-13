"""Field case: a relay coil wired to a bottom-edge pin of a DI module, with a two-pin switch pair on pins 9 and 10.
KI-902 (LANE_WIRE_DROPPED) is fixed by FUSE-TERMINAL; that revealed the old DRAWING_SHORTS_NETS of KI-947 (-G1:- and -DI1:15),
fixed by the guard's hand-off keeping only pins of the wire's own net (SHORT-G1-DI1)."""

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

_W = (BU, 0.75)


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    xf = d.terminal_strip("XF", "DEMO-TB-FUSE-2.5")
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5")
    with d.function("SUP", "Supply"):
        for n in (1, 2):
            d.series(dc.plus, xf[n].inner, wire=_W)
    with d.function("CTL", "Control"):
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        d.series(xf[2].outer, k1.coil, dc.minus, wire=_W)
    with d.function("DI", "PLC inputs"):
        di = d.device("DI1", "DEMO-PLC-DI-16")
        d.series(k1.coil.A1, di["15"], wire=_W)
        cv = d.device("CV01", "DEMO-ACT-4P-2SW")
        d.series(di["9"], cv.sw_1, wire=_W)
        d.series(x2[1].outer, cv.sw_1[5], wire=_W)
        d.series(di["10"], cv.sw_2, wire=_W)
        d.series(x2[2].outer, cv.sw_2[7], wire=_W)
    return fr.build(d, cabinet_document(cab))


def test_a_coil_on_a_bottom_pin_of_a_di_module_builds_with_no_error() -> None:
    errors = [f.code for f in _build().findings if f.severity.name == "ERROR"]
    assert errors == []
