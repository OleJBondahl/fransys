"""Field case: a wire the router cannot draw is a cut with a finding, never a build stop.
The bug: two wires of a run were neither drawn nor cut, and the CONNECTION_NOT_DRAWN ERROR made fr.write refuse the whole build.
Fixed by layout-0189 (LEGACY-B3 L1), an undrawable wire becomes a cut with a marker pair and a finding; no new ERROR."""

from typing import NamedTuple

import fransys as fr
from _model_build_cover import unit_document

_FUNCTIONS = 4
_RELAYS = 2
_STOPS = {"CONNECTION_NOT_DRAWN"}


class _Io(NamedTuple):
    X1: fr.TerminalStrip


def _shape() -> fr.Design:
    """The circuit above, as one unit, at the house profile."""

    @fr.unit(
        "shape",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="first",
        by="AB",
        title="Shape",
        number="S-1",
    )
    def shape(u: fr.Design) -> _Io:
        n = _FUNCTIONS * _RELAYS  # R1266: a feed point takes two conductors, so the run has a twin terminal for each pair
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", n + 1, interface=True)
        feed = x1.run("feed", n, bridged=True)
        common = x1[n + 1].inner  # the common point takes one conductor: its wires chain from pin to pin
        for i in range(_FUNCTIONS):
            with u.function(f"F{i + 1}", f"Function {i + 1}"):
                for j in range(_RELAYS):
                    k = u.device(f"K{i + 1}{j + 1}", "DEMO-RLY-2CO-24")
                    h = u.device(f"H{i + 1}{j + 1}", "DEMO-LAMP-24")
                    u.series(feed[1 + i * _RELAYS + j].inner, k.coil["A1"], wire=("RD", 0.75))
                    u.series(common, k.coil["A2"], wire=("BU", 0.75))
                    u.series(feed[1 + (i * _RELAYS + j + 1) % n].inner, k.co_1["11"], wire=("RD", 0.75))
                    u.series(k.co_1["14"], h.lamp[1], wire=("RD", 0.75))
                    u.series(h.lamp[2], k.coil["A2"], wire=("BU", 0.75))
                    common = h.lamp[2]
        return _Io(x1)

    d = fr.design("demo_parts")
    d.add(shape, "U1")
    return d


def test_an_undrawable_wire_is_a_cut_and_never_stops_the_build() -> None:
    """The build completes, no wire is left undrawn, and no ERROR stops the export."""
    document = unit_document("shape")
    result = fr.build(_shape(), document)  # a LayoutError here is the other face of the bug
    undrawn = [f for f in result.findings if f.code in _STOPS]
    assert not undrawn, [(f.code, f.message) for f in undrawn]
    assert not [f for f in result.findings if f.severity is fr.Severity.ERROR]
