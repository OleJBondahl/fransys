"""HA-D3B-FIX (layout-0158): the FIX FIRST on P3, each defect a case through `fr`.

Defect 1: a leaving line and its stub stand inside the frame (pump p03's `-W1`, `field_cable`).
Defect 2: legs end on their pins with the pins' leads drawn, a leaving line ends on its stub box's
edge with no thin piece, and a line's label keeps the house text gap from its line.
"""

import functools
import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # the sibling fixture modules
import ha_p3_cases
import ha_study_board
from fransys_render._leads import _absolute, wired_local_ports
from fransys_render._markers import box_origin, marker_facing, markers_group
from fransys_render._numbers import format_decimal, grid_to_mm
from fransys_render._symbol_geometry import oriented_symbol

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import Box, Point, pad
from fransys_layout.geometry.units import TEXT_GAP
from fransys_layout.lint._harness import through
from fransys_model.derive import draws_as_line
from fransys_model.layout import (
    ConnectorBox,
    HarnessFanOut,
    HarnessLine,
    LinkMarker,
    Page,
    Route,
    SymbolPlacement,
    layout_of,
    page_slice,
    sheet_format_of,
)
from fransys_model.vocab.tables import functions, items

_CASES = ("field_cable", "leaving", "two_units", "mixed")
_FANS = ("field_cable", "leaving", "mixed", "study")  # two_units ends in plugs only


@functools.cache
def _built(name: str):
    return ha_study_board.build() if name == "study" else getattr(ha_p3_cases, name)()


@pytest.mark.parametrize("name", [*_CASES, "study"])
def test_every_leaving_line_and_its_stub_stand_inside_the_frame(name: str) -> None:
    """Defect 1: the room is kept beyond the pins' row, so nothing crosses the frame.

    The lint's OUT_OF_CONTENT_BOX sees every line point, line label, stub and box (layout-0158).
    """
    built = _built(name)
    model = built.model
    lines = layout_of(model, HarnessLine).values()
    stubs = [m for m in layout_of(model, LinkMarker).values() if "line_stub" in m.key]
    assert lines
    assert stubs
    assert all(p.x >= 0 and p.y >= 0 for line in lines for p in line.points)
    assert all(m.x - m.width // 2 >= 0 for m in stubs)
    out = [f for f in built.findings if f.code == "OUT_OF_CONTENT_BOX"]
    assert out == []


@pytest.mark.parametrize("name", _FANS)
def test_each_leg_ends_on_its_pin_and_the_pin_draws_its_lead(name: str) -> None:
    """Defect 2: a leg ends at its pin's port, as a wire does, so the port's lead is drawn."""
    model = _built(name).model
    legs = 0
    for page in layout_of(model, Page).values():
        ends = {
            (leg.points[-1].x, leg.points[-1].y)
            for fan in page_slice(model, HarnessFanOut, page)
            for leg in fan.legs
        }
        legs += len(ends)
        reached = set()
        for placement in page_slice(model, SymbolPlacement, page):
            symbol = oriented_symbol(model, placement)
            if symbol is None:  # an unknown symbol key draws nothing
                continue
            wired = wired_local_ports(model, page, placement, symbol)
            for port in symbol.ports:
                at = _absolute(placement, port.position.x, port.position.y)
                if at in ends:
                    assert port.id in wired
                    reached.add(at)
        boxed = {end for end in ends - reached if _on_a_box(end, model, page)}
        assert reached | boxed == ends  # a boxed pin view draws no pin: its leg ends on the box
    assert legs


def _on_a_box(point: tuple[int, int], model, page) -> bool:
    x, y = point
    return any(
        (box.x <= x <= box.x + box.width and y in (box.y, box.y + box.height))
        or (box.y <= y <= box.y + box.height and x in (box.x, box.x + box.width))
        for box in page_slice(model, ConnectorBox, page)
    )


@pytest.mark.parametrize("name", [*_CASES, "study"])
def test_each_leaving_line_ends_on_its_stub_box_edge_with_no_thin_piece(name: str) -> None:
    """Defect 2: the line meets the middle of the box's near edge; no marker stub is drawn."""
    model = _built(name).model
    stubs = [m for m in layout_of(model, LinkMarker).values() if "line_stub" in m.key]
    lines = layout_of(model, HarnessLine).values()
    ends = {(p.x, p.y) for line in lines for p in (line.points[0], line.points[-1])}
    pages = layout_of(model, Page)
    for marker in stubs:
        assert marker.carrier is not None
        assert draws_as_line(model, marker.carrier)
        facing = marker_facing(model, marker)
        x, y = box_origin(marker, facing)
        edge = {
            (0, -1): (marker.x, y + marker.height),
            (0, 1): (marker.x, y),
            (1, 0): (x, marker.y),
            (-1, 0): (x + marker.width, marker.y),
        }[facing.dx, facing.dy]
        assert edge in ends
        page = next(p for p in pages.values() if p.id == marker.page)
        sheet = sheet_format_of(model, page.sheet_format)
        x1 = format_decimal(grid_to_mm(sheet.content_x_mm, marker.x, sheet.module_mm))
        y1 = format_decimal(grid_to_mm(sheet.content_y_mm, marker.y, sheet.module_mm))
        assert f'x1="{x1}" y1="{y1}"' not in markers_group(model, page)
    assert stubs


@pytest.mark.parametrize("name", [*_CASES, "study"])
def test_a_line_label_keeps_the_house_text_gap_from_its_line(name: str) -> None:
    """Defect 2: `-W11` touched its trunk; a label stands `TEXT_GAP` off every run of its line.

    A label with no such place is reported `LABEL_UNPLACED`, never placed silently.
    """
    model = _built(name).model
    results, findings = stage_results(model, read_inputs(model))
    unplaced = {s for f in findings if f.code == "LABEL_UNPLACED" for s in f.subjects}
    lines = [line for line in results.lines.lines if line.harness not in unplaced]
    for line in lines:
        near = pad(line.label, TEXT_GAP - 1)
        assert not any(through(seg, near) for seg in itertools.pairwise(line.points)), line
    assert lines


@pytest.mark.parametrize("name", [*_CASES, "study"])
def test_no_line_turns_back_on_itself(name: str) -> None:
    """Defect 2: the trunk of `-W11` ran past its split and back; a line stops on its ends.

    A line turns back only at a fan's split, where it runs on to a further pin row.
    """
    model = _built(name).model
    lines = layout_of(model, HarnessLine).values()
    splits = {
        (leg.points[0].x, leg.points[0].y)
        for fan in layout_of(model, HarnessFanOut).values()
        for leg in fan.legs
    }
    for line in lines:
        for a, b, c in zip(line.points, line.points[1:], line.points[2:], strict=False):
            one = (b.x - a.x, b.y - a.y)
            two = (c.x - b.x, c.y - b.y)
            back = one[0] * two[1] == one[1] * two[0] and one[0] * two[0] + one[1] * two[1] <= 0
            assert not back or (b.x, b.y) in splits, (line.harness, b)
    assert lines


def _study_box_and_symbols():
    built = _built("study")
    model = built.model
    tag = {f.id: (items(model)[f.item].tag, f.name) for f in functions(model).values()}
    by_tag = {one: fid for fid, one in tag.items()}
    placed = {p.function: p for p in layout_of(model, SymbolPlacement).values()}
    box = next(
        b for b in layout_of(model, ConnectorBox).values() if b.function == by_tag[("J10", "x1")]
    )
    return built, box, placed, by_tag


def test_hl19_the_box_over_k1_is_as_wide_as_its_cells_and_overlaps_no_text() -> None:
    """(layout-0173) `-K1-J10` is 64 wide, never stretched over K1's columns.

    UNDO: `box_views._box` takes `max(width, room.width)` again (probe hl19-stretch).
    """
    built, box, placed, by_tag = _study_box_and_symbols()
    assert box.width == 64
    assert len(box.cells) == 4
    coil, aux = by_tag[("K1", "coil")], by_tag[("K1", "aux")]
    found = [
        f
        for f in built.findings
        if f.code == "TEXT_OVERLAP" and {by_tag[("J10", "x1")], coil} <= set(f.subjects)
    ]
    assert found == []
    # the symbols keep their places in their circuits: coil and contact stand in two columns
    assert (placed[coil].x, placed[aux].x) == (232, 808)
    assert not box.x <= placed[coil].x <= box.x + box.width


def test_hl19_each_cell_of_the_box_has_a_routed_lead_to_its_symbol() -> None:
    """A cell's lead is an ordinary route that starts under the cell and ends at its symbol.

    UNDO: `engine.cells_placed` is skipped (the views stay in their columns, probe hl19-views).
    """
    built, box, _, _ = _study_box_and_symbols()
    routes = list(layout_of(built.model, Route).values())
    routed = 0
    for cell in box.cells:  # the first cell's join is a power symbol standing on its view
        centre = cell.x + cell.width // 2
        leads = [r for r in routes if cell.port in (r.a, r.b) and r.page == box.page]
        routed += bool(leads)
        assert all(any(pt.x == centre for pt in r.points) for r in leads), cell
        assert all(len({(pt.x, pt.y) for pt in r.points}) > 2 for r in leads), cell  # not a stub
    assert routed == 3


@pytest.mark.parametrize("name", [*_CASES, "study"])
def test_no_line_runs_along_an_outline_or_back_through_its_own_box(name: str) -> None:
    """Defect 3: `-W12` left P12 south, turned back through the box and ran along the outline.

    A line's own boxes are obstacles; it starts on a box's edge and leaves it outward.
    UNDO: `_lines._grid` drops the line's own boxes (probe f4-own-boxes).
    """
    built = _built(name)
    assert [f for f in built.findings if f.code == "LINE_ON_OUTLINE"] == []
    model = built.model
    boxes = layout_of(model, ConnectorBox).values()
    lines = layout_of(model, HarnessLine).values()
    assert boxes or name == "field_cable", name  # its cable has no plug: terminals to a motor
    assert lines, name
    for line in lines:
        for box in (b for b in boxes if b.page == line.page):
            inside = Box(x=box.x, y=box.y, width=box.width, height=box.height)
            runs = itertools.pairwise(Point(x=p.x, y=p.y) for p in line.points)
            hit = [run for run in runs if through(run, inside)]
            assert hit == [] or (name == "study" and _mated_stack(model, box)), (
                line.harness,
                box.function,
            )


def _mated_stack(model, box) -> bool:
    """Known, and the same before the box fix: `-W17`'s trunk to `-W17-P18` runs down through
    the mated stack `-K1-J10` / `-W17-P18`, whose lead side is the far side from the line.
    """
    one = functions(model)[box.function]
    return items(model)[one.item].tag in {"J10", "P18"}


@pytest.mark.parametrize("name", _FANS)
def test_each_pin_row_gets_its_own_fan_and_no_leg_runs_oblique_beyond_it(name: str) -> None:
    """Defect 4: study `-W11` reached `-X1:5/6` with 60 mm legs from `-X1:1/3`'s fan.

    Legs leaving one split reach one row: their pins lie within the fan distance (32 G) of each
    other along the facing axis. Each split stands on its line.
    """
    model = _built(name).model
    lines = layout_of(model, HarnessLine).values()
    splits = 0
    for fan in layout_of(model, HarnessFanOut).values():
        runs = [
            (a, b)
            for line in lines
            if (line.harness, line.page) == (fan.harness, fan.page)
            for a, b in itertools.pairwise(line.points)
        ]
        by_split: dict[tuple[int, int], list[int]] = {}
        for leg in fan.legs:
            start, knee, pin = leg.points[0], leg.points[1], leg.points[-1]
            by_split.setdefault((start.x, start.y), []).append(pin.y if knee.x == pin.x else pin.x)
            assert any(_on_run(start, run) for run in runs), (fan.harness, start)
        assert all(max(row) - min(row) <= 32 for row in by_split.values()), by_split
        splits += len(by_split)
    assert splits


def _on_run(point, run) -> bool:
    a, b = run
    return min(a.x, b.x) <= point.x <= max(a.x, b.x) and min(a.y, b.y) <= point.y <= max(a.y, b.y)
