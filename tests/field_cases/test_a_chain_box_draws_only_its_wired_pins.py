"""Field case: a chain member's unwired pin is not drawn, whatever the profile says.
The bug: none; the code was right and the expectation in layout-0215 was wrong (owner 2026-10-13).
Fixed by layout-0215 (amended, owner 2026-10-13): a chain box draws the pins that are wired, whatever the profile says."""

from itertools import pairwise

import fransys as fr
from _drawn_facts import symbol_subjects
from _model_build_cover import unit_document
from fransys.colours import BK, RD

from fransys_model.vocab.tables import ports


def _ports_drawn(*, hide: bool) -> dict[str, set[str]]:
    """Each module's drawn port names, over all drawn symbols, from a three-module chain."""
    d = fr.design("demo_parts", place="CAB")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    with d.function("PS", "Supply"):
        psu = d.device("T1", "DEMO-PSU-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    with d.function("CH", "Chain"):
        mods = [d.device(f"D{i}", "DEMO-MODULE-2P-COM4") for i in range(1, 4)]
    d.series(psu.output["-"], mods[0].pwr["minus"], wire=(BK, 1.0))
    d.series(psu.output["+"], mods[2].pwr["plus"], wire=(RD, 1.0))
    for a, b in pairwise(mods):
        d.series(a.pwr["plus"], b.pwr["minus"], wire=(RD, 1.0))
        for pin in "1234":
            d.series(a.OUT[pin], b.IN[pin], wire=(BK, 0.5))
    doc = unit_document(cab)
    model = fr.build(d, doc).model
    by_id = {p.id.value: p.id for p in ports(model).values()}
    drawn: dict[str, set[str]] = {}
    for one in symbol_subjects(model):
        names = set(one.sides) if one.sides else {fr.derive.port_designation(model, by_id[port]) for port in one.ports}
        drawn.setdefault(one.tag, set()).update(names)
    return drawn


def test_the_house_profile_draws_no_unwired_pin_of_a_chain_member() -> None:
    drawn = _ports_drawn(hide=False)
    assert any("-OUT:" in name for name in drawn["D1"])  # wired pins are drawn
    assert not [name for name in drawn["D1"] if "-IN:" in name]
    assert not [name for name in drawn["D3"] if "-OUT:" in name]
    assert any("-IN:" in name for name in drawn["D2"])
