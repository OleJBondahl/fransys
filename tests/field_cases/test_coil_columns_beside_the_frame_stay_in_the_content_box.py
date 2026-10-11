"""Field case: a 24 V control page of many coil columns keeps every box inside the content box.

The engineering shape: nine columns, each a chain of two push buttons and a contactor coil, fed
from one 24 V run and returning to one 0 V run of two terminal strips. The coils' wires reach
terminals on other pages, so their ends carry link markers.

The bug: the last column stands against the frame and its terminal's label, keep-out box and
marker box leave the content box (`OUT_OF_CONTENT_BOX`, three findings). The consumer sees the same
finding on coil ports A1 and A2, which demo parts do not reach (`DEMO-SW-8P` now
exists; a coil-at-frame case with it has the same cause and is not added).
The fix (decision layout-0175): packing counts a column's placed pitch, so a column whose ink would
leave the box moves whole to the next page.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

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
    d.layout.profile(hide_unused_pins=True, column_gap=16)  # the unit's own profile (model-0192)
    x4 = d.terminal_strip("X4", "DEMO-TB-2.5")
    x5 = d.terminal_strip("X5", "DEMO-TB-2.5")
    plus, minus = x4.run("24V", bridged=True), x5.run("0V", bridged=True)
    with d.function("DRV", "Drives"):
        for n in range(1, _COLUMNS + 1):
            coil = d.device(f"K{n}", "DEMO-CTR-3P-24").coil
            first, second = (d.device(f"B{n}{m}", "DEMO-PB-NC").sw for m in (1, 2))
            d.wire(plus, first["A"], wire=("RD", 0.75))
            d.wire(first["B"], second["A"], wire=("RD", 0.75))
            d.wire(second["B"], coil["A1"], wire=("RD", 0.75))
            d.wire(coil["A2"], minus, wire=("BK", 0.75))
            d.layout.chain(first, second, coil)
    return _Strips(x4)


def test_coil_columns_beside_the_frame_stay_in_the_content_box() -> None:
    d = fr.design("demo_parts")
    d.add(_control, "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    result = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-control", cover=cover)
    )
    assert [f.code for f in fr.check(result) if f.code == "OUT_OF_CONTENT_BOX"] == []
