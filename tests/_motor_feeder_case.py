"""The motor feeder case of P7.2: fan starters on a mains breaker, bundles of three poles (SW8).

The shape of the skid's G2 block from `examples/demo-skid`: a mains breaker feeds a strip, and
each starter runs breaker, contactor, overload and motor. Every function is wired, so today's
engine and the core draw the same functions. The motor is given its library symbol by a
`d.layout.symbol` hint, since `symbol_kit` has no pick for a motor on this base (KIT-FACTS).
"""

import tempfile
from pathlib import Path
from types import SimpleNamespace

import fransys as fr
from _page_drawings import page_drawings
from fransys.colours import BK, BU

from fransys_layout.core.score_wiring import crossing_points

__all__ = ["motor_feeder_case_drafts"]

POWER = (BK, 1.5)
CONTROL = (BU, 0.5)
MOTOR_PORTS = {"U": "u", "V": "v", "W": "w", "PE": "pe"}


def motor_feeder_case_drafts(starters: int = 3, *, control: bool = True) -> tuple:
    """The design and cabinet document of `starters` fan starters under one mains breaker."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G0", "Supply 24 V"):
        x10 = d.terminal_strip("X10", "DEMO-TB-2.5", 2)
        dc = d.dc_supply("24VDC", plus=x10[1], minus=x10[2], voltage=24)
    with d.function("G1", "Mains"):
        q0 = d.device("Q0", "DEMO-MCB-3P")
        x3 = d.terminal_strip("X3", "DEMO-TB-2.5", 3 * starters)
    with d.function("G2", "Fan starters"):
        for s in range(starters):
            f = d.device(f"F{3 + s}", "DEMO-MCB-3P")
            q = d.device(f"Q{3 + s}", "DEMO-CTR-3P-NC")
            ol = d.device(f"F{13 + s}", "DEMO-OVERLOAD-3P")
            m = d.device(f"M{1 + s}", "DEMO-MOTOR-4KW")
            h = d.device(f"H{3 + s}", "DEMO-LAMP-24")
            d.layout.symbol(m, "motor-3ph-pe", MOTOR_PORTS)
            d.layout.symbol(h, "lamp", {"1": "in", "2": "out"})
            for i, (a, b) in enumerate((("1", "2"), ("3", "4"), ("5", "6"))):
                t = x3[3 * s + i + 1]
                src = q0.element[b] if s == 0 else x3[3 * (s - 1) + i + 1].inner
                d.detail.wire(src, t.inner, wire=POWER)
                d.detail.wire(t.outer, f.element[a], wire=POWER)
                d.detail.wire(f.element[b], q.main[a], wire=POWER)
                d.detail.wire(q.main[b], ol.main[a], wire=POWER)
                d.detail.wire(ol.main[b], m.motor["UVW"[i]], wire=POWER)
            if control:
                d.series(dc.plus, ol.aux, q.aux_nc, q.coil, dc.minus, wire=CONTROL)
                d.series(dc.plus, q.aux, h.lamp, dc.minus, wire=CONTROL)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return d, doc


def feeder_counts(result) -> tuple[int, int]:
    """(references, crossings) of the pages the core path drew for `result` (SW8 row P7.2).

    References are the drawings' markers; crossings are points where a wire passes straight across
    another (`score_wiring.crossing_points`, one counter), page by page.
    """
    refs = crossings = 0
    for drawing in page_drawings(result).values():
        refs += len(drawing.markers)
        wires = [SimpleNamespace(net=w.id, page=0, points=w.points) for w in drawing.wires]
        crossings += len(crossing_points(wires))
    return refs, crossings
