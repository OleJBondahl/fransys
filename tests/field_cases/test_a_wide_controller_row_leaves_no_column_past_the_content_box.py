"""Field case: a wide controller beside many relay groups leaves no box past the content box.

The engineering shape: a unit holds a 24 V controller with twenty one-pin signal connectors
whose pin names are long, ten of them wired to terminals on another strip, so their ends carry
link markers. Twenty relay groups each take a coil from a controller pin, and fifteen chains of
two push buttons and a contactor coil stand beside them. The unit sets its own profile.

The bug: columns are planned on an estimated width, placed, and planned again once on the grown
widths. Most columns grow after the estimate (the controller's pins stand in rows wider than
the page), and after the one re-plan a column still lands past the content box: its keep-out,
label and routes leave it (`OUT_OF_CONTENT_BOX`). The test shows only this terminal-column and
coil-chain shape; it does not show coil labels or link markers leaving the box the same way.

The rule (decision layout-0175, amended): the plan settles within a stated bound. A placing
that measures a column wider than it was planned with plans again, three times at most.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

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
    d.layout.profile(hide_unused_pins=True, column_gap=16)  # the unit's own profile (model-0192)
    x4, x5, x6 = (d.terminal_strip(name, "DEMO-TB-2.5") for name in ("X4", "X5", "X6"))
    plus, minus = x4.run("24V", bridged=True), x5.run("0V", bridged=True)
    ctrl = d.device("U2", "DEMO-CTRL-20P")
    d.wire(plus, ctrl.supply["+"], wire=("RD", 0.75))
    d.wire(minus, ctrl.supply["-"], wire=("BK", 0.75))
    with d.function("DRV", "Drives"):
        for n in range(1, _SIGNALS + 1):
            d.wire(getattr(ctrl, f"s{n}")[f"SIGNAL_CHANNEL_{n:02d}"], x6[n], wire=("WH", 0.75))
    with d.function("CH", "Chains"):
        for n in range(1, _CHAINS + 1):
            coil = d.device(f"KC{n}", "DEMO-CTR-3P-24").coil
            first, second = (d.device(f"B{n}{m}", "DEMO-PB-NC").sw for m in (1, 2))
            d.wire(plus, first["A"], wire=("RD", 0.75))
            d.wire(first["B"], second["A"], wire=("RD", 0.75))
            d.wire(second["B"], coil["A1"], wire=("RD", 0.75))
            d.wire(coil["A2"], minus, wire=("BK", 0.75))
            d.layout.chain(first, second, coil)
    for n in range(1, _GROUPS + 1):
        with d.function(f"G{n}", f"Group {n}"):
            relay = d.device(f"K{n}", "DEMO-RLY-2CO-24")
            pin = getattr(ctrl, f"s{n}")[f"SIGNAL_CHANNEL_{n:02d}"]
            d.wire(pin, relay.coil["A1"], wire=("RD", 0.75))
            d.wire(relay.coil["A2"], minus, wire=("BK", 0.75))
            d.wire(plus, relay.co_1["11"], wire=("RD", 0.75))
            d.wire(relay.co_1["14"], x6[n + 20], wire=("RD", 0.75))
    return _Strips(x4)


def test_a_wide_controller_row_leaves_no_column_past_the_content_box() -> None:
    d = fr.design("demo_parts")
    d.add(_control, "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    result = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-control", cover=cover)
    )
    assert [f.code for f in fr.check(result) if f.code == "OUT_OF_CONTENT_BOX"] == []
