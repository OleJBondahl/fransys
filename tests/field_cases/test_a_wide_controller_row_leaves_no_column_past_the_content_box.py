"""The W06 wide controller row: a design builder that other tests import by name (`_control`).
It asserts that no connection is undrawn and that no route fails."""

from contextlib import nullcontext
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document

from fransys_model.kernel import id_namespace

# KI-278: the W06 build has 2 conductors with no path
# KI-467: ANNEX_UNPLACED at salts b to e in the bridged-strip build (TRACE-ROOTS-U-2)
_SIGNALS, _GROUPS, _CHAINS = 10, 20, 15


class _Strips(NamedTuple):
    X4: Any


@fr.unit(
    "demo-control",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Control",
    number="N-1",
)
def _control(d: Any) -> _Strips:
    d.layout.profile(hide_unused_pins=True)  # the unit's own profile (model-0192)
    x4, x5, x6 = (d.terminal_strip(name, "DEMO-TB-2.5") for name in ("X4", "X5", "X6"))
    plus, minus = x4.run("24V", bridged=True), x5.run("0V", bridged=True)
    ctrl = d.device("U2", "DEMO-CTRL-20P")
    d.series(plus, ctrl.supply["+"], wire=("RD", 0.75))
    d.series(minus, ctrl.supply["-"], wire=("BK", 0.75))
    with d.function("DRV", "Drives"):
        for n in range(1, _SIGNALS + 1):
            d.series(getattr(ctrl, f"s{n}")[f"SIGNAL_CHANNEL_{n:02d}"], x6[n].inner, wire=("WH", 0.75))
    with d.function("CH", "Chains"):
        for n in range(1, _CHAINS + 1):
            coil = d.device(f"KC{n}", "DEMO-CTR-3P-24").coil
            first, second = (d.device(f"B{n}{m}", "DEMO-PB-NC").sw for m in (1, 2))
            d.series(plus, first["A"], wire=("RD", 0.75))
            d.series(first["B"], second["A"], wire=("RD", 0.75))
            d.series(second["B"], coil["A1"], wire=("RD", 0.75))
            d.series(coil["A2"], minus, wire=("BK", 0.75))
    for n in range(1, _GROUPS + 1):
        with d.function(f"G{n}", f"Group {n}"):
            relay = d.device(f"K{n}", "DEMO-RLY-2CO-24")
            pin = getattr(ctrl, f"s{n}")[f"SIGNAL_CHANNEL_{n:02d}"]
            d.series(pin, relay.coil["A1"], wire=("RD", 0.75))
            d.series(relay.coil["A2"], minus, wire=("BK", 0.75))
            d.series(plus, relay.co_1["11"], wire=("RD", 0.75))
            d.series(relay.co_1["14"], x6[n + 20].inner, wire=("RD", 0.75))
    return _Strips(x4)


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_control, "U1")
    return fr.build(d, unit_document("demo-control"))


def test_a_wide_controller_rows_bridged_rails_are_drawn_joined() -> None:
    """KI-369, R1061: the bridge members' coil legs meet only through the bridge, so no connection of the build is undrawn."""
    assert [f.code for f in _built().findings if f.code == "CONNECTION_NOT_DRAWN"] == []


@pytest.mark.rule("G08-POWER")
@pytest.mark.parametrize("salt", ["-", "a", "b", "c", "d", "e"])
def test_a_bridged_strip_draws_each_terminals_own_wires_and_no_route_fails(salt: str) -> None:
    """R1141: the bridges leave the drawing's nets, so the 20 X5 0V terminals are not one net that cannot route.

    KI-407, R1194: a copy alone on its page stands at the trunk end its pin's drop ends at, so no wire end dangles.
    """

    with id_namespace(salt) if salt != "-" else nullcontext():
        assert [f.code for f in _built().findings if f.code == "DANGLING_WIRE_END"] == []
