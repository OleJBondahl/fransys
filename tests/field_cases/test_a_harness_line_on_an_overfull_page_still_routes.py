"""Field case: contactors and a deep coil column on one overfull page, wired straight to a nested unit's terminal strip.
The bug: a line's far end below the content box had no path inside it (layout-0166, layout-0167).
Redrawn without a mate (R1526, R1462) so the outline draws; T-a and T-b are MATES-RETURN witnesses."""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import fransys_parts
from _connector_parts import LIBRARY
from _drawn_pages import drawn_pages

from fransys_model.kernel import merge

_CONTACTOR = """schema = 2

[part]
mpn = "FLD-CTR"
manufacturer = "Demo"
description = "Contactor with coil and auxiliary contact"
category = "electromechanical"
class_code = "Q"

[[function]]
name = "coil"
kind = "coil"
symbol = "operating-device"
ports = [
    { name = "X1", role = "generic", symbol_port = "in" },
    { name = "X2", role = "generic", symbol_port = "out" },
]

[[function]]
name = "aux"
kind = "contact_no"
symbol = "make-contact"
ports = [
    { name = "T1", role = "generic", symbol_port = "in" },
    { name = "T2", role = "generic", symbol_port = "out" },
]
links = [{ a = "T1", b = "T2", kind = "switched" }]
"""
WIRE = ("WH", 0.5)


def _library(root: Path) -> Path:
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(LIBRARY)
    (root / "parts" / "ctr.toml").write_text(_CONTACTOR)
    return root


class _Strip(NamedTuple):
    X1: Any


def _board_of(terminals: int) -> Any:
    @fr.unit("fld-board", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
    def board(u: Any) -> _Strip:
        return _Strip(u.terminal_strip("X1", "DEMO-TB-2.5", terminals, interface=True))

    return board


class _Top(NamedTuple):
    pass


def _tail(u: Any, start: Any, count: int, tag: str = "K") -> Any:
    """`count` contactor coils in series after `start`: one tall column; the last coil's X2."""
    for i in range(count):
        coil = u.device(f"{tag}{i + 1}", "FLD-CTR").coil
        u.series(start, coil["X1"], wire=WIRE)
        start = coil["X2"]
    return start


def _contactors(u: Any, board: Any, count: int, deep: int) -> None:
    """Up to two contactors, their eight pins wired straight to the nested unit's terminal strip."""
    pin = board.X1
    for i in range(count):
        q = u.device(f"Q{i + 1}", "FLD-CTR")
        for n, end in enumerate((q.coil["X1"], q.coil["X2"], q.aux["T1"], q.aux["T2"]), start=1):
            if i == 0 and n == 1 and deep:
                first = u.device("G1", "FLD-CTR").coil
                u.series(pin[1].outer, first["X1"], wire=WIRE)
                u.series(_tail(u, first["X2"], deep - 1, "H"), end, wire=WIRE)
            else:
                u.series(pin[4 * i + n].outer, end, wire=WIRE)


def _top_with(contactors: int, deep: int) -> Any:
    @fr.unit("fld-top", revision=1, interface_version=1, date="2026-10-08", text="t", by="X")
    def top(u: Any) -> _Top:
        _contactors(u, u.add(_board_of(4 * contactors), "A1"), contactors, deep)
        return _Top()

    return top


@cache
def _built(contactors: int, deep: int = 0) -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(_library(root / "lib")))
    d = fr.Design(draft)
    d.add(_top_with(contactors, deep), "U1")
    (root / "cover.md").write_text("# Top\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset("cabinet_schematic"), "fld-top", cover=root / "cover.md")
    return fr.build(d, doc)


def _errors(built: fr.BuildResult) -> list[str]:
    return [f.code for f in built.findings if f.severity.name == "ERROR"]


def _outlines(built: fr.BuildResult) -> int:
    return sum(len(d.outlines) for d in drawn_pages(built.model).values())


def test_one_contactor_builds() -> None:
    assert _errors(_built(1)) == []
    assert _outlines(_built(1)) == 4  # one frame per wired terminal of the nested unit


def test_t_c_a_page_that_still_overflows_keeps_its_ink_in_the_page_and_builds() -> None:
    built = _built(2, 6)
    assert _errors(built) == []
    assert "OUT_OF_PAGE" not in {f.code for f in built.findings}
    assert _outlines(built) == 8


def test_t_c_a_line_end_below_the_box_of_a_page_no_cut_helps_still_routes() -> None:
    """layout-0166's extent, moved here by layout-0167: an upper band taller than a page."""
    built = _built(2, 8)
    assert _errors(built) == []
    assert "OUT_OF_PAGE" not in {f.code for f in built.findings}
    assert _outlines(built) == 8
