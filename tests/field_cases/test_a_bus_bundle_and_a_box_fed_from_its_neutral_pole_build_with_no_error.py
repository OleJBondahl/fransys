"""Field case: a main switch feeds a bus, and its neutral pole runs straight into a supply box.

The engineering shape: a four-pole main switch feeds a three-phase-and-neutral bus. Two motor
feeders and a 24 V supply (a breaker on one phase, then the supply box) hang on the bus. The
supply box's neutral input is wired to the switch's fourth pole, its phase input from the breaker.

The bug: the box is one place in the stack, so the switch (the bus bundle's driver) and the
breaker (one of its legs) stood on one node, and the build raised BundleError "a driver and a
leg on one node". The rule (BUNDLE, layout-0341): a column that would put a bundle's driver and
leg on one node through a box leaves that box pin as a cross-link wire instead of standing on it.
"""

import tempfile
from pathlib import Path

import fransys as fr

POWER = 2.5


def _cover() -> Path:
    path = Path(tempfile.mkdtemp()) / "cover.md"
    path.write_text("# Bus\n", encoding="utf-8")
    return path


def _design() -> tuple[fr.Design, fr.Draft]:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Bus", number="B-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-19", text="First issue", created="XX")
    with d.function("INC", "Incomer"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4, pe="DEMO-TB-PE-2.5")
        d.earth(x0.run("PE", 1)[1])
        mains = d.ac_supply("400V", 230, x0[1], x0[2], x0[3], n=x0[4])
        q0 = d.device("Q0", "DEMO-ISO-4P")
        d.series(mains, q0.main, wire=16)
        load = q0.main
        bus = d.ac_supply(
            "BUS",
            230,
            load["2"],
            load["4"],
            load["6"],
            n=load["8"],
            names=("1L1", "1L2", "1L3", "1N"),
        )
    with d.function("CTL", "Control supply"):
        f0, t0 = d.device("F01", "DEMO-MCB-C6"), d.device("T01", "DEMO-PSU-24")
        d.series(bus.L1, f0.element, t0.input, bus.N, wire=POWER)
        d.dc_supply("24VDC", t0)
    for k in (1, 2):
        with d.function(f"M{k}", f"Feeder {k}"):
            f, q = d.device(f"F{k}1", "DEMO-MCB-3P"), d.device(f"Q{k}1", "DEMO-CTR-3P-NC")
            x = d.terminal_strip(f"X{k}", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5")
            d.series(bus, f.element, q.main, x, wire=POWER)
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=_cover())


def test_the_build_has_no_error_finding() -> None:
    result = fr.build(*_design())
    errors = [f.message for f in result.findings if f.severity == fr.Severity.ERROR]
    assert errors == []
