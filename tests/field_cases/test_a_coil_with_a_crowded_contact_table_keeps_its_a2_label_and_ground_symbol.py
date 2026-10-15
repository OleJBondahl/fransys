"""Field case: coils with a crowded contact table below keep their A2 label and ground symbol.

The engineering shape: six 4-changeover relays, each coil driven by a channel of an external
controller box and each A2 returned to a bridged 0 V strip run that a 24 V supply's minus feeds
(so A2 carries a ground symbol). All 24 contact pins of the relays go to a field strip, so each
coil has a full contact table below it. The unit sets the profile `hide_unused_pins=True,
column_gap=4, row_spacing=400`; without it both versions give the same findings.

The bug (LEGACY-UNPLACED): from v0.18.7 to v0.19.1 the tables lay under the coils' A2 labels and
ground symbols, so five symbols were reported POWER_SYMBOL_UNPLACED (0 on v0.18.7) and the A2
labels joined LABEL_UNPLACED (3 on v0.18.7, 8 on v0.19.1).

Fixing change: LEGACY-UNPLACED (first labels and power leads read the functions as placed).
"""

import tempfile
from collections import Counter
from functools import cache
from pathlib import Path

import fransys as fr
from fransys.colours import BK, WH

RELAYS = 6
PINS = tuple(f"CH{j:02d}-" for j in range(1, RELAYS + 1))


@cache
def _codes() -> Counter:
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
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    return Counter(f.code for f in fr.check(result))


def test_every_ground_symbol_at_a_coil_finds_its_place() -> None:
    assert _codes()["POWER_SYMBOL_UNPLACED"] == 0  # v0.18.7: 0, v0.19.1: 5


def test_no_a2_label_joins_the_unplaced_labels() -> None:
    assert _codes()["LABEL_UNPLACED"] == 3  # v0.18.7: 3, v0.19.1: 8
