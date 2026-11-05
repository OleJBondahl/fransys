"""The PLC output card case of P7.1 B: a wide card, one coil under each channel pin (SW8)."""

import tempfile
from pathlib import Path
from typing import Any

import fransys as fr
from _page_drawings import page_drawings
from fransys.colours import BU

__all__ = ["card_case_drafts", "coil_wires_straight", "lamps_drafts", "page_count"]


def card_case_drafts(channels: int = 32) -> tuple[Any, ...]:
    """The design and cabinet document of one output card with a coil on every channel.

    The card is one external box with `channels` pins in one group; the coils stand in a second
    group, coil i wired from pin i. Nothing else is drawn: no feeder, strip or lamp.
    """
    pins = tuple(f"CH{j:02d}-" for j in range(1, channels + 1))
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("PLC", "Card"):
        card = d.device("A1", None, pins=pins, external=True)
    zero = d.terminal_strip("X0", "DEMO-TB-2.5", channels, bridged=True, rail=True)  # a point takes one conductor (R1266)
    rail = d.terminal_strip("X24", "DEMO-TB-2.5", 1)
    d.dc_supply("S", plus=rail[1], minus=zero[1], voltage=24)
    with d.function("B", "Relays"):
        for i, pin in enumerate(pins):
            relay = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            d.series(card[pin], relay.coil["A1"], wire=(BU, 0.5))
            d.series(relay.coil["A2"], zero[i + 1].outer, wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return d, doc


def lamps_drafts() -> tuple[Any, ...]:
    """Two relay coils and one wire: symbols the library holds, no generic box."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    d.series(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    d.series(first.coil["A1"], second.coil["A2"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)


def page_count(result) -> int:
    """The pages the core path drew for `result`: its `layout.drawn_page` records."""
    return len(page_drawings(result))


def coil_wires_straight(result) -> bool:
    """Whether every wire is two points and vertical: the card case holds no other wire.

    A coil is at its pin when the wire from the pin to it is straight (QUESTION 2, option a).
    """
    wires = [w for d in page_drawings(result).values() for w in d.wires]
    return bool(wires) and all(len(w.points) == 2 and w.points[0][0] == w.points[1][0] for w in wires)
