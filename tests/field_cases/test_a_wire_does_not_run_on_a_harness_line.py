"""Field case: a wire ran along a harness line that is not its own, and a fan split stood on it.

The engineering shape: a cabinet unit holds a header `-J1` wired to two lamps and a board unit
`-U1` whose connector `-X7` is its interface. A cable `-W1` has two cores from `-J1` to `-X7`. The
header's pin 1 takes a lamp wire and a core, so the wire and the core's fan-out leave one pin.

The bug: the cable's fan-out split stood on the lamp's wire and its legs and trunk ran along it.
The page drew the wire and the line as one conductor: two nets joined (`DRAWING_SHORTS_NETS`).

Rule: a fan-out's split stands on no wire, so its line runs along none. Fixed by layout-0246.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model.layout import HarnessFanOut, HarnessLine, Route, layout_of


class _Io(NamedTuple):
    X7: fr.Device


class _Open(NamedTuple):
    pass


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    x7 = u.device("X7", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    lamp = u.device("K1", "DEMO-LAMP-24", parent=pcb)
    u.detail.wire(x7[1], lamp["1"], wire=(BK, 0.5))
    u.detail.wire(x7[2], lamp["2"], wire=(BK, 0.5))
    return _Io(x7)


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    board = u.add(_board, "U1")
    j1 = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    for n in (1, 2):
        u.detail.wire(j1[n], u.device(f"H{n}", "DEMO-LAMP-24")["1"], wire=(BK, 0.5))
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, board.X7[1], j1[1])
    cable.core(2, board.X7[2], j1[2])
    return _Open()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    cover = tmp_path_factory.mktemp("cover") / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover))


def test_no_wire_is_drawn_joined_to_a_harness_line(built: fr.BuildResult) -> None:
    model = built.model
    assert layout_of(model, HarnessLine) != {}
    assert layout_of(model, HarnessFanOut) != {}
    assert layout_of(model, Route) != {}
    assert [f for f in fr.check(built) if f.code == "DRAWING_SHORTS_NETS"] == []
