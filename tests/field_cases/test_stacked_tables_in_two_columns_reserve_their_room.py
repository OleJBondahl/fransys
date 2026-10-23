"""Field case: two columns of two stacked contact tables each reserve room for the taller stack.

The engineering shape: two chains of two relays in series, side by side on one page row. Each
relay has a changeover contact feeding its own lamp, so each coil gets a contact table. The two
chains stand in two columns, one coil above the other, and each column's two tables stack at the
column's foot (decision layout-0170).

The question (CONTACT-IMAGES review): `image_reserves` sums the stacked tables' room per column
key, and tables of different columns might reserve too little. The sum is right per column
(`foot_down`), and the tables stand in the sheet and clear of everything. But the first table is
pushed below the A2 star marker, a push the reserve does not count, so the room below the row is
36 grid units short of the tallest stack (strict xfail; the fix is a later golden-lane order).
"""

import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any

import fransys as fr
import pytest
from _contact_tables import table_body_g, table_symbols
from _drawn_pages import drawn_pages
from fransys.colours import BU

Box = tuple[int, int, int, int]  # x0, y0, x1, y1
PADDING = 2  # the profile's marker padding: the reserve may exceed a stack by one of it


def _chain(d: Any, first: int, live: Any, rail: Any, lamps: Any) -> None:
    """Two relays in series from `live` to the rail, each with a contact feeding its lamp."""
    ks = [d.device(f"K{first + i}", "DEMO-RLY-2CO-24") for i in range(2)]
    ps = [d.device(f"P{first + i}", "DEMO-LAMP-24") for i in range(2)]
    d.detail.wire(live, ks[0].coil["A1"], wire=(BU, 0.5))
    d.detail.wire(ks[0].coil["A2"], ks[1].coil["A1"], wire=(BU, 0.5))
    d.detail.wire(ks[1].coil["A2"], rail, wire=(BU, 0.5))
    for k, p, end in zip(ks, ps, lamps, strict=True):
        d.detail.wire(k.co_1["14"], p.lamp["1"], wire=(BU, 0.5))
        d.detail.wire(p.lamp["2"], end, wire=(BU, 0.5))


def _built(chains: int) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Relay group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 8).run("R", 8, bridged=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
        _chain(d, 1, live[1], rail[2].outer, (rail[4].outer, rail[5].outer))
        if chains == 2:
            _chain(d, 3, live[2], rail[3].outer, (rail[6].outer, rail[7].outer))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


@pytest.fixture(scope="module")
def got() -> fr.BuildResult:
    """The two-chain circuit, built once."""
    return _built(chains=2)


@pytest.fixture(scope="module")
def one_column() -> fr.BuildResult:
    """The control: one chain, so one column holding one stack of two tables."""
    return _built(chains=1)


def _share(a: Box, b: Box) -> bool:
    """True when the two boxes share area."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _segments(points: tuple) -> list[Box]:
    """The thin boxes of a wire's segments."""
    return [
        (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]) + 1, max(p[1], q[1]) + 1)
        for p, q in pairwise(points)
    ]


def test_four_tables_in_two_stacks_stand_in_the_sheet_and_clear_of_everything(
    got: fr.BuildResult,
) -> None:
    """Four tables in two stacks: inside the sheet, off every cell, wire, label and other table."""
    assert [f.code for f in got.findings if f.severity.name == "ERROR"] == []
    tables = table_symbols(got.model)
    assert len(tables) == 4
    assert len({t.x for t in tables}) == 2  # two stacks, one per column
    (drawing,) = drawn_pages(got.model).values()
    boxes = [table_body_g(t) for t in tables]
    for x0, y0, x1, y1 in boxes:
        assert x0 >= 0
        assert y0 >= 0
        assert x1 <= drawing.area.w
        assert y1 <= drawing.area.h
    cells = [
        table_body_g(s) for s in drawing.symbols if s not in tables and s.key != "junction-dot"
    ]
    others = [(t.box.x, t.box.y, t.box.x + t.box.w, t.box.y + t.box.h) for t in drawing.texts]
    wires = [seg for w in drawing.wires for seg in _segments(w.points)]
    for i, box in enumerate(boxes):
        clear = [*cells, *others, *wires, *boxes[:i]]
        assert not [b for b in clear if _share(box, b)]


def _spare_room(built: fr.BuildResult) -> list[int]:
    """Per stack column: the page room below its tallest stack's bottom (>= 0 holds)."""
    (drawing,) = drawn_pages(built.model).values()
    stacks: dict[int, int] = {}
    for t in table_symbols(built.model):
        stacks[t.x] = max(stacks.get(t.x, 0), table_body_g(t)[3])
    return [drawing.area.h - bottom for bottom in stacks.values()]


def test_the_room_reserved_below_the_row_holds_the_tallest_stack(got: fr.BuildResult) -> None:
    """Each column's reserve holds its stack, the first table pushed below the A2 marker (0171).

    `contact_images` pushes the first table below the ground symbol under the foot coil's A2;
    the reserve counts that push (it was 36 short, 472 against 508), and no more than the stack.
    """
    spare = _spare_room(got)
    assert len(spare) == 2
    assert all(0 <= one <= PADDING for one in spare)


def test_one_column_reserves_the_room_of_its_stack_too(one_column: fr.BuildResult) -> None:
    """The control: one column holding one stack of two tables reserves its room too."""
    assert len(table_symbols(one_column.model)) == 2
    spare = _spare_room(one_column)
    assert len(spare) == 1
    assert all(0 <= one <= PADDING for one in spare)
