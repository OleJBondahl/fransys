"""Field case: an unbridged terminal fed to a supply's input, the supply standing over the module it feeds.
The bug: the terminal's net fell to a cross-link and no cell was dealt it (NO_CELL); fixed by layout-0486 (R1167)."""

import tempfile
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BN, BU

CORRECTNESS = {"NO_CELL", "CONNECTION_NOT_DRAWN", "DANGLING_WIRE_END"}


def _built(mpn: str, plus: str, minus: str, *, hide: bool):
    """Two supplies of `mpn` fed from unbridged terminals into one redundancy module."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    ac = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    live, neutral = ac.run("L", 2), ac.run("N", 2)
    with d.function("G", "Supply"):
        m1 = d.device("M1", "DEMO-RED-2IN")
        psus = [d.device(f"G{n}", mpn) for n in (1, 2)]
    for n, psu in enumerate(psus, start=1):
        d.series(live[n].outer, psu.input["L"], wire=(BN, 1.5))
        d.series(neutral[n].outer, psu.input["N"], wire=(BU, 1.5))
        group = getattr(m1, f"in_{n}")
        d.series(psu.output[plus], group[f"{n}+"], wire=(BN, 1.5))
        d.series(psu.output[minus], group[f"{n}-"], wire=(BU, 1.5))
    rail = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    d.dc_supply("S", plus=m1.out["+"], minus=m1.out["-"], voltage=24)
    d.series(m1.out["+"], rail.run("P", 2, bridged=True, rail=True)[1].outer, wire=(BN, 1.5))
    d.series(m1.out["-"], rail.run("M", 2, bridged=True, rail=True)[1].outer, wire=(BU, 1.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


@pytest.mark.parametrize(
    ("mpn", "plus", "minus", "hide"),
    [pytest.param("DEMO-PSU-24", "+", "-", False, id="two-feeders")],  # two feeders with terminal chains
)
def test_every_terminal_of_an_unbridged_run_is_drawn(mpn: str, plus: str, minus: str, *, hide: bool) -> None:
    """No NO_CELL, undrawn connection, dangling wire end or failed route."""
    found = {f.code for f in _built(mpn, plus, minus, hide=hide).findings}
    assert not found & CORRECTNESS
