"""Field case: a unit of 18 supply modules chained by their bus boxes, beside a part-less bridged strip that feeds the first and takes the last.
The bug (v0.22.4): the unit built alone drew a trunk through a terminal body (WIRE_THROUGH_BODY) and over another net; in a system it was clean.
Fixed by layout-0554 (KI-702, KI-699, R1793): the foreign clearance reads the y the page is drawn at, with the kept levels."""

from contextlib import nullcontext
from itertools import pairwise
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import _COVER
from fransys.colours import BK, BN, GN, RD, WH, YE

from fransys_model.kernel import id_namespace

COMMS = ((GN, 0.5), (WH, 0.5), (BN, 0.5), (YE, 0.5))


class _Io(NamedTuple):
    """No boundary device to hand back."""


@fr.unit("chain", revision=1, interface_version=1, date="2026-11-06", text="first", by="AB", title="Chain", number="N-1")
def _unit(d: Any) -> _Io:
    with d.function("A", "Feed"):
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
        f1, f2 = d.device("Q1", "DEMO-FUSE-DC-160"), d.device("Q2", "DEMO-FUSE-DC-160")
        d.series(x1[1].inner, f1.element, wire=(RD, 70))
        d.series(x1[2].inner, f2.element, wire=(BK, 70))
    with d.function("B", "Chain"):
        mods = [d.device(f"N{k}", "CHAIN-MODULE-48V-BUS") for k in range(1, 19)]
        d.series(f2.element, mods[0].pw, wire=(BK, 70))
        d.series(*(m.pw for m in mods), wire=(RD, 70))
        d.series(mods[-1].pw["P+"], f1.element[2], wire=(RD, 70))
        for lower, upper in pairwise(mods):
            d.series(lower.bus.pins[4:], upper.bus.pins[:4], wire=COMMS)
    with d.function("C", "Strip"):
        x2 = d.terminal_strip("X2", None, 8, bridged=((1, 2), (3, 4), (5, 6), (7, 8)), external=True, interface=(2, 4, 6, 8))
        d.series((x2[1].outer, x2[3].outer, x2[5].outer), mods[0].bus.pins[:3], wire=COMMS[:3])
        d.series(mods[-1].bus.OUT_3, x2[7].outer, wire=COMMS[3])
    with d.function("D", "Detector"):
        det = d.device("XX-XX", "CHAIN-GAS-DETECTOR", interface=True)
        d.series(det.sup[2], det.sig[6], wire=(BK, 0.75))
    return _Io()


@pytest.mark.timeout(600)  # the unit builds in about 150 s (KI-702); one salt, the fix is salt-independent
@pytest.mark.parametrize("salt", ["-"])
def test_the_unit_built_alone_draws_no_trunk_through_a_terminal_and_none_over_another_net(salt: str) -> None:
    d = fr.design("demo_parts", "chain_parts")
    d.add(_unit, "U1")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "chain", cover=_COVER)
    with id_namespace(salt) if salt != "-" else nullcontext():
        codes = [f.code for f in fr.check(fr.build(d, doc))]
    assert codes.count("WIRE_THROUGH_BODY") == 0
    assert codes.count("WIRE_MEETS_NET") == 0


@pytest.mark.timeout(600)  # KI-706: the same build; one salt per test, as the first
def test_the_unit_built_alone_draws_every_connection_and_places_every_marker() -> None:
    d = fr.design("demo_parts", "chain_parts")
    d.add(_unit, "U1")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "chain", cover=_COVER)
    codes = [f.code for f in fr.check(fr.build(d, doc))]
    assert codes.count("CONNECTION_NOT_DRAWN") == 0
    assert codes.count("MARKER_UNPLACED") == 0
