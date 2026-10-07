"""The diagram frame (BD5): box sizes, ends, channels, sheets and cuts on hand facts."""

from functools import cache

from diagram_models import station

from fransys_layout.engines.diagram.frame import build_frame
from fransys_layout.engines.diagram.read import read_diagrams
from fransys_layout.engines.diagram.sizes import (
    MARKER_W,
    PAGE_PAD,
    TRACK_PITCH,
    attach_pitch,
    label_room,
    tab_reach,
)
from fransys_layout.engines.diagram.values import BoxFacts, DiagramFacts, LineFacts
from fransys_layout.geometry import WIRING_GRID, Facing, snap_up
from fransys_layout.stages.channel import plan_channel
from fransys_model.kernel import Id
lazy from fransys_layout.engines.diagram.frame_values import Frame

TH = 8


def _id(name: str) -> Id:
    return Id(kind="item", value=name)


def _box(name: str, *texts: int) -> BoxFacts:
    return BoxFacts(box=_id(name), text_widths=texts or (40,), dashed=False)


def _line(a: str, b: str, label: int = 20, tab_a: int | None = None, tab_b: int | None = None):
    cable = Id(kind="item", value=f"w-{a}{b}")
    return LineFacts(cable=cable, a=_id(a), b=_id(b), label_width=label, tab_a=tab_a, tab_b=tab_b)


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


def _build(facts: DiagramFacts) -> Frame:
    frame = build_frame(facts)
    assert frame is not None
    return frame


def _boxes(frame):
    return {b.box: b for s in frame.sheets for c in s.columns for b in c.boxes}


def _star(leaves: int, **kw):
    names = [f"l{i}" for i in range(leaves)]
    boxes = [_box("hub"), *(_box(n) for n in names)]
    return _facts(boxes, [_line("hub", n) for n in names], **kw)


def test_box_width_fits_the_widest_text_and_the_column_is_uniform():
    """Widths 40 and 100: column 1 holds both, both get the widest; kills: first text."""
    facts = _facts(
        [_box("hub"), _box("a", 40), _box("b", 30, 100)], [_line("hub", "a"), _line("hub", "b")]
    )
    frame = _build(facts)
    boxes = _boxes(frame)
    assert boxes[_id("a")].width == boxes[_id("b")].width == snap_up(100 + 16)
    assert boxes[_id("hub")].width == snap_up(40 + 16)  # kills: one width for all columns


def test_height_fits_the_ends_and_the_texts():
    """Four ends on one side need (4+1) pitches; a three-text box needs its text; kills: no +1."""
    frame = _build(_star(4))
    assert _boxes(frame)[_id("hub")].height == snap_up(5 * attach_pitch(TH))
    tall = _facts([_box("a", 40, 40, 40), _box("b")], [_line("a", "b")])
    assert _boxes(_build(tall))[_id("a")].height == snap_up(3 * TH + 2 * (WIRING_GRID // 2) + 16)


def test_columns_are_centred_on_the_tallest():
    """The hub column is centred on the leaf column; kills: top-aligned columns."""
    frame = _build(_star(3))
    boxes = _boxes(frame)
    leaves = [boxes[_id(f"l{i}")] for i in range(3)]
    hub = boxes[_id("hub")]
    low, high = leaves[0].y, leaves[-1].y + leaves[-1].height
    assert low == PAGE_PAD
    assert hub.y == PAGE_PAD + snap_up(((high - low) - hub.height) // 2)


def test_ends_are_ordered_by_the_far_boxs_top_then_line():
    """Lines hub-c, hub-a, hub-b: the hub's ends run a, b, c (lines 1, 2, 0); kills: line order."""
    boxes = [_box("hub"), _box("a"), _box("b"), _box("c")]
    facts = _facts(boxes, [_line("hub", "c"), _line("hub", "a"), _line("hub", "b")])
    frame = _build(facts)
    hub = _boxes(frame)[_id("hub")]
    assert [e.line for e in hub.ends] == [1, 2, 0]
    assert [e.y for e in hub.ends] == [hub.y + attach_pitch(TH) * k for k in (1, 2, 3)]


def test_the_box_in_the_lower_column_is_left_whatever_the_line_says():
    """Line (leaf, hub) still leaves the hub's east edge and enters the leaf's west edge."""
    facts = _facts([_box("hub"), _box("a"), _box("b")], [_line("a", "hub"), _line("b", "hub")])
    boxes = _boxes(_build(facts))
    assert {e.side for e in boxes[_id("hub")].ends} == {Facing.E}  # kills: left is a
    assert {e.side for e in boxes[_id("a")].ends} == {Facing.W}


def test_a_tab_touches_its_outer_edge_and_widens_the_channel():
    """A 20 wide tab at the hub end: touch x is edge + reach; kills: no tab."""
    plain = _build(_facts([_box("hub"), _box("a")], [_line("hub", "a")]))
    tabbed = _build(_facts([_box("hub"), _box("a")], [_line("hub", "a", tab_a=20)]))
    hub = _boxes(tabbed)[_id("hub")]
    (end,) = hub.ends
    assert hub.touch_x(end) == hub.x + hub.width + tab_reach(20)
    (before,), (after,) = plain.sheets[0].channels[:1], tabbed.sheets[0].channels[:1]
    assert after.tab_l == tab_reach(20)
    assert before.tab_l == 0
    assert after.width - before.width == tab_reach(20)
    west = _facts([_box("hub"), _box("a")], [_line("hub", "a", tab_b=20)])
    leaf = _boxes(_build(west))[_id("a")]
    assert leaf.touch_x(leaf.ends[0]) == leaf.x - tab_reach(20)  # kills: tab on wrong side


def test_the_channel_widens_by_a_track_pitch_per_track():
    """Ends of a fan differ in y, so its cores bend: K is the plan's count and width follows it."""
    for leaves in (2, 3, 4):
        frame = _build(_star(leaves))
        (ch, _last) = frame.sheets[0].channels
        cores = []
        for line in range(leaves):
            (_, _, left), (_, _, right) = frame.ends_of(line)
            cores.append((line, left.y, right.y))
        plan = plan_channel(cores)
        assert plan is not None
        assert ch.count == plan.count >= 1  # kills: K ignored
        label = label_room(20)
        assert ch.width == ch.tab_l + label + (ch.count + 1) * TRACK_PITCH + label + ch.tab_r
        assert {t.line for t in ch.tracks} == {c[0] for c in cores if c[1] != c[2]}
    one = _build(_star(1)).sheets[0].channels[0]
    assert one.count == 0  # kills: a straight core takes a track
    assert one.width == label_room(20) * 2 + TRACK_PITCH
    assert one.track_x(1) == one.start + label_room(20) + TRACK_PITCH


def test_a_same_column_line_adds_a_track_pitch_after_the_last_column():
    """Lines hub-a, hub-b, a-b: a-b lies in column 1, gains a pitch; kills: S ignored."""
    boxes = [_box("hub"), _box("a"), _box("b")]
    both = _build(_facts(boxes, [_line("hub", "a"), _line("hub", "b"), _line("a", "b")]))
    none = _build(_facts(boxes, [_line("hub", "a"), _line("hub", "b")]))
    trailing = both.sheets[0].channels[-1]
    assert trailing.same == (2,)
    assert trailing.right is None
    assert trailing.width == label_room(20) + 2 * TRACK_PITCH
    assert none.sheets[0].channels[-1].width == 2 * PAGE_PAD  # nothing routed there
    ends = [e for b in _boxes(both).values() for e in b.ends if e.line == 2]
    assert [e.side for e in ends] == [Facing.E, Facing.E]  # both leave east edges


def test_the_diagram_is_none_when_a_column_is_taller_than_the_sheet():
    assert build_frame(_star(30, height=600)) is None  # kills: no height check
    assert build_frame(_star(3, height=600)) is not None


def test_the_diagram_is_none_when_a_column_is_wider_than_a_sheet():
    assert build_frame(_facts([_box("a", 900), _box("b")], [_line("a", "b")], width=700)) is None


def _path(n: int, width: int):
    boxes = [_box(f"b{i}") for i in range(n)]
    return _facts(boxes, [_line(f"b{i}", f"b{i + 1}") for i in range(n - 1)], width=width)


@cache
def _cut_frames():
    return _build(_path(12, 600)), _build(_path(12, 20000))


def test_columns_fill_a_sheet_until_the_next_one_would_not_fit():
    """The cut falls after the last column that fits; sheets number from 1; kills: early cut."""
    small, big = _cut_frames()
    assert [s.number for s in small.sheets] == list(range(1, len(small.sheets) + 1))
    assert len(small.sheets) >= 2
    assert len(small.cuts) == len(small.sheets) - 1
    first, cut = small.sheets[0], small.cuts[0]
    last = first.columns[-1]
    big_cols = list(big.sheets[0].columns)
    gap = big.sheets[0].channels[last.index].width
    nxt = big_cols[last.index + 1]
    limit = 600 - PAGE_PAD
    assert last.x + last.width + cut.left_zone <= limit
    assert last.x + last.width + gap + nxt.width + cut.left_zone > limit  # kills: cut too early
    assert (cut.left, cut.right, cut.left_sheet) == (last.index, last.index + 1, 1)
    leading_zone = cut.tab_r + label_room(20) + MARKER_W
    assert small.sheets[1].columns[0].x == leading_zone
    assert small.sheets[0].columns[0].x == PAGE_PAD
    assert small.sheets[0].channels[-1].left != last.index  # no channel drawn at a cut


def test_a_cut_keeps_every_line_end_on_its_own_sheet():
    small, _ = _cut_frames()
    cut = small.cuts[0]
    (line,) = cut.lines
    sheets = [number for number, _box_, _end in small.ends_of(line)]
    assert sheets == [1, 2]


def test_the_station_frame_is_five_boxes_in_two_columns_all_on_the_grid():
    (facts,) = read_diagrams(station())
    frame = _build(facts)
    (sheet,) = frame.sheets
    first, second = sheet.columns
    assert (len(first.boxes), len(second.boxes)) == (1, 4)
    assert frame.cuts == ()
    numbers = []
    for column in sheet.columns:
        numbers += [column.x, column.width]
        for box in column.boxes:
            numbers += [box.x, box.y, box.width, box.height]
            numbers += [e.y for e in box.ends] + [box.touch_x(e) for e in box.ends]
    for ch in sheet.channels:
        numbers += [ch.start, ch.width, ch.tab_l, ch.tab_r, ch.label]
        numbers += [ch.track_x(t) for t in range(1, ch.count + 1)]
    assert all(n % WIRING_GRID == 0 for n in numbers)  # kills: an off-grid size


def test_the_same_facts_give_the_same_frame():
    (facts,) = read_diagrams(station())
    assert _build(facts) == _build(facts)
