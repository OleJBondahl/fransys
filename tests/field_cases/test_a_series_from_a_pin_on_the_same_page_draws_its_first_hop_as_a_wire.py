"""Field case: a relay changeover K1 whose break throw starts a series ending at coil K3, which stands at the top of its own column.
The bug: the hop K1:12 to K3:A1 would turn back round K1, so it was drawn as a same-page cross-reference pair (#1-1B, #1-2A), not as a wire.
Fixed by layout-0224 (SAME-PAGE-BRANCH), the hop is a wire that never climbs back; only a hop that leaves the page is a marker pair."""

from typing import NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document


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
    document = unit_document("shape")
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
