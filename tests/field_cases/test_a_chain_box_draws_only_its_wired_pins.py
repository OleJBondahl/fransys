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
from _drawn_facts import symbol_subjects
from fransys.colours import BK, RD

from fransys_model.vocab.tables import ports


def _ports_drawn(*, hide: bool) -> dict[str, set[str]]:
    """Each module's drawn port names, over all drawn symbols, from a three-module chain."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    with d.function("CH", "Chain"):
        mods = [d.device(f"D{i}", "DEMO-MODULE-2P-COM4") for i in range(1, 4)]
    for a, b in pairwise(mods):
        d.detail.wire(a.pwr["plus"], b.pwr["minus"], wire=(RD, 1.0))
        for pin in "1234":
            d.detail.wire(a.OUT[pin], b.IN[pin], wire=(BK, 0.5))
    cover = pathlib.Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# cover\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    by_id = {p.id.value: p.id for p in ports(model).values()}
    drawn: dict[str, set[str]] = {}
    for one in symbol_subjects(model):
        if one.sides:
            names = set(one.sides)
        else:
            names = {fr.derive.port_designation(model, by_id[port]) for port in one.ports}
        drawn.setdefault(one.tag, set()).update(names)
    return drawn


def test_the_house_profile_draws_no_unwired_pin_of_a_chain_member() -> None:
    drawn = _ports_drawn(hide=False)
    assert any("-OUT:" in name for name in drawn["D1"])  # wired pins are drawn
    assert not [name for name in drawn["D1"] if "-IN:" in name]
    assert not [name for name in drawn["D3"] if "-OUT:" in name]
    assert any("-IN:" in name for name in drawn["D2"])
