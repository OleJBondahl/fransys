"""Field case: a main switch feeds a bus, and its neutral pole runs straight into a supply box.
The bug: the box stood the bus driver and a leg on one node, so the build raised BundleError "a driver and a leg on one node".
Fixed by layout-0341 (BUNDLE), a column that puts a bundle's driver and leg on one node leaves that box pin as a cross-link wire."""

import tempfile
from contextlib import nullcontext
from pathlib import Path

import fransys as fr
import pytest
from _model_build_cover import error_messages

from fransys_model.kernel import id_namespace

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
    assert error_messages(fr.build(*_design())) == []


def _cnd(salt: str) -> int:
    with id_namespace(salt) if salt else nullcontext():
        return sum(f.code == "CONNECTION_NOT_DRAWN" for f in fr.build(*_design()).findings)


@pytest.mark.parametrize("salt", ["", "e", "l", "n", "r"])
def test_the_neutral_crossing_is_drawn_or_stood_for_by_a_reference_pair_with_leads(salt: str) -> None:
    assert _cnd(salt) == 0
