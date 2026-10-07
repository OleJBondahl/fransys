"""Private to `write/`: the connector box, harness line, fan-out and stub builders (layout-0155)."""

from collections import Counter
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import PREFIX
from fransys_model.kernel import make_id
from fransys_model.layout import (
    BoxCell,
    BoxText,
    ConnectorBox,
    FanLeg,
    HarnessFanOut,
    HarnessLine,
    LinkMarker,
    MarkerSide,
    RoutePoint,
    Side,
    StarKind,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.geometry import Point
    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLine, LineStub
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.layout import DrawingSet, Page


def connector_boxes(
    keys: WriteKeys,
    boxes: Sequence[PlacedConnectorBox],
    page_of: Mapping[PageId, Page],
    sets: Mapping[int, DrawingSet],
    stamp: str,
) -> list[ConnectorBox]:
    """One `ConnectorBox` per placed box, keyed by its function, drawing set and second page."""
    seen: set[tuple[Id[Any], int]] = set()
    records = []
    # sets and pages in order, so a second page's key never depends on the input order
    for placed in sorted(boxes, key=lambda one: (one.drawing_set, one.page)):
        extra: AuthoringKey = ("drawing_set", *sets[placed.drawing_set].key[len(PREFIX) + 1 :])
        # a second page of one function in one set tells itself apart by its page number
        if (placed.function, placed.drawing_set) in seen:
            extra = (*extra, "page", str(placed.page))
        seen.add((placed.function, placed.drawing_set))
        key = (*PREFIX, "connector_box", *keys.function[placed.function], *extra)
        box = placed.box
        records.append(
            ConnectorBox(
                id=make_id(ConnectorBox, key),
                key=key,
                page=page_of[placed.drawing_set, placed.page].id,
                function=placed.function,
                x=box.x,
                y=box.y,
                width=box.width,
                height=box.height,
                texts=tuple(BoxText(index=i, x=at.x, y=at.y) for i, at in enumerate(placed.texts)),
                cells=tuple(
                    BoxCell(
                        index=i,
                        port=c.port,
                        x=c.box.x,
                        y=c.box.y,
                        width=c.box.width,
                        height=c.box.height,
                    )
                    for i, c in enumerate(placed.cells)
                ),
                produced_by=stamp,
            )
        )
    return records


def _tails[T: (DrawnLine, DrawnFanOut, LineStub)](
    drawn: Sequence[T], sets: Mapping[int, DrawingSet]
) -> list[tuple[T, AuthoringKey]]:
    """Each piece with its key tail: drawing set, then page and repeat number once needed."""
    on_line: Counter[tuple[Id[Any], int, int]] = Counter()
    on_page: Counter[tuple[Id[Any], int, int, int]] = Counter()
    tails = []
    for one in sorted(drawn, key=lambda one: (one.drawing_set, one.page)):
        line = (one.harness, one.branch, one.drawing_set)
        tail: AuthoringKey = ("drawing_set", *sets[one.drawing_set].key[len(PREFIX) + 1 :])
        if on_line[line]:
            tail = (*tail, "page", str(one.page))
        if on_page[*line, one.page]:
            tail = (*tail, "piece", str(on_page[*line, one.page]))
        on_line[line] += 1
        on_page[*line, one.page] += 1
        tails.append((one, tail))
    return tails


def _route(points: Sequence[Point]) -> tuple[RoutePoint, ...]:
    return tuple(RoutePoint(index=i, x=p.x, y=p.y) for i, p in enumerate(points))


def harness_lines(
    keys: WriteKeys,
    lines: Sequence[DrawnLine],
    page_of: Mapping[PageId, Page],
    sets: Mapping[int, DrawingSet],
    stamp: str,
) -> list[HarnessLine]:
    """One `HarnessLine` per drawn line, keyed by harness, branch, drawing set and page."""
    records = []
    for line, tail in _tails(lines, sets):
        item, branch = keys.item[line.harness], str(line.branch)
        key = (*PREFIX, "harness_line", *item, "branch", branch, *tail)
        records.append(
            HarnessLine(
                id=make_id(HarnessLine, key),
                key=key,
                page=page_of[line.drawing_set, line.page].id,
                harness=line.harness,
                branch=line.branch,
                points=_route(line.points),
                text_x=line.text.x,
                text_y=line.text.y,
                produced_by=stamp,
            )
        )
    return records


def harness_fan_outs(
    keys: WriteKeys,
    fan_outs: Sequence[DrawnFanOut],
    page_of: Mapping[PageId, Page],
    sets: Mapping[int, DrawingSet],
    stamp: str,
) -> list[HarnessFanOut]:
    """One `HarnessFanOut` per drawn fan-out, one `FanLeg` per conductor."""
    records = []
    for fan, tail in _tails(fan_outs, sets):
        item, branch = keys.item[fan.harness], str(fan.branch)
        key = (*PREFIX, "harness_fan_out", *item, "branch", branch, *tail)
        legs = tuple(
            FanLeg(index=i, conductor=leg.conductor, points=_route(leg.points))
            for i, leg in enumerate(fan.legs)
        )
        records.append(
            HarnessFanOut(
                id=make_id(HarnessFanOut, key),
                key=key,
                page=page_of[fan.drawing_set, fan.page].id,
                harness=fan.harness,
                branch=fan.branch,
                x=fan.at.x,
                y=fan.at.y,
                legs=legs,
                produced_by=stamp,
            )
        )
    return records


def line_stubs(
    keys: WriteKeys,
    stubs: Sequence[LineStub],
    page_of: Mapping[PageId, Page],
    sets: Mapping[int, DrawingSet],
    stamp: str,
) -> list[LinkMarker]:
    """One off `LinkMarker` per leaving-line stub; it is its own partner."""
    records = []
    for stub, tail in _tails(stubs, sets):
        item, branch = keys.item[stub.harness], str(stub.branch)
        key = (*PREFIX, "link_marker", "line_stub", *item, "branch", branch, *tail)
        marker_id = make_id(LinkMarker, key)
        records.append(
            LinkMarker(
                id=marker_id,
                key=key,
                page=page_of[stub.drawing_set, stub.page].id,
                port=stub.port,
                side=MarkerSide.OWNER,
                partner=marker_id,
                x=stub.at.x,
                y=stub.at.y,
                width=stub.box.width,
                height=stub.box.height,
                produced_by=stamp,
                star=StarKind.OFF,
                far=stub.far,
                carrier=stub.harness,
                facing=Side[stub.facing.name],
            )
        )
    return records
