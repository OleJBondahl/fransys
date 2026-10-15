"""Field case: a GNYE core to a device with no PE port still lands on the strip's PE terminal.

The engineering shape: a field box strip X1 with a PE part feeds a lamp H1 (a device with no PE
port) through a four-core cable W1: `d.series(dc.plus, x1, w1, h1.lamp, dc.minus)`.

The bug: the series marked the GNYE core spare, so the strip's PE terminal stayed unused and the
guide's "else open and earthed" never ran for the far end.

Rule (API-FRICTION-1 F9, author-0044): the core's near end lands on the strip's next free PE
terminal and its far end stays open, because the device has no PE port. Without a strip PE part
either, the core is spare.
"""

import fransys as fr
from fransys.colours import BK, GNYE

from fransys_model.vocab.tables import items, parts, ports

_PE_PART = "DEMO-TB-PE-2.5"


def _pe_terminal(model) -> str:
    """The designation of the strip's PE part terminal, read from the part, not its number."""
    (pe,) = {
        fr.derive.port_designation(model, port.id)
        for port in ports(model).values()
        if (item := items(model)[fr.derive.item_of_port(model, port.id)]).part
        and parts(model)[item.part].mpn == _PE_PART
    }
    return pe


def _pe_core(model) -> list[tuple[str, str, str]]:
    """The ends and the word of the GNYE core of W1, wired or open."""
    (cable,) = fr.derive.cable_items(model)
    wired = [
        (r.end_a_designation, r.end_b_designation, "")
        for r in fr.derive.cable_rows(model, cable)
        if r.colour == GNYE
    ]
    opened = [
        (r.at_designation, "", "spare" if r.spare else "")
        for r in fr.derive.open_core_rows(model, cable)
        if r.colour == GNYE
    ]
    return wired + opened


def test_the_core_lands_on_the_strips_pe_terminal_and_stays_open_at_the_lamp() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    d.series(dc.plus, x1, w1, d.device("H1", "DEMO-LAMP-24").lamp, dc.minus, wire=(BK, 0.75))
    model = fr.build(d).model
    assert _pe_core(model) == [(_pe_terminal(model), "", "")]
