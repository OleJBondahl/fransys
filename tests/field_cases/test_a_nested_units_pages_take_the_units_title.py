"""Field case: the pages that draw a nested unit take its title, not a range of its blocks.
The bug: those pages were titled "Board circuit 1" to "Board circuit 10", the board's blocks.
Fixed by model-0256: a nested unit's pages read the unit's title. Its build draws every connection: no CONNECTION_NOT_DRAWN (KI-515, R1532)."""

from functools import cache
from itertools import pairwise
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK

from fransys_model.derive import page_title, unit_release
from fransys_model.layout import DrawingSet, Page, layout_of

_BLOCKS = 10


class _Io(NamedTuple):
    X1: fr.Device
    X2: fr.Device
    X3: fr.Device
    X4: fr.Device
    X5: fr.Device
    X6: fr.Device
    X7: fr.Device
    X8: fr.Device
    X9: fr.Device
    X10: fr.Device


@fr.unit(
    "demo-board",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Relay board",
)
def _board(u: Any) -> Any:
    pcb = u.device("A1", "DEMO-PCB-IO")
    connectors = []
    for i in range(1, _BLOCKS + 1):
        with u.function(f"F{i}", f"Board circuit {i}"):
            x = u.device(f"X{i}", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
            lamp = u.device(f"K{i}", "DEMO-LAMP-24", parent=pcb)
        u.series(x[1], lamp["1"], wire=(BK, 0.5))
        u.series(x[2], lamp["2"], wire=(BK, 0.5))
        connectors.append(x)
    return _Io(*connectors)


class _Open(NamedTuple):
    pass


def _cabinet() -> Any:
    @fr.unit(
        "demo-cab",
        revision=1,
        interface_version=1,
        date="2026-01-01",
        text="first",
        by="AB",
        title="Cabinet",
    )
    def cab(u: Any) -> _Open:
        board = u.add(_board, "U1")
        lamps = []
        for n in range(1, _BLOCKS + 1):
            lamp = u.device(f"H{n}", "DEMO-LAMP-24")
            cable = u.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=1)
            cable.core(1, getattr(board, f"X{n}")[1], lamp["1"])
            lamps.append(lamp)
        for a, b in pairwise(lamps):  # one core per cable keeps each stub's ports; the return pins chain so no lamp is half-wired
            u.series(a["2"], b["2"], wire=(BK, 0.5))
        return _Open()

    return cab


@cache
def _titles() -> dict[str, list[str]]:
    """Page titles by the name of the unit whose set the page belongs to."""
    d = fr.design("demo_parts")
    d.add(_cabinet(), "C1", place=None)
    model = fr.build(d, unit_document("demo-cab")).model
    sets = layout_of(model, DrawingSet)
    found: dict[str, list[str]] = {}
    for page in layout_of(model, Page).values():
        owner = sets[page.drawing_set].unit
        if owner is None:
            continue
        name = unit_release(model, owner).name
        found.setdefault(name, []).append(page_title(model, page))
    return found


def test_without_a_title_the_cabinet_pages_that_draw_the_board_read_its_own_title() -> None:
    assert _titles()["demo-cab"].count("Relay board") == 2


def test_the_boards_own_pages_still_read_their_block_texts() -> None:
    board = _titles()["demo-board"]
    assert not any("Board circuit" in title for title in _titles()["demo-cab"])  # the cabinet pages read the unit title, not the blocks
    assert board[0].startswith("Board circuit 1, Board circuit 2")
    assert "Relay board" not in board


def test_a_one_core_cable_to_each_board_connector_is_drawn() -> None:
    d = fr.design("demo_parts")
    d.add(_cabinet(), "C1", place=None)
    assert [f for f in fr.build(d, unit_document("demo-cab")).findings if f.code == "CONNECTION_NOT_DRAWN"] == []
