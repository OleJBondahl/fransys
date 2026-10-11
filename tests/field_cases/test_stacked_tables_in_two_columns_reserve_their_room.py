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
from fransys.colours import BU

from fransys_layout.stages import pagerun
from fransys_layout.stages.lookups import placed_keepout
from fransys_model.derive.drawing_text import CONTACT_SLOTS, content_extent
from fransys_model.layout import Label, LabelKind, Route, layout_of, sheet_for
from fransys_model.vocab import PageKind

Box = tuple[int, int, int, int]  # x, y, width, height


def _chain(d: Any, first: int, live: Any, rail: Any, lamps: Any) -> None:
    """Two relays in series from `live` to the rail, each with a contact feeding its lamp."""
    ks = [d.device(f"K{first + i}", "DEMO-RLY-2CO-24") for i in range(2)]
    ps = [d.device(f"P{first + i}", "DEMO-LAMP-24") for i in range(2)]
    d.wire(live, ks[0].coil["A1"], wire=(BU, 0.5))
    d.wire(ks[0].coil["A2"], ks[1].coil["A1"], wire=(BU, 0.5))
    d.wire(ks[1].coil["A2"], rail, wire=(BU, 0.5))
    for k, p, end in zip(ks, ps, lamps, strict=True):
        d.wire(k.co_1["14"], p.lamp["1"], wire=(BU, 0.5))
        d.wire(p.lamp["2"], end, wire=(BU, 0.5))


class _Built:
    """The built model with what the placement stages kept of the page."""

    def __init__(self) -> None:
        self.cells: list[Box] = []
        self.reserve_bottom = 0
        self.tables: list[Label] = []
        self.model: Any = None
        self.findings: Any = ()


@pytest.fixture(scope="module")
def got() -> _Built:
    """Build the two-chain circuit once, keeping the cells' boxes and the reserved room's bottom."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        return _built(monkeypatch)


def _built(monkeypatch: pytest.MonkeyPatch) -> _Built:
    got = _Built()
    unreserve = pagerun.unreserve

    def keep(placed: Any, rooms: Any) -> Any:
        got.reserve_bottom = max(
            got.reserve_bottom,
            *(placed_keepout(one).y + placed_keepout(one).height for one in placed),
        )
        done = unreserve(placed, rooms)
        got.cells = [(b.x, b.y, b.width, b.height) for b in (placed_keepout(one) for one in done)]
        return done

    monkeypatch.setattr(pagerun, "unreserve", keep)
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Relay group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", 8).run("R", 8, bridged=True)
        d.dc_supply("S", plus=live[1], minus=rail[1], voltage=24)
        _chain(d, 1, live[1], rail[2].outer, (rail[4].outer, rail[5].outer))
        _chain(d, 3, live[2], rail[3].outer, (rail[6].outer, rail[7].outer))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    got.model, got.findings = result.model, result.findings
    got.tables = [
        one
        for one in layout_of(result.model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE and one.slot in CONTACT_SLOTS
    ]
    return got


def _box(one: Label) -> Box:
    return one.x, one.y, one.width, one.height


def _share(a: Box, b: Box) -> bool:
    """True when the two boxes share area."""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def _segments(route: Route) -> list[Box]:
    """The thin boxes of a route's segments."""
    points = sorted(route.points, key=lambda p: p.index)
    return [
        (min(p.x, q.x), min(p.y, q.y), abs(p.x - q.x) + 1, abs(p.y - q.y) + 1)
        for p, q in pairwise(points)
    ]


def test_four_tables_in_two_stacks_stand_in_the_sheet_and_clear_of_everything(
    got: _Built,
) -> None:
    """Four tables in two stacks: inside the sheet, off every cell, wire, label and other table."""
    assert [f.code for f in got.findings if f.severity.name == "ERROR"] == []
    assert len(got.tables) == 4
    assert len({t.x for t in got.tables}) == 2  # two stacks, one per column
    sheet = sheet_for(got.model, PageKind.SCHEMATIC)
    width = content_extent(sheet.content_width_mm, sheet.module_mm)
    height = content_extent(sheet.content_height_mm, sheet.module_mm)
    for t in got.tables:
        assert t.x >= 0
        assert t.y >= 0
        assert t.x + t.width <= width
        assert t.y + t.height <= height
    others = [_box(one) for one in layout_of(got.model, Label).values() if one not in got.tables]
    wires = [seg for route in layout_of(got.model, Route).values() for seg in _segments(route)]
    for i, t in enumerate(got.tables):
        clear = [*got.cells, *others, *wires, *(_box(u) for u in got.tables[:i])]
        assert not [b for b in clear if _share(_box(t), b)]


@pytest.mark.xfail(
    strict=True,
    reason="the reserve counts each table's size, not the push below the A2 marker: 36 short",
)
def test_the_room_reserved_below_the_row_holds_the_tallest_stack(got: _Built) -> None:
    """Each column's last coil keeps `foot_down` of its tables (80); the stack ends 36 below that.

    `contact_images` pushes the first table below the A2 star marker (images.py `push_clear`),
    and `image_reserves` knows nothing of that push.
    """
    assert got.reserve_bottom >= max(t.y + t.height for t in got.tables)
