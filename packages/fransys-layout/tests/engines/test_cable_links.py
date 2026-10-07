"""Row links in the cable engine (CT5-LINK P2; CD5 and CD8 at L1, acceptance 23, 24, 26).

A link is a core with both ends in one row: two runs from its pins to a track beside that row and
a straight run between the corners, its text horizontal on the track. The model tests read the
records of `cable_models`; the hand-built tests use `block_facts(loops=...)`. Each test names its
probe.
"""

from dataclasses import replace
from itertools import pairwise

from cable_facts import TEXT_HEIGHT, block_facts
from cable_models import l1_picture, ring

from fransys_layout.engines.cable.place import place_block
from fransys_layout.engines.cable.read import read_blocks
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.geometry import WIRING_GRID, text_width
from fransys_layout.stages.channel import plan_channel, rise
from fransys_model.derive.cable_drawing import block_cables, cable_heading, core_text, row_links
from fransys_model.derive.cable_drawing import end_label as label_of
from fransys_model.layout import (
    BlockRow,
    BoxKind,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    EndStyle,
    layout_of,
)

G = WIRING_GRID
ROOM = G + TEXT_HEIGHT  # a link track's room: a grid unit and the text's height


def _laid(model, subject):
    """The block of `subject` as (head, its cable boxes, its end boxes, its wires)."""
    (head,) = (h for h in layout_of(model, CableBlock).values() if h.subject == subject)
    boxes = [b for b in layout_of(model, CableBox).values() if b.block == head.id]
    ends = [e for e in layout_of(model, EndBox).values() if e.block == head.id]
    wires = [w for w in layout_of(model, CoreWire).values() if w.block == head.id]
    return head, [b for b in boxes if b.kind is not BoxKind.HARNESS], ends, wires


def _texts(model, block):
    """(kind, x0, x1, y0, y1) per printed text of `block`; a link's is horizontal on its track.

    Copied from test_cable_engine.py: the test modules do not import each other.
    """
    profile, _, _ = profile_and_sheet(model)
    h, pad = profile.text_height, profile.marker_padding
    cables = {c.cable: c for c in block_cables(model, block.subject, block.unit)}
    cores = {c.conductor: c for cable in cables.values() for c in cable.cores}
    links = set(row_links(model, block.subject, block.unit))
    out = []
    for end in layout_of(model, EndBox).values():
        label = label_of(model, end.item, block.unit) if end.block == block.id else ""
        if label and end.style is not EndStyle.BLANK:
            w = text_width(label, height=h)
            y = end.y + end.height + pad if end.row is BlockRow.BOTTOM else end.y - pad - h
            x = end.x + (end.width - w) / 2
            out.append(("label", x, x + w, y, y + h))
    for box in layout_of(model, CableBox).values():
        if box.block == block.id and box.item in cables:
            w = text_width(cable_heading(model, cables[box.item], block.unit), height=h)
            out.append(("heading", box.x + pad, box.x + pad + w, box.y + pad, box.y + pad + h))
    for wire in layout_of(model, CoreWire).values():
        if wire.block == block.id:
            w = text_width(core_text(cores[wire.conductor]), height=h)
            if wire.conductor in links:
                x0, y0 = wire.text_x - w / 2, wire.text_y - h / 2
                out.append(("link", x0, x0 + w, y0, y0 + h))
            else:
                y0 = wire.text_y - w / 2
                out.append(("core", wire.text_x - h / 2, wire.text_x + h / 2, y0, y0 + w))
    return out


def _segments(wire):
    for run in (wire.run_a, wire.run_b):
        yield from pairwise(run)


def _enters(a, b, rect):
    """Whether segment a-b (axis-parallel) has a point strictly inside `rect` (x0, x1, y0, y1)."""
    x0, x1, y0, y1 = rect
    lo_x, hi_x = sorted((a.x, b.x))
    lo_y, hi_y = sorted((a.y, b.y))
    return lo_x < x1 and hi_x > x0 and lo_y < y1 and hi_y > y0


def _touches(a, b, rect):
    """Whether segment a-b has a point in `rect` or on its edge."""
    x0, x1, y0, y1 = rect
    return (
        min(a.x, b.x) <= x1 and max(a.x, b.x) >= x0 and min(a.y, b.y) <= y1 and max(a.y, b.y) >= y0
    )


def _closed(box):
    return box.x, box.x + box.width, box.y, box.y + box.height


def test_l1_picture_draws_its_looped_core_at_the_row_outside_the_box():
    """Acceptance 23: core 3 joins two pins of -H2; both runs stand on those cells at the row's
    edge, none of its points is in the box or on its edge, its text is outside the box, no text
    overlaps a wire, and the box holds the texts of the two crossing cores only.

    Probe: `place._cores` not excluding links (the looped core gets a box column).
    """
    s = l1_picture()
    head, (box,), ends, wires = _laid(s.model, s.cable)
    links = set(row_links(s.model, s.cable, None))
    (link,) = [w for w in wires if w.conductor in links]
    (facts,) = [f for f in read_blocks(s.frozen) if f.subject == s.cable]
    (core,) = [c for c in facts.cables[0].cores if c.link]
    cell_x = {pin.port: pin.x for end in ends for pin in end.pins}
    bottom = next(e for e in ends if e.row is BlockRow.BOTTOM)
    assert (link.run_a[0].x, link.run_b[0].x) == (cell_x[core.end_a], cell_x[core.end_b])
    assert link.run_a[0].y == link.run_b[0].y == bottom.y  # the bottom row's top edge
    assert (len(link.run_a), len(link.run_b)) == (3, 2)
    inside = _closed(box)
    assert not any(_touches(a, b, inside) for a, b in _segments(link))
    assert not (inside[0] <= link.text_x <= inside[1] and inside[2] <= link.text_y <= inside[3])
    texts = _texts(s.model, head)
    segments = [seg for wire in wires for seg in _segments(wire)]
    assert not any(_enters(a, b, t[1:]) for a, b in segments for t in texts)
    held = [
        t[0]
        for t in texts
        if t[0] in ("core", "link")
        if inside[0] < (t[1] + t[2]) / 2 < inside[1] and inside[2] < (t[3] + t[4]) / 2 < inside[3]
    ]
    assert held == ["core", "core"]
    assert [t[0] for t in texts].count("link") == 1


def test_the_ring_draws_its_highest_keyed_core_as_the_one_link_and_an_empty_box():
    """Acceptance 24, layout half: of WH7's three cores the highest-keyed (W3's) is the one link;
    W3's box is heading-only, no wire reaches it, and no text overlaps a wire.

    Probe: `end_rows` colouring the ring so the link is the lowest-keyed core.
    """
    s = ring()
    head, boxes, _, wires = _laid(s.model, s.harness)
    links = row_links(s.model, s.harness, None)
    (w3,) = [
        c
        for cable in block_cables(s.model, s.harness, None)
        if cable.cable == s.w3
        for c in cable.cores
    ]
    assert links == (w3.conductor,)
    (link,) = [w for w in wires if w.conductor in links]
    assert (len(link.run_a), len(link.run_b)) == (3, 2)
    assert len(wires) == 3
    (box3,) = [b for b in boxes if b.item == s.w3]
    segments = [seg for wire in wires for seg in _segments(wire)]
    assert not any(_touches(a, b, _closed(box3)) for a, b in segments)
    texts = _texts(s.model, head)
    assert not any(_enters(a, b, t[1:]) for a, b in segments for t in texts)
    assert [t[0] for t in texts].count("link") == 1


def _rect(wire, width, pad=0):
    """A wire's text rectangle (x0, x1, y0, y1), widened by `pad` sideways."""
    x, y = wire.text_x, wire.text_y
    return x - width // 2 - pad, x + width // 2 + pad, y - TEXT_HEIGHT // 2, y + TEXT_HEIGHT // 2


def _link_wires(block, facts):
    keys = {c.conductor for c in facts.cables[0].cores if c.link}
    return [w for w in block.wires if w.conductor in keys]


def _reorder(facts, order):
    """The first top end's pins in `order` (indices into its current pins)."""
    end = facts.top[0]
    return replace(
        facts, top=(replace(end, pins=tuple(end.pins[i] for i in order)), *facts.top[1:])
    )


def _all_segments(block):
    return [seg for wire in block.wires for seg in _segments(wire)]


def test_a_link_text_wider_than_its_span_avoids_a_wire_between_the_pins():
    """CD8 at L1: a crossing core's drop stands between a top link's pins and the text is wider
    than the span; the text is moved off the middle and meets no vertical wire, a pad apart.

    Probe: `place_links._left` returning `wanted`.
    """
    facts = _reorder(block_facts([(0, 0)], text=120, loops=[(True, 0)]), (1, 0, 2))
    block = place_block(facts)
    assert block is not None
    (link,) = _link_wires(block, facts)
    (core,) = [w for w in block.wires if w is not link]
    assert link.run_a[0].x < core.run_a[0].x < link.run_b[0].x  # the drop is between the pins
    assert link.text_x != (link.run_a[0].x + link.run_b[0].x) // 2  # not at its wanted middle
    rect = _rect(link, 120, pad=facts.pad)
    assert not any(_enters(a, b, rect) for a, b in _all_segments(block) if a.x == b.x)


def test_two_links_on_one_level_keep_their_texts_apart():
    """CD8 at L1: two disjoint top links share a track, their texts are wider than their spans,
    and the second text moves clear of the first and of every vertical wire.

    Probe: `place_links._wire` not adding its text to `blocked`.
    """
    facts = block_facts([(0, 0)], text=100, loops=[(True, 0), (True, 0)])
    block = place_block(facts)
    assert block is not None
    one, two = sorted(_link_wires(block, facts), key=lambda w: w.run_a[0].x)
    assert one.run_a[1].y == two.run_a[1].y  # one level
    first, second = _rect(one, 100), _rect(two, 100)
    assert first[1] + facts.pad < second[0]
    for wire in (one, two):
        rect = _rect(wire, 100, pad=facts.pad)
        assert not any(_enters(a, b, rect) for a, b in _all_segments(block) if a.x == b.x)


def _drop(block):
    return block.boxes[0].box.y, block.height


def test_a_top_link_moves_the_cable_box_down_one_room_a_level():
    """CD8 at L1: one link, or two disjoint ones, lowers the box and the block by one room; two
    overlapping links take two tracks a room apart and lower them by two.

    Probe: `place_links.lift` multiplying by the link count instead of the level count.
    """
    base = place_block(block_facts([(0, 0)]))
    plain = block_facts([(0, 0)], loops=[(True, 0)])
    disjoint = block_facts([(0, 0)], loops=[(True, 0), (True, 0)])
    overlap = _reorder(disjoint, (0, 1, 3, 2, 4))
    placed = {
        name: place_block(f) for name, f in (("one", plain), ("two", disjoint), ("over", overlap))
    }
    assert base is not None
    assert all(b is not None for b in placed.values())
    over = placed["over"]
    assert over is not None
    y, height = _drop(base)
    for name, levels in (("one", 1), ("two", 1), ("over", 2)):
        assert _drop(placed[name]) == (y + ROOM * levels, height + ROOM * levels), name
    end = next(e for e in over.ends if e.top)
    tracks = sorted({w.run_a[1].y for w in _link_wires(over, overlap)})
    assert tracks == [end.y + end.height + G, end.y + end.height + G + ROOM]
    assert {w.run_a[1].y for w in _link_wires(placed["two"], disjoint)} == {end.y + end.height + G}


def test_a_bottom_link_raises_the_lower_band_by_its_text_room():
    """CD8 at L1: a bottom-row link is a net of the lower band; the gap from the box to the row is
    `rise` for one link track plus a grid unit, and its text stands above its track.

    Probe: `place._place_at` passing `head` 0 to `rise`.
    """
    facts = block_facts([(0, 0)], loops=[(False, 0)])
    block = place_block(facts)
    base = place_block(block_facts([(0, 0)]))
    assert block is not None
    assert base is not None
    plan = plan_channel([(1, 24, 24), (2, 56, 88)], {2})
    assert plan is not None
    row = next(e for e in block.ends if not e.top)
    (box,) = (b.box for b in block.boxes)
    assert row.y - (box.y + box.height) == rise(plan, 1, TEXT_HEIGHT) + G
    gap = next(e for e in base.ends if not e.top).y - (
        base.boxes[0].box.y + base.boxes[0].box.height
    )
    assert row.y - (box.y + box.height) == gap + TEXT_HEIGHT  # the empty band already held a track
    (link,) = _link_wires(block, facts)
    track = link.run_a[1].y
    assert track == row.y - G
    assert _rect(link, 40)[3] <= track  # the text is above the track
    assert _rect(link, 40)[2] >= box.y + box.height  # and below the box


def test_a_link_text_wider_than_the_block_widens_it():
    """A 120-wide link text over two pins: the block's right edge holds the text.

    Probe: `place._right` ignoring the link texts (the text ends past the block's width).
    """
    facts = block_facts([(0, 0)] * 2, text=120, loops=[(True, 0)])
    placed = place_block(facts)
    assert placed is not None
    (link,) = (w for w in placed.wires if len(w.run_a) == 3)
    assert link.text_x + 120 // 2 <= placed.width


def test_a_link_text_does_not_grow_the_cable_box():
    """The box holds the crossing cores' texts only: a 120-wide link text leaves its height alone.

    Probe: `box_room` taking the longest text over link cores too (the box grows to 120).
    """
    plain = block_facts([(0, 0)], text=8, loops=[(True, 0)])
    (cable,) = plain.cables
    cores = tuple(replace(c, text_width=120) if c.link else c for c in cable.cores)
    wide = replace(plain, cables=(replace(cable, cores=cores),))
    base, linked = place_block(plain), place_block(wide)
    assert base is not None
    assert linked is not None
    assert linked.boxes[0].box.height == base.boxes[0].box.height
