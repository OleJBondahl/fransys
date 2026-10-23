"""Field case: a coil with its bottom-right taken prints its table top-right (CONTACT-TABLE).

The engineering shape: six 4-changeover relays in two rows of three, each coil fed by a controller
channel and returned to a bridged 0 V strip, all 24 contact pins wired to a field strip. The
tables are switched on (`contact_tables = true`).
The rule (owner 2026-10-18, R339/R345): a table stands bottom-right of its coil, and top-right
when the bottom-right is taken. Here the upper row has its next row below it, so its tables stand
above it; the lower row has the room and its tables stand below. Decision: el-0049.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from _tables_on import TABLES_ON
from fransys.colours import BK, WH

RELAYS = 6
PINS = tuple(f"CH{j:02d}-" for j in range(1, RELAYS + 1))


@cache
def _page() -> dict[str, list[tuple[int, int]]]:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(hide_unused_pins=True, column_gap=4, row_spacing=400)
    with d.function("V24", "Supply"):
        psu = d.device("G1", "DEMO-PSU-24")
        zero = d.terminal_strip("X5", "DEMO-TB-2.5", 7).run("Z", 7, bridged=True)
        d.dc_supply("24VDC", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
        d.detail.wire(psu.output["-"], zero[1].outer, wire=(BK, 0.5))
    with d.function("PLC", "Outputs"):
        plc = d.device("A1", None, pins=PINS, external=True)
    with d.function("VLV", "Relays"):
        relays = [d.device(f"K{i + 4}", "DEMO-RLY-4CO-24") for i in range(RELAYS)]
        for pin, relay in zip(PINS, relays, strict=True):
            d.detail.wire(plc[pin], relay.coil["A1"], wire=(WH, 0.5))
            d.detail.wire(relay.coil["A2"], zero[7].outer, wire=(BK, 0.5))
    with d.function("USE", "Contacts to the field"):
        field = d.terminal_strip("X7", "DEMO-TB-2.5", 4 * 2 * RELAYS)
        pin = iter(range(1, 4 * 2 * RELAYS + 1))
        for relay in relays:
            for n in (1, 2, 3, 4):
                contact = getattr(relay, f"co_{n}")
                d.detail.wire(field[next(pin)].outer, contact[f"{n}1"], wire=(WH, 0.5))
                d.detail.wire(field[next(pin)].outer, contact[f"{n}4"], wire=(WH, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    drawings = fr.build(d, document, settings=TABLES_ON).drawings.values()
    symbols = [s for drawing in drawings for s in drawing.symbols]
    return {
        key: [(s.x, s.y) for s in symbols if s.key == key]
        for key in ("operating-device", "contact-head")
    }


def _head_of(coil: tuple[int, int]) -> tuple[int, int]:
    heads = _page()["contact-head"]
    return min((h for h in heads if h[0] == coil[0] + 8), key=lambda h: abs(h[1] - coil[1]))


def test_every_coil_has_one_table_at_its_right() -> None:
    coils = _page()["operating-device"]
    assert len(coils) == len(_page()["contact-head"]) == RELAYS
    assert all(_head_of(c) for c in coils)


def test_a_coil_with_another_below_it_takes_top_right_and_the_lowest_takes_bottom_right() -> None:
    coils = _page()["operating-device"]
    for coil in coils:
        has_row_below = any(o[0] == coil[0] and o[1] > coil[1] for o in coils)
        head = _head_of(coil)
        assert (head[1] < coil[1]) == has_row_below, (coil, head)
