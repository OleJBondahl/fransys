"""Field case (KI-1453, fixed by RAIL-CLOSURE, designer R3871): a plug mated to a child unit's connector, its pins wired by one series to
two bridged strips flagged as rails. The plug pins were cut from the stands, so the wire to the rail terminal had no drawer.
Unmated plug or no rail flag is clean."""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-11-24", "text": "First", "by": "XX"}


class _Io(NamedTuple):
    c: fr.Device


@fr.unit("rail-plug-child", **_REL)
def _child(u: fr.Design) -> _Io:
    return _Io(u.device("C", "DEMO-CONN-2P", interface=True))


@fr.unit("rail-plug-parent", **_REL)
def _parent(u: fr.Design) -> _Io:
    child = u.add(_child, "B1")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 2, bridged=True, rail=True)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5").run("GND", 2, bridged=True, rail=True)
    u.dc_supply("24V", plus=x1[1], minus=x2[1], voltage=24, names=("24V", "GND"))
    plug = u.device("J1", "DEMO-CONN-2P")
    u.mate(plug, child.c)
    u.series((x1[2], x2[2]), (plug["1"], plug["2"]), wire=(("RD", 0.5), ("BK", 0.5)))
    return _Io(child.c)


def test_a_mated_plug_wired_to_rail_terminals_draws_every_end() -> None:
    """KI-1453: no plug pin end is left undrawn."""
    d = fr.design("demo_parts", "mate_parts")
    result = fr.build(d, unit_document(d.add(_parent, "U1")))
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in result.findings}


def test_a_mated_pin_that_stands_draws_its_conductor_end_once() -> None:
    """KI-1453: a child pin whose mate stands and whose conductor ends at a rail terminal has one power symbol and one wire end at its lead tip."""
    d = fr.design("demo_parts", "mate_parts")
    drawings = fr.build(d, unit_document(d.add(_parent, "U1"))).drawings.values()
    stood = 0
    for drawing in drawings:
        for pin in (s for s in drawing.symbols if s.key == "connector-fixed"):
            box = pin.outline
            assert box is not None
            stands = [s for s in drawing.symbols if s.key in ("ground", "power-supply") and set(s.ports) & set(pin.ports)]
            tips = {(pin.x, box.y), (pin.x, box.y + box.h)}
            ends = [p for w in drawing.wires for p in (w.points[0], w.points[-1]) if p in tips]
            assert len(stands) == len(ends) <= 1
            stood += len(stands)
    assert stood == 2
