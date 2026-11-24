"""Field case: ten changeover relays on one 24 V source, each make contact feeding its own fuse and lamp.
The bug: the fault reader held the items above eight at rest, so two fuses read 0 A against the source's 6000 A and the breaking check missed them.
Fixed by FAULT-CHAIN (designer R3676): a position's value is walked over the stateful items of its own chain."""

from decimal import Decimal

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BU

_RELAYS = 10
_WIRE = (BU, 0.5)


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", "fault_chain_parts", place="PLANT")
    d.location("PLANT", "Plant room")
    psu = d.device("T1", "FC-PSU-24-6KA")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    dc = d.dc_supply("S", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    for i in range(1, _RELAYS + 1):
        relay = d.device(f"K{i}", "DEMO-RLY-2CO-24")
        fuse = d.device(f"F{i}", "FC-FUSE-DC-160-1500A")
        lamp = d.device(f"H{i}", "DEMO-LAMP-24")
        d.series(dc.plus, relay.coil["A1"], wire=_WIRE)
        d.series(relay.coil["A2"], dc.minus, wire=_WIRE)
        d.series(dc.plus, relay.co_1[11], wire=_WIRE)
        d.series(relay.co_1[14], fuse[1], wire=_WIRE)
        d.series(fuse[2], lamp["1"], wire=_WIRE)
        d.series(lamp["2"], dc.minus, wire=_WIRE)
    return fr.build(d)


def test_every_fuse_behind_a_changeover_reads_the_source_and_is_checked() -> None:
    """All ten fuses read 6000 A from the source, so all ten break below it."""
    result = _build()
    faults = fr.derive.prospective_fault(result.model)
    assert [fault.current_a for fault in faults] == [Decimal(6000)] * _RELAYS
    expect_codes(result, "RATING_BREAKING_BELOW_FAULT")
    assert sum(f.code == "RATING_BREAKING_BELOW_FAULT" for f in result.findings) == _RELAYS
