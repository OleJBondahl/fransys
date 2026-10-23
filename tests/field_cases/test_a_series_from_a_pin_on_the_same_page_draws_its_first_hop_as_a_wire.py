"""Field case: a series that starts at a pin of an element drawn on the same page is a wire.

The engineering shape: a relay changeover K1 on the 24 V rail. Its make throw feeds coil K2
through the chain K1:14 to K2:A1. Its break throw (K1:12) starts a second series, which ends at
coil K3, so the hop K1:12 to K3:A1 leaves a bottom pin and enters a top pin of another column.

The bug: K3 stood at the top of its own column, above K1:12, so the hop would turn back round K1
and was drawn as a cross-reference pair (`#1-1B`, `#1-2A`) on the same page, not as a wire.
The rule (SAME-PAGE-BRANCH, owner "vertical circuits, refs only at ends", 2026-09-23):
the hop is a wire that never climbs back; only a hop that leaves the page is a marker pair.
D2 (2026-10-05) is kept: a marker that is still drawn prints the cell alone.

Fixing decision: layout-0224.
"""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages


class _Io(NamedTuple):
    G1: fr.Device


def _design() -> fr.Design:
    """The circuit above as one unit."""

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
        g1 = u.device("G1", "DEMO-PSU-24")
        dc = u.dc_supply("24VDC", g1)
        k1 = u.device("K1", "DEMO-RLY-2CO-24")
        k2 = u.device("K2", "DEMO-CTR-3P-24")
        k3 = u.device("K3", "DEMO-RLY-2CO-24")
        u.series(dc.plus, k1.co_1.no, k2.coil, dc.minus, wire=0.75)
        u.series(k1.co_1.nc, k3.coil, dc.minus, wire=0.75)
        return _Io(g1)

    d = fr.design("demo_parts")
    d.add(shape, "U1")
    return d


def _built():
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Shape\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "shape", cover=cover)
    return fr.build(_design(), document).model


def _hop(model):
    """The wire that leaves K1's break throw (below the contact) for K3's coil, or `None`."""
    ((page,),) = [[d] for d in drawn_pages(model).values()]
    (k1,) = (s for s in page.symbols if s.key == "change-over-contact")
    for wire in page.wires:
        if any(x == k1.x and y > k1.y + 8 for x, y in wire.points):
            return wire
    return None


def test_the_hop_from_the_break_throw_to_the_second_coil_is_a_wire() -> None:
    """No marker stands on the page, and the hop is a wire."""
    # UNDO: references/hung.py `hung_joins`: return `joins` unchanged
    model = _built()
    ((page,),) = [[d] for d in drawn_pages(model).values()]
    assert not [s for s in page.symbols if s.key == "reference-marker"]
    assert _hop(model) is not None


def test_the_hop_runs_downward_and_never_climbs_back() -> None:
    """Its points never rise above the pin it leaves: no 180 degree turn round K1."""
    route = _hop(_built())
    assert route is not None
    ys = [y for _, y in route.points]
    assert ys in (sorted(ys), sorted(ys, reverse=True))  # `a` to `b` is in id order
