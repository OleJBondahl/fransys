"""The released I/O board unit that the unit-tag field cases place."""

from typing import Any, NamedTuple

import fransys as fr


class Io(NamedTuple):
    J1: fr.Device


def demo_board(**extra: Any) -> Any:
    """The `demo-board` unit at revision 1; `extra` adds unit keywords such as `title`."""

    @fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", **extra)
    def board(u: Any) -> Io:
        root = u.device("U9", "DEMO-PCB-IO")
        return Io(u.device("J1", "DEMO-CONN-2P", parent=root, interface=True, unused=True))

    return board
