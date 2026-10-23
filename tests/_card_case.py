"""The PLC output card case of P7.1 B: a wide card, one coil under each channel pin (SW8)."""

import tempfile
from pathlib import Path

import fransys as fr
from _page_drawings import page_drawings
from fransys.colours import BU

__all__ = ["card_case_drafts", "coil_wires_straight", "page_count"]


def card_case_drafts(channels: int = 32) -> tuple:
    """The design and cabinet document of one output card with a coil on every channel.

    The card is one external box with `channels` pins in one group; the coils stand in a second
    group, coil i wired from pin i. Nothing else is drawn: no feeder, strip or lamp.
    """
    pins = tuple(f"CH{j:02d}-" for j in range(1, channels + 1))
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("PLC", "Card"):
        card = d.device("A1", None, pins=pins, external=True)
    with d.function("B", "Relays"):
        for i, pin in enumerate(pins):
            relay = d.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
            d.detail.wire(card[pin], relay.coil["A1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return d, doc


def page_count(result) -> int:
    """The pages the core path drew for `result`: its `layout.drawn_page` records."""
    return len(page_drawings(result))


def coil_wires_straight(result) -> bool:
    """Whether every wire is two points and vertical: the card case holds no other wire.

    A coil is at its pin when the wire from the pin to it is straight (QUESTION 2, option a).
    """
    wires = [w for d in page_drawings(result).values() for w in d.wires]
    return bool(wires) and all(
        len(w.points) == 2 and w.points[0][0] == w.points[1][0] for w in wires
    )
