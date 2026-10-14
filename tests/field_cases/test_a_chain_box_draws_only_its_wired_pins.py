"""Field case: a chain member's unwired pin is not drawn, whatever the profile says.

The engineering shape: a block holds a daisy chain of three two-port modules (a power pass-through
and a 4-pin IN and OUT comms pair). Module n's OUT pins and plus go to module n+1; the first
module's IN connector and the last one's OUT connector are wired to nothing.

The rule (owner 2026-10-13, spec LONG-CHAIN LC2 amendment 1): a chain box draws the pins that are
wired. The house profile (`hide_unused_pins=False`) does not bring the idle ones back.

Fixed by: nothing; the code was right (owner 2026-10-13) and layout-0215 was amended.
"""

import pathlib
import tempfile
from itertools import pairwise

import fransys as fr
from fransys.colours import BK, RD
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import items


def _ports_drawn(*, hide: bool) -> dict[str, set[str]]:
    """Each module's drawn port names, over all placements, from a three-module chain."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    with d.function("CH", "Chain"):
        mods = [d.device(f"D{i}", "DEMO-MODULE-2P-COM4") for i in range(1, 4)]
    for a, b in pairwise(mods):
        d.wire(a.pwr["plus"], b.pwr["minus"], wire=(RD, 1.0))
        for pin in "1234":
            d.wire(a.OUT[pin], b.IN[pin], wire=(BK, 0.5))
    cover = pathlib.Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# cover\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    tag_of = {one.id: one.tag for one in items(model).values()}
    drawn: dict[str, set[str]] = {}
    for one in results.layout.placed:
        tag = tag_of.get(one.function)
        if tag is not None:
            drawn.setdefault(tag, set()).update(g.name for g in one.geometry.ports)
    return drawn


def test_the_house_profile_draws_no_unwired_pin_of_a_chain_member() -> None:
    drawn = _ports_drawn(hide=False)
    assert any(name.startswith("OUT") for name in drawn["D1"])  # wired pins are drawn
    assert not [name for name in drawn["D1"] if name.startswith("IN")]
    assert not [name for name in drawn["D3"] if name.startswith("OUT")]
    assert any(name.startswith("IN") for name in drawn["D2"])
