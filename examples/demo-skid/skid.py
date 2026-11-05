"""A demo skid: a mains breaker, fan starters, a PLC, and 16 valve relays with read-back.

The shapes of a small plant cabinet, drawn from invented `demo_parts` only. `design()` returns
the design and its cabinet document, scaled by `VALVES` and `STARTERS` so groups spill over pages.
"""

import math
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK, BU

VALVES = 16
STARTERS = 3
VALVE_BREAKER = 8  # the tag number of the valve group's breaker: no fan breaker takes it
POWER = (BK, 1.5)
CONTROL = (BU, 0.5)

Handle = Any  # fransys exports no name for the run and device handles `d.*` returns


def supply(d: fr.Design, terminals: int) -> tuple[Handle, Handle]:
    """Group G0: a 24 V supply on two bridged strips, sized to the terminals the skid wires."""
    with d.function("G0", "Supply 24 V"):
        live = d.terminal_strip("X10", "DEMO-TB-2.5", terminals).run("P", terminals, bridged=True, rail=True)
        rail = d.terminal_strip("X11", "DEMO-TB-2.5", terminals).run("M", terminals, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
    return live, rail


def starters(d: fr.Design, live: Handle, rail: Handle) -> list[tuple[Handle, Handle]]:
    """Groups G1 and G2: the mains breaker, its strip, and one fan starter per strip row."""
    with d.function("G1", "Mains"):
        q0 = d.device("Q0", "DEMO-MCB-3P")
        x3 = d.terminal_strip("X3", "DEMO-TB-2.5-TWIN", 3 * STARTERS)
    made = []
    breakers = [n for n in range(3, 4 + STARTERS) if n != VALVE_BREAKER][:STARTERS]
    first_overload = max(13, breakers[-1] + 1)  # the overloads follow the breakers at any size
    with d.function("G2", "Fan starters"):
        for s in range(STARTERS):
            f = d.device(f"F{breakers[s]}", "DEMO-MCB-3P")
            q = d.device(f"Q{3 + s}", "DEMO-CTR-3P-NC")
            ol = d.device(f"F{first_overload + s}", "DEMO-OVERLOAD-3P")
            mo = d.device(f"M{1 + s}", "DEMO-MOTOR-4KW")
            h = d.device(f"H{3 + s}", "DEMO-LAMP-24")
            if s == 0:
                d.series(q0.element, x3, f.element, q.main, ol.main, mo.motor, wire=POWER)
            else:
                d.series(f.element, q.main, ol.main, mo.motor, wire=POWER)
                for pole in (1, 2, 3):  # the row jumpers: each terminal feeds the next row's
                    d.series(x3[3 * s + pole - 3].inner, x3[3 * s + pole].inner, wire=POWER)
                    # a series from a strip leaves inner; the fuse is fed from the outer side
                    d.series(x3[3 * s + pole].outer, f.element[str(2 * pole - 1)], wire=POWER)
            d.series(live, q.aux, h.lamp, rail, wire=CONTROL)
            d.series(q.coil, rail, wire=CONTROL)
            made.append((q, ol))
    return made


def valves(d: fr.Design, live: Handle, rail: Handle, chans: list[Handle]) -> list[Handle]:
    """Groups G4 and G5: valve relays behind one breaker, their contacts in a Valves group."""
    with d.function("G4", "Valve relays"):
        f8 = d.device("F8", "DEMO-MCB-C6")
        d.series(live, f8.element, wire=CONTROL)
        relays = [d.device(f"K{i + 4}", "DEMO-RLY-2CO-24") for i in range(VALVES)]
    with d.function("G5", "Valves"):
        lamps = [d.device(f"Y{i + 4}", "DEMO-LAMP-24") for i in range(VALVES)]
    for i, (k, y) in enumerate(zip(relays, lamps, strict=True)):
        d.series(chans[STARTERS + i], k.coil, rail, wire=CONTROL)
        d.series(f8.element, k.co_1.no, y.lamp, rail, wire=CONTROL)
    return relays


class Skid(NamedTuple):
    """The skid unit's interface: nothing is reached from outside, the cabinet stands alone."""


@fr.unit(
    "demo-skid",
    revision=1,
    interface_version=1,
    date="2026-10-15",
    text="First issue",
    by="OJB",
    title="Skid",
    number="P-1",
)
def skid(d: fr.Design) -> Skid:
    """The skid cabinet as one unit: its parts, groups and wires."""
    live, rail = supply(d, 4 + 2 * STARTERS + 2 * VALVES)
    fans = starters(d, live, rail)
    channels = STARTERS + VALVES
    with d.function("G3", "PLC"):
        di = d.device("DI1", "DEMO-PLC-DI-16")
        d.device("AI1", "DEMO-PLC-AI-4", unused=True)  # no wire reaches the analogue cards: spare
        d.device("AI2", "DEMO-PLC-AI-4", unused=True)
        dos = [d.device(f"DO{i + 1}", "DEMO-PLC-DO-2") for i in range(math.ceil(channels / 2))]
    chans = [getattr(dos[c // 2], f"do_{c % 2 + 1}") for c in range(channels)]
    relays = valves(d, live, rail, chans)
    for (q, _), chan in zip(fans, chans, strict=False):
        d.series(chan, q.coil, wire=CONTROL)
    reads = [c for q, ol in fans for c in (q.aux_nc, ol.aux)] + [k.co_2.no for k in relays]
    for i, contact in enumerate(reads[:16]):
        d.series(live, contact, getattr(di, f"di_{i + 1}"), wire=CONTROL)
    return Skid()


def design() -> tuple[fr.Design, fr.Draft]:
    """The skid's `(design, document)` pair: the skid unit added as U1 to a cabinet design."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Skid", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    d.add(skid, "U1", place="CAB")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Skid\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-skid", cover=cover)
