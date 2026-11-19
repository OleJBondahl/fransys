from __future__ import annotations

lazy import fransys as fr

from . import typed


def build_bus(d: fr.Design) -> tuple[fr.Terminal, fr.Terminal]:
    strip = d.terminal_strip("XDC", typed.PRT02, interface=True)
    return (strip.run("DC+", 1)[1], strip.run("DC-", 1)[1])
