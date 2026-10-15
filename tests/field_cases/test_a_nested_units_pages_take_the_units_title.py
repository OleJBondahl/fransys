"""Field case: the pages that draw a nested unit take its title, not a range of its blocks.

The engineering shape: a cabinet unit nests a relay board with ten function blocks, each holding
an interface connector and a lamp; the cabinet wires a cable to every connector. The cabinet's
drawing set draws the board's group on two pages.

The bug: those pages were titled "Board circuit 1, ... Board circuit 9" and "Board circuit 10",
the blocks of the board, though the pages draw the board's boundary at the cabinet's level; and
`d.layout.page_title` took no handle for the board, so no title could be set for them.

The rule (decisions author-0049 and model-0256): `d.layout.page_title` takes what `d.add`
returns and titles every page of another set that draws that nested unit; without it such a page
is titled with the nested unit's own title. A device of the unit keeps its meaning.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
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
            x = u.device(
                f"X{i}", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F"
            )
            lamp = u.device(f"K{i}", "DEMO-LAMP-24", parent=pcb)
        u.detail.wire(x[1], lamp["1"], wire=(BK, 0.5))
        connectors.append(x)
    return _Io(*connectors)


class _Open(NamedTuple):
    pass


def _cabinet(hint: str | None, *, on_device: str | None = None) -> Any:
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
        for n in range(1, _BLOCKS + 1):
            lamp = u.device(f"H{n}", "DEMO-LAMP-24")
            cable = u.cable(f"W{n}", "DEMO-CBL-4G1.5", length_m=1)
            cable.core(1, getattr(board, f"X{n}")[1], lamp["1"])
        if hint is not None:
            u.layout.page_title(board, hint)
        if on_device is not None:
            u.layout.page_title(board.X10, on_device)
        return _Open()

    return cab


@cache
def _titles(hint: str | None, on_device: str | None = None) -> dict[str, list[str]]:
    """Page titles by the name of the unit whose set the page belongs to."""
    d = fr.design("demo_parts")
    d.add(_cabinet(hint, on_device=on_device), "C1", place=None)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover)
    ).model
    sets = layout_of(model, DrawingSet)
    found: dict[str, list[str]] = {}
    for page in layout_of(model, Page).values():
        owner = sets[page.drawing_set].unit
        if owner is None:
            continue
        name = unit_release(model, owner).name
        found.setdefault(name, []).append(page_title(model, page))
    return found


def test_a_title_on_the_nested_unit_handle_names_the_cabinet_pages_that_draw_it() -> None:
    cabinet = _titles("Board I/O")["demo-cab"]
    assert cabinet.count("Board I/O") == 2
    assert "Cabinet" in cabinet


def test_the_nested_units_own_pages_keep_their_block_titles() -> None:
    board = _titles("Board I/O")["demo-board"]
    assert "Board I/O" not in board
    assert board[-1] == "Board circuit 10"


def test_a_device_of_the_nested_unit_keeps_its_meaning() -> None:
    cabinet = _titles(None, "X10 page")["demo-cab"]
    assert cabinet.count("X10 page") == 1


def test_a_second_title_for_the_nested_unit_is_refused() -> None:
    @fr.unit("demo-twice", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def twice(u: Any) -> _Open:
        board = u.add(_board, "U1")
        u.layout.page_title(board, "One")
        with pytest.raises(fr.AuthorError, match="already has a title"):
            u.layout.page_title(board, "Two")
        return _Open()

    fr.design("demo_parts").add(twice, "C2", place=None)


def test_without_a_title_the_cabinet_pages_that_draw_the_board_read_its_own_title() -> None:
    cabinet = _titles(None)["demo-cab"]
    assert cabinet.count("Relay board") == 2
    assert not any("Board circuit" in title for title in cabinet)


def test_the_boards_own_pages_still_read_their_block_texts() -> None:
    board = _titles(None)["demo-board"]
    assert board[0].startswith("Board circuit 1, Board circuit 2")
    assert "Relay board" not in board
