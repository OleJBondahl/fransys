"""Field case: three relay coils whose A1 terminals share one net with one digital input channel.

The engineering shape: three relays each have a coil whose A1 terminal is hand-wired to the same
net as one channel of a four-channel input module. Each coil asks for a digital input name, so
the net holds the channel and three requests that all pick that one channel.

Seen on main at 191631b3a: no PLC_REQUEST_AMBIGUOUS, but PLC_BINDING_WIRING_MISMATCH for K2 and
K3, each bound to the channel A1 that K1 also holds.

The ruling (designer, 2026-10-14, for 0.18, PLC-CONTESTED): two or more kind-matched requests
whose wired pick is the same channel get one PLC_CHANNEL_CONTESTED (ERROR) naming them all, bind
nothing and do not go to the free queue (model-0211 amendment, to come). Strict xfail until then.

The second test is the true model of the legacy circuit: only one coil asks. It binds the wired
channel with no finding.
"""

import fransys as fr
import pytest
from fransys.colours import BK

INFO_CODES = {"ITEM_WITHOUT_PART", "PORT_UNCONNECTED"}


@pytest.mark.xfail(strict=True, reason="until PLC-CONTESTED (0.18)")
def test_three_coil_requests_on_one_channel_are_contested() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    for n in (1, 2, 3):
        coil = d.device(f"K{n}", "DEMO-CO-4P-24")
        d.wire(coil.coil["A1"], di.di_1["1"], wire=(BK, 1.0))
        coil.coil.plc(fr.DI, f"K{n} coil")
    findings = [f for f in fr.check(fr.build(d)) if f.code not in INFO_CODES]
    assert [f.code for f in findings] == ["PLC_CHANNEL_CONTESTED"]
    assert findings[0].severity is fr.Severity.ERROR
    assert all(f"-K{n}" in findings[0].message for n in (1, 2, 3))


def test_one_request_among_three_coils_on_a_net_binds_the_wired_channel_without_a_finding() -> None:
    """True model of the legacy circuit: only K1 asks; K2 and K3 share the net but ask for nothing.

    The wired channel is the second one, so a bind by the free queue (first channel) would differ.
    """
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    coils = [d.device(f"K{n}", "DEMO-CO-4P-24") for n in (1, 2, 3)]
    for coil in coils:
        d.wire(coil.coil["A1"], di.di_2["2"], wire=(BK, 1.0))
    coils[0].coil.plc(fr.DI, "Contactors closed")
    build = fr.build(d)
    findings = [f for f in fr.check(build) if f.code not in INFO_CODES]
    assert findings == []
    named = {row.pin: row.signal_name for row in fr.derive.plc_channel_rows(build.model)}
    assert named["-A1:2"] == "Contactors closed"
