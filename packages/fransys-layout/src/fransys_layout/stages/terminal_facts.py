"""The two facts about a terminal's wires: in line on a wire, and a lone point (layout-0113)."""

from typing import NamedTuple

from fransys_layout.conventions import fact

_SOURCE = "terminal strip (IEC 60947-7)"
_IN_LINE_WIRES = 2


class TerminalRead(NamedTuple):
    """A terminal's role, its port count (`inline_terminal` only) and the wires on its ports."""

    terminal: bool
    ports: int
    wires: int


@fact("inline_terminal", kind="physical", source=_SOURCE)
def inline_terminal(read: TerminalRead) -> bool:
    """A one-port terminal with two wires on its port sits in line on a wire."""
    return read.terminal and read.ports == 1 and read.wires == _IN_LINE_WIRES


@fact("terminal_point", kind="physical", source=_SOURCE)
def terminal_point(read: TerminalRead) -> bool:
    """A terminal with one wire is a lone point: its own point and nothing in line."""
    return read.terminal and read.wires == 1
