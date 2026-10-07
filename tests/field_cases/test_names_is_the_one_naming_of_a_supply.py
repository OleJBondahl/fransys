"""Field case: `names=` is the one naming of a DC supply's two rails; its source adds no third.

A 24 V supply device whose output pins are `P` and `M` feeds a 24V run and a GND run. The call is
`dc_supply("24V", psu.output, plus=P, minus=M, names=("24V", "GND"), earthing=IT)`. `M` is also
the IEC 60445 mark of a mid pin, so the call found it again as the supply's mid and declared a
third rail `0V` on the same pin: two names on one net, NET_POTENTIAL_CONFLICT and NET_SHORTED, and
the rating saw the minus rail at -24 V, 48 V across the 28 V output, RATING_VOLTAGE_BELOW_CIRCUIT.

The rule: the source gives the voltage and the pins the call did not name. A pin that `plus=` or
`minus=` already names is never also the mid. The decision that fixed it: author-0026.
"""

import fransys as fr
from _model_build_cover import system_document

from fransys_model.vocab.tables import supply_systems


def _model() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Supply", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24-PM")
    lamp = d.device("H1", "DEMO-LAMP-24")
    plus = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("24V", 2, bridged=True)
    minus = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("GND", 2, bridged=True)
    wire = ("RD", 0.75)
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply(
        "24V", psu.output, plus=psu.output["P"], minus=psu.output["M"],
        names=("24V", "GND"), earthing=fr.IT,
    )  # fmt: skip
    d.wire(psu.output["P"], plus[1], wire=wire)
    d.wire(psu.output["M"], minus[1], wire=("BK", 0.75))
    d.wire(plus[2], lamp.lamp["1"], wire=wire)
    d.wire(minus[2], lamp.lamp["2"], wire=("BK", 0.75))
    return fr.build(d, system_document())


def test_the_supply_has_exactly_the_two_named_rails_and_no_error() -> None:
    result = _model()
    rails = {
        name: rail.max_v
        for system in supply_systems(result.model).values()
        if system.name == "24V"
        for name, rail in system.rails.items()
    }
    errors = [f.code for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert (rails, errors) == ({"24V": 24, "GND": 0}, [])
