"""Field case: an open core on a PE-role port whose net is a loose control wire is a spare.

The engineering shape: a motor M1 has a PE pin. A loose wire runs from that pin to a terminal of a
plain strip, so the pin is on no PE net. The GNYE core of cable W1 is parked open on that pin.

The bug: `open_core_is_spare` called the core earthed because the port's role is PE, so the row
said "not a spare", and `PE_PORT_OFF_PE` stayed silent because no declared net listed the net.

Rule (G2, EARTH-04, EARTH-05): "earthed" means "on the PE net". The core is a spare, and
`PE_PORT_OFF_PE` fires on any non-PE physical net, a loose wire included.
"""

import fransys as fr
from fransys.colours import BK, GNYE


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    d.detail.wire(m1.motor["PE"], x1[1], wire=(BK, 1.5))
    w1.spare(GNYE, at=m1.motor["PE"])
    return fr.build(d)


def test_the_core_is_listed_as_a_spare() -> None:
    model = _build().model
    (cable,) = fr.derive.cable_items(model)
    (row,) = fr.derive.open_core_rows(model, cable)
    assert (row.colour, row.spare) == (GNYE, True)


def test_the_port_off_the_pe_net_gives_the_warning() -> None:
    found = [f for f in fr.check(_build()) if f.code == "PE_PORT_OFF_PE"]
    assert [f.severity.name for f in found] == ["WARNING"]
