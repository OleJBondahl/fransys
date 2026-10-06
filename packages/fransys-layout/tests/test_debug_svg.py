"""The debug drawing helper: one SVG per page of a stage-side `Layout` (WP7, WP8,
package-layout.md 9)."""

import dataclasses

from debug_svg import WIRE_COLOURS, write_debug_pages
from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import (
    LabelKind,
    Layout,
    LinkMarker,
    MarkerSide,
    PlacedLabel,
    Route,
    RoutePoint,
    place,
)
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import _reference_band


def _layout(*pages, routes=(), markers=(), labels=()):
    placed = tuple(
        function
        for plan, columns, drawn_functions in pages
        for function in place(
            plan, columns, drawn_functions, PageStacking(profile=PROFILE, sheet=SHEET)
        )[0]
    )
    return Layout(
        pages=tuple(plan for plan, _, _ in pages),
        placed=placed,
        routes=routes,
        decisions=(),
        markers=markers,
        labels=labels,
    )


def _label(number: int, kind: LabelKind, *, x: int, y: int, page: int = 1):
    """A label box of `kind` at `(x, y)`, the shape `place_slot_labels` returns."""
    return PlacedLabel(
        kind=kind,
        subject=hid("function", number),
        slot="tag",
        drawing_set=1,
        page=page,
        box=Box(x=x, y=y, width=32, height=8),
    )


def _route(number: int, net: int, *corners, page: int = 1):
    """Route `number` of physical net `net` through `corners`, as `(x, y)` pairs."""
    return Route(
        connection=hid("conductor", number),
        physical_net=hid("net", net),
        drawing_set=1,
        page=page,
        a=hid("port", number * 10 + 1),
        b=hid("port", number * 10 + 2),
        points=tuple(
            RoutePoint(index=index, at=Point(x=x, y=y)) for index, (x, y) in enumerate(corners)
        ),
    )


def test_one_svg_per_page_holds_its_boxes_and_port_dots(tmp_path) -> None:
    """Two cells: a body box and a keep-out box each, two port dots each, one content box."""
    plan = page_plan(("a",))
    paths = write_debug_pages(
        _layout((plan, (column("a", (1, 2)),), (drawn(1), drawn(2)))), tmp_path, sheet=SHEET
    )
    svg = paths[0].read_text(encoding="utf-8")
    assert [path.name for path in paths] == ["drawing_set1-page1.svg"]
    assert svg.count("<circle") == 4
    assert svg.count("<rect") == 2 + 2 * 2
    assert f'width="{SHEET.content_width}" height="{SHEET.content_height}"' in svg
    # One dashed keep-out box per function, 56 G wide, and a solid body box 16 G wide.
    assert svg.count("stroke-dasharray") == 2
    assert svg.count('width="56" height="32" fill="none" stroke="#c08080"') == 2
    assert svg.count('width="16" height="32" fill="#eef2f8"') == 2
    # M4: every page keeps a reference band along its top, so the first row's keep-out top
    # stands one band below the content box's top, its `in` port there and its `out` port 32 G
    # lower.
    band = _reference_band(SHEET, PROFILE)
    assert band > 0
    assert f'<circle cx="8" cy="{band}" r="4" fill="#c03030"/>' in svg
    assert f'<circle cx="8" cy="{band + 32}" r="4" fill="#c03030"/>' in svg
    # D3: the lower keep-out top stands `row_spacing` below the upper keep-out bottom
    # (band + 32 G), not pushed to the page foot.
    lower_in = band + 32 + PROFILE.row_spacing
    assert PROFILE.row_spacing == 104
    assert f'<circle cx="8" cy="{lower_in}" r="4" fill="#c03030"/>' in svg
    assert f'<circle cx="8" cy="{lower_in + 32}" r="4" fill="#c03030"/>' in svg


def test_pages_are_written_in_drawing_set_and_page_order_with_their_own_cells(tmp_path) -> None:
    """A page draws only the functions placed on it, whatever order the pages came in."""
    first = page_plan(("a",))
    second = dataclasses.replace(page_plan(("b",), number=2), title="second")
    layout = _layout(
        (second, (column("b", (2, 3)),), (drawn(2), drawn(3))),
        (first, (column("a", (1,)),), (drawn(1),)),
    )
    paths = write_debug_pages(layout, tmp_path, sheet=SHEET)
    assert [path.name for path in paths] == ["drawing_set1-page1.svg", "drawing_set1-page2.svg"]
    assert paths[0].read_text(encoding="utf-8").count("<circle") == 2
    assert paths[1].read_text(encoding="utf-8").count("<circle") == 4
    assert "second" in paths[1].read_text(encoding="utf-8")


def test_routes_are_polylines_in_their_nets_colour_with_a_junction_dot(tmp_path) -> None:
    """Two branches of one net meet at the port they share; a second net is drawn apart."""
    layout = _layout(
        (page_plan(("a",)), (column("a", (1, 2)),), (drawn(1), drawn(2))),
        routes=(
            _route(1, 1, (8, 0), (8, 200)),
            _route(2, 1, (8, 0), (8, 48), (200, 48)),
            # Another net ending on net 1's wire is a crossing, not a junction.
            _route(3, 2, (8, 200), (200, 200)),
        ),
    )
    svg = write_debug_pages(layout, tmp_path, sheet=SHEET)[0].read_text(encoding="utf-8")
    assert svg.count("<polyline") == 3
    assert '<polyline points="8,0 8,48 200,48"' in svg
    assert svg.count(f'stroke="{WIRE_COLOURS[0]}"') == 2
    assert svg.count(f'stroke="{WIRE_COLOURS[1]}"') == 1
    # The two branches of net 1 end on one another only at the port they share.
    assert svg.count('r="5" fill="#101010"') == 1
    assert '<circle cx="8" cy="0" r="5" fill="#101010"/>' in svg


def test_a_marker_is_a_triangle_pointing_away_on_the_owner_side(tmp_path) -> None:
    """The owner's triangle points right and both carry the partner's `p<page>`.

    A visual aid only, the page alone, not the real printed text (decision layout-0089): this
    helper has no `Model` to read LD3's `#n`, column or row from, and a stage marker no longer
    carries the partner's column.
    """
    layout = _layout(
        (page_plan(("a",)), (column("a", (1,)),), (drawn(1),)),
        markers=(
            LinkMarker(
                connection=hid("conductor", 1),
                port=hid("port", 12),
                side=MarkerSide.OWNER,
                drawing_set=1,
                page=1,
                at=Point(x=8, y=32),
                box=Box(x=8, y=28, width=24, height=8),
                partner_page=2,
            ),
            LinkMarker(
                connection=hid("conductor", 2),
                port=hid("port", 22),
                side=MarkerSide.USER,
                drawing_set=1,
                page=1,
                at=Point(x=200, y=32),
                box=Box(x=176, y=28, width=24, height=8),
                partner_page=1,
            ),
        ),
    )
    svg = write_debug_pages(layout, tmp_path, sheet=SHEET)[0].read_text(encoding="utf-8")
    assert '<polygon points="8,24 8,40 24,32"' in svg
    assert '<polygon points="200,24 200,40 184,32"' in svg
    assert ">p2<" in svg
    assert ">p1<" in svg


def test_a_page_draws_only_its_own_routes_and_markers(tmp_path) -> None:
    """A route of page 2 is not drawn on page 1, the same rule the placed functions follow."""
    layout = _layout(
        (page_plan(("a",)), (column("a", (1,)),), (drawn(1),)),
        (dataclasses.replace(page_plan(("b",), number=2)), (column("b", (2,)),), (drawn(2),)),
        routes=(_route(1, 1, (8, 0), (8, 200), page=2),),
        markers=(
            LinkMarker(
                connection=hid("conductor", 1),
                port=hid("port", 12),
                side=MarkerSide.USER,
                drawing_set=1,
                page=2,
                at=Point(x=8, y=200),
                box=Box(x=8, y=196, width=24, height=8),
                partner_page=1,
            ),
        ),
    )
    paths = write_debug_pages(layout, tmp_path, sheet=SHEET)
    first, second = (path.read_text(encoding="utf-8") for path in paths)
    assert (first.count("<polyline"), first.count("<polygon")) == (0, 0)
    assert (second.count("<polyline"), second.count("<polygon")) == (1, 1)


def _marker_at(box: Box, *, page: int = 1):
    return LinkMarker(
        connection=hid("conductor", 1),
        port=hid("port", 12),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=page,
        at=Point(x=box.x, y=box.y + 4),
        box=box,
        partner_page=2,
    )


def test_a_marker_box_is_drawn_dashed_in_its_own_colour_on_its_own_page(tmp_path) -> None:
    """The box the router avoids is visible: orange and dashed, not a label's violet."""
    layout = _layout(
        (page_plan(("a",)), (column("a", (1,)),), (drawn(1),)),
        (dataclasses.replace(page_plan(("b",), number=2)), (column("b", (2,)),), (drawn(2),)),
        markers=(_marker_at(Box(x=8, y=196, width=24, height=8), page=2),),
    )
    first, second = (
        path.read_text(encoding="utf-8")
        for path in write_debug_pages(layout, tmp_path, sheet=SHEET)
    )
    assert (
        '<rect x="8" y="196" width="24" height="8" fill="none" stroke="#b06020" '
        'stroke-width="1" stroke-dasharray="3 2"/>'
    ) in second
    assert 'stroke="#b06020"' not in first
    assert 'stroke="#7a3a9a"' not in second


def test_a_marker_box_outside_the_content_box_is_inside_the_canvas(tmp_path) -> None:
    """Like a label box, a marker box that leaves the sheet widens the canvas, not clipped."""
    layout = _layout(
        (page_plan(("a",)), (column("a", (1,)),), (drawn(1),)),
        markers=(_marker_at(Box(x=SHEET.content_width + 200, y=8, width=24, height=8)),),
    )
    svg = write_debug_pages(layout, tmp_path, sheet=SHEET)[0].read_text(encoding="utf-8")
    assert f'width="{SHEET.content_width + 200 + 24 + 64 + 64}"' in svg


def test_label_boxes_are_drawn_on_their_own_page_named_by_their_kind(tmp_path) -> None:
    """WP10: one violet box per `PlacedLabel`, and page 2 keeps its own."""
    layout = _layout(
        (page_plan(("a",)), (column("a", (1,)),), (drawn(1),)),
        (dataclasses.replace(page_plan(("b",), number=2)), (column("b", (2,)),), (drawn(2),)),
        labels=(
            _label(1, LabelKind.TAG, x=24, y=12),
            _label(1, LabelKind.CROSS_REFERENCE, x=24, y=20),
            _label(2, LabelKind.WIRE, x=64, y=40, page=2),
        ),
    )
    first, second = (
        path.read_text(encoding="utf-8")
        for path in write_debug_pages(layout, tmp_path, sheet=SHEET)
    )
    assert first.count('stroke="#7a3a9a"') == 2
    assert '<rect x="24" y="12" width="32" height="8"' in first
    assert ">tag<" in first
    assert ">cross_reference<" in first
    assert second.count('stroke="#7a3a9a"') == 1
    assert ">wire<" in second
    assert ">tag<" not in second
