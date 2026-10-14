"""Field case: eight relays, each in its own block, on a 4.0 mm module sheet build.

The engineering shape: eight relays (`DEMO-CO-4P-24`), one per block, coil A1 from a 4-terminal
feed strip (two coils per terminal), coil A2 from a 20-pin external controller, on a sheet of
module 4.0 mm.

The bug: the fuzz study of 2026-10-14 (C2) saw `KeyError` in `wide_columns.lane_of` here. It no
longer crashes at layout-0232 (WIDE-COLUMNS); this is its regression case.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-bank", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _bank(u: fr.Design) -> _Io:
    u.layout.profile(
        sheet=u.layout.sheet(
            "S3",
            width_mm=420,
            height_mm=297,
            content_x_mm=10,
            content_y_mm=10,
            content_width_mm=400,
            content_height_mm=277,
            frame_columns=8,
            frame_rows=6,
            module_mm=Decimal("4.0"),
        )
    )
    feed = u.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=True)
    u.terminal_strip("X2", "DEMO-TB-2.5", 8)
    with u.function("PLC", "Controller"):
        ctl = u.device("A1", None, pins=tuple(f"CH{j:02d}-" for j in range(1, 21)), external=True)
    for n in range(1, 9):
        with u.function(f"R{n}", f"Relay {n}"):
            k = u.device(f"K{n}", "DEMO-CO-4P-24")
            u.wire(feed[(n - 1) % 4 + 1], k.coil["A1"], wire=("WH", 0.75))
            u.wire(ctl[f"CH{n:02d}-"], k.coil["A2"], wire=("BU", 0.75))
    return _Io(feed)


def test_eight_relays_on_a_four_mm_module_sheet_build(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_bank, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-bank", cover=cover))
