"""The harness line, fan-out and stub builders: unique keys, ordered points, an off stub."""

from fransys_layout.engines.schematic.write.harness import (
    harness_fan_outs,
    harness_lines,
    line_stubs,
)
from fransys_layout.engines.schematic.write.keys import PREFIX, WriteKeys
from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLeg, DrawnLine, LineStub
from fransys_model.kernel import make_id
from fransys_model.layout import DrawingSet, MarkerSide, Page, PageRole, Side, StarKind
from fransys_model.vocab import Item, Port
from fransys_model.vocab.connectivity import Conductor

HARNESS = make_id(Item, ("h1",))
PORT = make_id(Port, ("f", "p1", "1"))
FAR = make_id(Port, ("g", "p2", "1"))
WIRES = [make_id(Conductor, ("c", str(n))) for n in range(2)]


def _set() -> DrawingSet:
    key = (*PREFIX, "drawing_set", "one")
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=1, produced_by="t"
    )


def _page(drawing_set: DrawingSet, number: int) -> Page:
    key = (*drawing_set.key, str(number))
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by="t",
    )


def _keys() -> WriteKeys:
    return WriteKeys(
        function={},
        port={},
        conductor={},
        item={HARNESS: ("h1",)},
        unit={},
        aspect_node={},
        port_function={},
        port_name={},
        item_function={},
    )


def _world() -> tuple[dict[int, DrawingSet], dict[tuple[int, int], Page]]:
    sets = {1: _set()}
    return sets, {(1, 1): _page(sets[1], 1), (1, 2): _page(sets[1], 2)}


def _line(page: int, points: tuple[Point, ...] = (Point(x=0, y=0), Point(x=8, y=0))) -> DrawnLine:
    return DrawnLine(
        harness=HARNESS,
        branch=0,
        drawing_set=1,
        page=page,
        points=points,
        text=Point(x=4, y=-2),
        label=Box(x=0, y=-6, width=8, height=8),
    )


def _stub(page: int) -> LineStub:
    return LineStub(
        harness=HARNESS,
        branch=0,
        drawing_set=1,
        page=page,
        port=PORT,
        far=FAR,
        at=Point(x=8, y=0),
        facing=Facing.E,
        box=Box(x=8, y=-4, width=24, height=8),
    )


def test_two_pages_of_one_branch_and_a_repeat_on_a_page_get_unique_keys() -> None:
    sets, page_of = _world()
    drawn = [_line(2), _line(1), _line(2)]
    records = harness_lines(_keys(), drawn, page_of, sets, "t")
    assert len({r.key for r in records}) == 3
    assert len({r.id for r in records}) == 3
    base = (*PREFIX, "harness_line", "h1", "branch", "0", "drawing_set", "one")
    assert [r.key for r in records] == [
        base,
        (*base, "page", "2"),
        (*base, "page", "2", "piece", "1"),
    ]


def test_points_and_text_are_stored_in_order() -> None:
    sets, page_of = _world()
    pts = (Point(x=0, y=0), Point(x=8, y=0), Point(x=8, y=16))
    (record,) = harness_lines(_keys(), [_line(1, pts)], page_of, sets, "t")
    assert [(p.index, p.x, p.y) for p in record.points] == [(0, 0, 0), (1, 8, 0), (2, 8, 16)]
    assert (record.text_x, record.text_y) == (4, -2)
    assert record.page == page_of[1, 1].id


def test_a_fan_out_has_one_leg_per_conductor() -> None:
    sets, page_of = _world()
    legs = tuple(
        DrawnLeg(conductor=c, points=(Point(x=8, y=0), Point(x=16, y=4 * n)))
        for n, c in enumerate(WIRES)
    )
    fan = DrawnFanOut(
        harness=HARNESS, branch=0, drawing_set=1, page=1, at=Point(x=8, y=0), legs=legs
    )
    (record,) = harness_fan_outs(_keys(), [fan], page_of, sets, "t")
    assert record.key[:4] == (*PREFIX, "harness_fan_out", "h1")
    assert (record.x, record.y) == (8, 0)
    assert [(leg.index, leg.conductor) for leg in record.legs] == list(enumerate(WIRES))
    assert [(p.x, p.y) for p in record.legs[1].points] == [(8, 0), (16, 4)]


def test_a_stub_is_an_off_marker_that_is_its_own_partner() -> None:
    sets, page_of = _world()
    first, second = line_stubs(_keys(), [_stub(1), _stub(2)], page_of, sets, "t")
    assert first.key[len(PREFIX) :] == (
        "link_marker",
        "line_stub",
        "h1",
        "branch",
        "0",
        "drawing_set",
        "one",
    )
    assert second.key == (*first.key, "page", "2")
    assert first.star is StarKind.OFF
    assert first.partner == first.id
    assert (first.port, first.far, first.carrier) == (PORT, FAR, HARNESS)
    assert first.facing is Side.E
    assert first.side is MarkerSide.OWNER
    assert (first.x, first.y, first.width, first.height) == (8, 0, 24, 8)


def test_the_builders_write_only_their_own_kinds_never_a_route() -> None:
    sets, page_of = _world()
    fan = DrawnFanOut(
        harness=HARNESS,
        branch=0,
        drawing_set=1,
        page=1,
        at=Point(x=8, y=0),
        legs=(DrawnLeg(conductor=WIRES[0], points=(Point(x=8, y=0), Point(x=16, y=4))),),
    )
    records = [
        *harness_lines(_keys(), [_line(1)], page_of, sets, "t"),
        *harness_fan_outs(_keys(), [fan], page_of, sets, "t"),
        *line_stubs(_keys(), [_stub(1)], page_of, sets, "t"),
    ]
    assert {type(r).__name__ for r in records} == {"HarnessLine", "HarnessFanOut", "LinkMarker"}
