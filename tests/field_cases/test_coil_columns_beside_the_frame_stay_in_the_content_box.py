"""Field case: a 24 V control page of many coil columns keeps every box inside the content box.
The bug: the last column's terminal label, keep-out box and marker box left the content box (`OUT_OF_CONTENT_BOX`).
Fixed by layout-0175: packing counts a column's placed pitch, so a column whose ink would leave the box moves whole."""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document

_COLUMNS = 9


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
    x4 = d.terminal_strip("X4", "DEMO-TB-2.5")
    x5 = d.terminal_strip("X5", "DEMO-TB-2.5")
    plus, minus = x4.run("24V", bridged=True), x5.run("0V", bridged=True)
    with d.function("DRV", "Drives"):
        for n in range(1, _COLUMNS + 1):
            coil = d.device(f"K{n}", "DEMO-CTR-3P-24").coil
            first, second = (d.device(f"B{n}{m}", "DEMO-PB-NC").sw for m in (1, 2))
            d.series(plus, first["A"], wire=("RD", 0.75))
            d.series(first["B"], second["A"], wire=("RD", 0.75))
            d.series(second["B"], coil["A1"], wire=("RD", 0.75))
            d.series(coil["A2"], minus, wire=("BK", 0.75))
    return _Strips(x4)


def test_coil_columns_beside_the_frame_stay_in_the_content_box() -> None:
    d = fr.design("demo_parts")
    d.add(_control, "U1")
    result = fr.build(d, unit_document("demo-control"))
    assert [f for f in fr.check(result) if f.severity.name == "ERROR"] == []
