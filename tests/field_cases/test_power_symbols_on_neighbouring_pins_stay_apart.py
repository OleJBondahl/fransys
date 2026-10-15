"""A supply bar and a ground triangle on neighbouring connector pins touch, a harness line beside.

Engineering shape: a cabinet whose interface connector, mated to a harness, carries a 24V supply
on pin 1 and the 0V return on pin 2. The harness line stands at the connector's side.

The bug: the two power symbols were placed on adjacent pins with their closed boxes sharing an
edge, and the harness line ran along the ground triangle's edge. Render drew two nets joined
(DRAWING_SHORTS_NETS).

Fixed by layout-0245: a pin view that moves under its cell gets its power leads set again.
"""

from typing import NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK, BN, BU

from fransys_model.layout import HarnessLine, PowerSymbol, layout_of

CTRL = (BU, 0.75)


class _Io(NamedTuple):
    j1: fr.Device


@fr.unit(
    "shape", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
    title="Shape", number="S-1", class_code="U",
)  # fmt: skip
def _shape(c):
    q0 = c.device("Q0", None, external=True, pins=("L", "N"))
    mains = c.ac_supply("230V", 230, q0["L"], n=q0["N"])
    g1 = c.device("G1", "DEMO-PSU-24")
    c.series(mains.L1, g1.input, wire=(BK, 1.5))
    c.detail.wire(q0["N"], g1.input["N"], wire=(BU, 1.5))
    c.dc_supply("24VDC", g1.output)
    j1 = c.device("J1", "DEMO-CONN-4P", interface=True)
    c.detail.wire(g1.output["+"], j1[1], wire=CTRL)
    c.detail.wire(g1.output["-"], j1[2], wire=CTRL)
    return _Io(j1)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    d = fr.design("demo_parts")
    unit = d.add(_shape, "U1")
    loom = d.harness("W1")
    cable = d.cable("C1", "DEMO-CBL-4G1.5", length_m=5, parent=loom)
    p1 = d.device("P1", "DEMO-HSG-4F", parent=loom)
    p2 = d.device("P2", "DEMO-HSG-4F", parent=loom)
    d.mate(p1, unit.j1)
    cable.core(BN, p1[1], p2[1])
    cable.core(BK, p1[2], p2[2])
    cover = tmp_path_factory.mktemp("shape") / "cover.md"
    cover.write_text("# Shape\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "shape", cover=cover))


def _shorts(built: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(built) if f.code == "DRAWING_SHORTS_NETS"]


def test_neighbouring_power_symbols_stand_apart(built: fr.BuildResult) -> None:
    symbols = {one.port for one in layout_of(built.model, PowerSymbol).values()}
    assert len(symbols) >= 2, "both power symbols are drawn"
    assert [f for f in _shorts(built) if set(f.subjects) <= symbols] == []


def test_neighbouring_power_symbols_and_a_harness_line_draw_no_short(built: fr.BuildResult) -> None:
    assert layout_of(built.model, HarnessLine)
    assert _shorts(built) == []
