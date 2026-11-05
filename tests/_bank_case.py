"""The w08 bank: sixteen relays on one controller's pins with lamps, as a unit and as a built design.

Invented demo data only (invariant 6): `examples/demo-parts`.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

__all__ = ["bank_unit", "built_bank"]


class _Io(NamedTuple):
    feed: fr.TerminalStrip


_PINS = tuple(f"CH{j:02d}-" for j in range(1, 17))
_HOUSE_A3 = {fr.PageKind.SCHEMATIC: "A3", fr.PageKind.BLOCK_DIAGRAM: "A3"}


def bank_unit(count: int) -> Any:
    """`count` relays, each in its own function, on one controller, with lamps, as a unit."""

    @fr.unit("demo-bank", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def bank(u: fr.Design) -> _Io:
        feed = u.terminal_strip("X1", "DEMO-TB-2.5", 8, interface=True, bridged=True)
        back = u.terminal_strip("X2", "DEMO-TB-2.5", 8 + count, bridged=True)
        with u.function("PLC", "Controller"):
            controller = u.device("A1", None, pins=_PINS, external=True)
        ends = {}  # a terminal point takes one conductor (R1266): the bridged feed and back rails chain from relay pin to relay pin
        for i in range(count):
            with u.function(f"R{i + 1}", f"Relay {i + 1}"):
                relay = u.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
                u.series(ends.get("feed", feed[1].inner), relay.coil["A1"], wire=("WH", 0.75))
                u.series(controller[_PINS[i % 16]], relay.coil["A2"], wire=("BU", 0.75))
                lamp = u.device(f"P{i + 1}", "DEMO-LAMP-24")
                u.series(relay.co_1["14"], lamp.lamp[1], wire=("WH", 0.75))
                u.series(ends.get("back", back[1].inner), relay.co_1["11"], wire=("WH", 0.75))
                u.series(lamp.lamp[2], back[9 + i].inner, wire=("BU", 0.75))
                ends["feed"], ends["back"] = relay.coil["A1"], relay.co_1["11"]
        return _Io(feed)

    return bank


def built_bank(count: int, **build_kwargs: Any) -> fr.BuildResult:
    """The built design of one bank unit U1; `build_kwargs` go to `fr.build`."""
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Bank\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.add(bank_unit(count), "U1")
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-bank", cover=cover)
        build_kwargs.setdefault("settings", fr.settings(paper=_HOUSE_A3))
        return fr.build(d, document, **build_kwargs)
