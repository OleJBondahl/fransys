"""Field case: adjacent contacts under PLC input channels, each fed from the 24 V rail.

The engineering shape: a PLC input module with three wired channels, and three contactors whose
auxiliary make contacts each return on one channel and are fed on the other pin from a DC
supply's plus rail. Each contact stands under its channel, so the contacts form a row, and each
fed pin draws a power-supply symbol on a lead pointing down.

The bug (found on a pump cabinet's feedback contacts): neighbouring contact columns are wider than
their channel pitch, so a fed pin stands inside the keepout of the contact beside it. The lead,
which starts one unit behind the pin, crossed that keepout's flush edge by one unit at every
length, so no lead of up to 12 grids cleared and `POWER_SYMBOL_UNPLACED` warned, once per such
contact.

Decision: layout-0222: a lead is checked from its first unit out.
"""

from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BU, RD

if TYPE_CHECKING:
    from pathlib import Path


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G0", "PLC group"):
        module = d.device("K1", "DEMO-PLC-DI-4P")
        psu = d.device("T1", "DEMO-PSU-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    with d.function("G1", "Contactor group") as group:
        lamps = {n: d.device(f"P{n}", "DEMO-LAMP-24") for n in (2, 3, 4)}
        contactors = {n: d.device(f"K{n}", "DEMO-CTR-3P-NC") for n in (2, 3, 4)}
    d.layout.break_before(group)
    for number, contactor in contactors.items():
        d.detail.wire(contactor.coil["A1"], lamps[number].lamp["1"], wire=(BU, 0.5))
        d.detail.wire(contactor.main["1"], lamps[number].lamp["1"], wire=(BU, 0.5))
        d.detail.wire(psu.output["+"], contactor.aux["13"], wire=(RD, 0.5))
        channel = getattr(module, f"di_{number - 1}")[str(number - 1)]
        d.detail.wire(contactor.aux["14"], channel, wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def test_every_power_symbol_of_a_contact_row_is_placed(tmp_path: Path) -> None:
    """No fed contact pin leaves its power symbol unplaced."""
    codes = [f.code for f in fr.check(_build(tmp_path))]
    assert "POWER_SYMBOL_UNPLACED" not in codes
