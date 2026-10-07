"""The diagram placer (BD5): routes, tabs, cut stubs, markers and labels on hand facts."""

from dataclasses import replace
from functools import cache
from itertools import pairwise

from diagram_models import chain

from fransys_layout import lay_out_cables
from fransys_layout.engines.diagram.frame import build_frame
from fransys_layout.engines.diagram.place import place_diagram
from fransys_layout.engines.diagram.read import read_diagrams
from fransys_layout.engines.diagram.sizes import MARKER_W, TEXT_LEAD, tab_reach
from fransys_layout.engines.diagram.values import BoxFacts, DiagramFacts, LineFacts
from fransys_layout.engines.diagram.write import write_diagrams
from fransys_layout.geometry import WIRING_GRID, Facing
from fransys_model.kernel import Id
from fransys_model.layout import DiagramLine, DiagramMarker, layout_of

TH = 8


def _id(name: str) -> Id:
    return Id(kind="item", value=name)


def _box(name: str) -> BoxFacts:
    return BoxFacts(box=_id(name), text_widths=(40,), dashed=False)


def _line(a: str, b: str, tab_a: int | None = None, tab_b: int | None = None) -> LineFacts:
    cable = Id(kind="item", value=f"w-{a}{b}")
    return LineFacts(cable=cable, a=_id(a), b=_id(b), label_width=20, tab_a=tab_a, tab_b=tab_b)


def _facts(boxes, lines, width: int = 1868, height: int = 1248) -> DiagramFacts:
    return DiagramFacts(
        unit=None,
        boxes=tuple(boxes),
        lines=tuple(lines),
        text_height=TH,
        turn_penalty=1,
        crossing_penalty=1,
        width=width,
        height=height,
    )


def _place(facts: DiagramFacts):
    placed = place_diagram(facts)
    assert placed is not None
    return placed


def _lines(placed):
    return {line.cable.value: line for s in placed.sheets for line in s.lines}


def _star(leaves: int):
    names = [f"l{i}" for i in range(leaves)]
    return _facts([_box("hub"), *(_box(n) for n in names)], [_line("hub", n) for n in names])


def _orthogonal(points) -> bool:
    return all(p.x == q.x or p.y == q.y for p, q in pairwise(points))


@cache
def _cut():
    boxes = [_box(f"b{i}") for i in range(12)]
    lines = [_line(f"b{i}", f"b{i + 1}") for i in range(11)]
    return _place(_facts(boxes, lines, width=600))


def test_a_straight_line_is_two_points_from_a_to_b():
    """Equal end y: no track, two points a to b; kills: a jog on a straight run, a/b swapped."""
    placed = _place(_facts([_box("hub"), _box("a")], [_line("hub", "a")]))
    line = _lines(placed)["w-huba"]
    boxes = {b.box.value: b for b in placed.sheets[0].boxes}
    assert len(line.points) == 2
    assert line.points[0].y == line.points[1].y
    assert line.points[0].x == boxes["hub"].x + boxes["hub"].width
    assert line.points[1].x == boxes["a"].x
    assert (line.a, line.b) == (_id("hub"), _id("a"))


def test_a_reversed_line_runs_from_a_all_the_same():
    """Line a to hub, with hub in the left column: points still start at a; kills: no reverse."""
    placed = _place(_facts([_box("hub"), _box("a")], [_line("a", "hub")]))
    boxes = {b.box.value: b for b in placed.sheets[0].boxes}
    first = _lines(placed)["w-ahub"].points[0]
    assert first.x == boxes["a"].x  # a is the right box; its west edge


def test_a_jogged_line_goes_through_its_track():
    """The bending lines of a fan are orthogonal, on a track x, on the grid; kills: a diagonal."""
    placed = _place(_star(3))
    lines = list(_lines(placed).values())
    bending = [ln for ln in lines if len(ln.points) > 2]
    assert bending
    for line in lines:
        assert _orthogonal(line.points)
        assert all(p.x % WIRING_GRID == p.y % WIRING_GRID == 0 for p in line.points)
        assert all(p != q for p, q in pairwise(line.points))
    for line in bending:
        assert line.points[1].x == line.points[2].x  # the vertical run on its track


def test_crossing_lines_take_distinct_tracks_and_no_vertical_runs_overlap():
    """A fan of four needs two tracks; two vertical runs on one x never overlap in y."""
    placed = _place(_star(4))
    runs = []
    for line in _lines(placed).values():
        for p, q in pairwise(line.points):
            if p.x == q.x and p.y != q.y:
                runs.append((p.x, min(p.y, q.y), max(p.y, q.y)))
    assert len({x for x, _, _ in runs}) >= 2
    for i, (x, lo, hi) in enumerate(runs):
        for x2, lo2, hi2 in runs[i + 1 :]:
            assert x != x2 or hi <= lo2 or hi2 <= lo  # kills: overlapping runs on one track


def test_a_same_column_line_detours_to_the_reserved_track():
    """Line a-b inside column 1 leaves both east edges for track count+1; kills: wrong track."""
    boxes = [_box("hub"), _box("a"), _box("b")]
    facts = _facts(boxes, [_line("hub", "a"), _line("hub", "b"), _line("a", "b")])
    placed = _place(facts)
    line = _lines(placed)["w-ab"]
    by = {b.box.value: b for b in placed.sheets[0].boxes}
    edge = by["a"].x + by["a"].width
    first, *_, last = line.points
    assert first.x == last.x == edge
    assert max(p.x for p in line.points) > edge
    assert len({p.x for p in line.points}) == 2
    frame = build_frame(facts)
    assert frame is not None
    trailing = frame.sheets[0].channels[-1]
    assert max(p.x for p in line.points) == trailing.track_x(trailing.count + 1)
    assert _orthogonal(line.points)


def test_a_tab_moves_the_touch_point_out_and_is_placed_with_its_box():
    """A 20 wide tab at hub: touch at the tab's outer edge, a PlacedTab E; kills: no tab."""
    placed = _place(_facts([_box("hub"), _box("a")], [_line("hub", "a", tab_a=20)]))
    hub = next(b for b in placed.sheets[0].boxes if b.box.value == "hub")
    line = _lines(placed)["w-huba"]
    (tab,) = hub.tabs
    assert line.points[0].x == hub.x + hub.width + tab_reach(20)
    assert (tab.side, tab.text_width, tab.cable) == (Facing.E, 20, line.cable)
    assert tab.y == line.points[0].y
    leaf = next(b for b in placed.sheets[0].boxes if b.box.value == "a")
    assert leaf.tabs == ()  # kills: a tab on the box without one


def test_a_west_tab_is_on_the_west_side():
    placed = _place(_facts([_box("hub"), _box("a")], [_line("hub", "a", tab_b=24)]))
    leaf = next(b for b in placed.sheets[0].boxes if b.box.value == "a")
    assert [(t.side, t.text_width) for t in leaf.tabs] == [(Facing.W, 24)]
    assert _lines(placed)["w-huba"].points[-1].x == leaf.x - tab_reach(24)


def test_a_cut_line_is_a_stub_and_a_marker_on_each_sheet():
    """Each cut line has a half per sheet ending at its marker; kills: a missing half or marker."""
    placed = _cut()
    assert len(placed.sheets) >= 2
    numbers = [s.number for s in placed.sheets]
    assert numbers == list(range(1, len(numbers) + 1))
    cut_cables = {m.cable for s in placed.sheets for m in s.markers}
    assert len(cut_cables) == len(placed.sheets) - 1
    for cable in cut_cables:
        halves = [(s, ln) for s in placed.sheets for ln in s.lines if ln.cable == cable]
        assert len(halves) == 2
        for sheet, line in halves:
            (marker,) = (m for m in sheet.markers if m.cable == cable)
            other = next(s.number for s, _ in halves if s.number != sheet.number)
            assert marker.at_sheet == other
            assert (marker.x, marker.y) == (line.points[-1].x, line.points[-1].y)
            assert len(line.points) == 2


def test_a_cut_stub_ends_inside_its_zone():
    """Left stub ends MARKER_W short of the zone's end; the right one at MARKER_W."""
    placed = _cut()
    first, second = placed.sheets[0], placed.sheets[1]
    (marker,) = (m for m in first.markers)
    (back,) = (m for m in second.markers if m.cable == marker.cable)
    assert back.x == MARKER_W
    assert marker.x % WIRING_GRID == 0
    right = max(b.x + b.width for b in first.boxes)
    assert right < marker.x
    line = next(ln for ln in second.lines if ln.cable == marker.cable)
    assert line.points[0].x > MARKER_W  # the half starts at its box, left of its marker


def test_a_label_sits_above_the_longest_horizontal_run():
    """Straight line: label centred over the run, one text lead above it; kills: label below."""
    placed = _place(_facts([_box("hub"), _box("a")], [_line("hub", "a")]))
    line = _lines(placed)["w-huba"]
    p, q = line.points
    assert line.text_x == (p.x + q.x) // 2 // WIRING_GRID * WIRING_GRID
    assert line.text_y <= p.y - TH // 2 - TEXT_LEAD
    assert line.text_y > p.y - 4 * WIRING_GRID  # close to the run


def test_a_diagram_that_does_not_fit_is_none():
    assert place_diagram(_facts([_box("a"), _box("b")], [_line("a", "b")], height=8)) is None


def test_the_same_facts_give_the_same_placement():
    assert _place(_star(3)) == _place(_star(3))


def test_a_cut_chain_writes_as_records_with_matching_markers():
    """write_diagrams accepts the cut placement: every marker finds its line on its sheet."""
    (facts,) = read_diagrams(chain(12))
    placed = _place(replace(facts, width=600))
    assert len(placed.sheets) >= 2
    model = write_diagrams(lay_out_cables(chain(12))[0], (placed,))
    markers = layout_of(model, DiagramMarker)
    assert len(markers) == 2 * (len(placed.sheets) - 1)
    lines = layout_of(model, DiagramLine)
    assert all(m.line in lines for m in markers.values())
