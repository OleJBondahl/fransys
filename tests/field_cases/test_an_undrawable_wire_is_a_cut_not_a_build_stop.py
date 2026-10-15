"""Field case: a wire the router cannot draw is a cut with a finding, never a build stop.

The engineering shape: a terminal strip X1 with a bridged run of three terminals. Four function
blocks each hold two relays whose coils are wired from the run, whose contacts feed a lamp from the
run, and whose other coil pin returns to one strip terminal. One relay of the first block is
advised into the fourth block with `d.layout.draw_in`, so its coil stands in a group whose other
cells share the same run terminals.

The bug: two wires of the run, at the coil pins of relays of the other blocks, were neither drawn
nor cut. The lint reported `CONNECTION_NOT_DRAWN` as an ERROR, so `fr.write` refused the whole
build. The same family of circuits raised `LayoutError` ("two LinkMarker records share one key",
`write/unique.py`) or `ROUTE_FAILED` in a consumer's larger module (3.9 mm); here the first
failure shows at the house module.
The rule (LEGACY-B3 L1): a wire the router cannot draw becomes a cut, a marker pair at its two
ends, with a finding naming the wire; two link markers never share a key; no new ERROR.

Fixed in layout-0189: a terminal echo counts only a terminal of the wire's own chain, so a terminal
that shares the net across a bridge no longer hides the wire's link marker pair.
"""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr

_FUNCTIONS = 4
_RELAYS = 2
_STOPS = {"CONNECTION_NOT_DRAWN", "ROUTE_FAILED"}


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
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=True)
        feed = x1.run("feed", 3, bridged=True)
        relays = []
        groups = []
        for i in range(_FUNCTIONS):
            with u.function(f"F{i + 1}", f"Function {i + 1}") as group:
                for j in range(_RELAYS):
                    k = u.device(f"K{i + 1}{j + 1}", "DEMO-RLY-2CO-24")
                    h = u.device(f"H{i + 1}{j + 1}", "DEMO-LAMP-24")
                    u.detail.wire(feed[1 + (i + j) % 3], k.coil["A1"], wire=("RD", 0.75))
                    u.detail.wire(x1[4], k.coil["A2"], wire=("BU", 0.75))
                    u.detail.wire(feed[1 + (i + j + 1) % 3], k.co_1["11"], wire=("RD", 0.75))
                    u.detail.wire(k.co_1["14"], h.lamp[1], wire=("RD", 0.75))
                    u.detail.wire(h.lamp[2], x1[4], wire=("BU", 0.75))
                    relays.append(k)
            groups.append(group)
        u.layout.draw_in(relays[1].coil, groups[-1])
        return _Io(x1)

    d = fr.design("demo_parts")
    d.add(shape, "U1")
    return d


def test_an_undrawable_wire_is_a_cut_and_never_stops_the_build() -> None:
    """The build completes, no wire is left undrawn, and no ERROR stops the export."""
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Shape\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "shape", cover=cover)
    result = fr.build(_shape(), document)  # a LayoutError here is the other face of the bug
    undrawn = [f for f in result.findings if f.code in _STOPS]
    assert not undrawn, [(f.code, f.message) for f in undrawn]
    assert not [f for f in result.findings if f.severity is fr.Severity.ERROR]
