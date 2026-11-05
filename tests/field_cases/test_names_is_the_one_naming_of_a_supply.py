"""Field case: `names=` is the one naming of a DC supply's two rails; its source adds no third.
The bug: the call found the minus pin again as the supply's mid, so a third rail `0V` was declared on the same pin.
Fixed by author-0026: the source gives the voltage and the pins the call did not name; a named pin is never also the mid."""

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
    plus = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("24V", 2, bridged=True, rail=True)
    minus = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("GND", 2, bridged=True, rail=True)
    wire = ("RD", 0.75)
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply(
        "24V", psu.output, plus=psu.output["P"], minus=psu.output["M"],
        names=("24V", "GND"),
    )  # fmt: skip
    d.series(psu.output["P"], plus[1].inner, wire=wire)
    d.series(psu.output["M"], minus[1].inner, wire=("BK", 0.75))
    d.series(plus[2].inner, lamp.lamp["1"], wire=wire)
    d.series(minus[2].inner, lamp.lamp["2"], wire=("BK", 0.75))
    return fr.build(d, system_document())


def test_the_supply_has_exactly_the_two_named_rails_and_no_error() -> None:
    result = _model()
    rails = {name: rail.max_v for system in supply_systems(result.model).values() if system.name == "24V" for name, rail in system.rails.items()}
    errors = [f.code for f in fr.check(result) if f.severity is fr.Severity.ERROR]
    assert (rails, errors) == ({"24V": 24, "GND": 0}, [])
