"""The cable engine, whole: `lay_out_cables` over invented models built once (CT5-2 P1, CD5-CD11).

Each test names its spec acceptance item and the probe that must make it fail.
"""

from functools import cache
from itertools import pairwise
from types import SimpleNamespace
from typing import Any

import fransys_author
import fransys_parts

from fransys_layout import lay_out_cables, lay_out_schematic
from fransys_layout.engines.cable.place import block_pitch
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.geometry import WIRING_GRID, snap_up, text_width
from fransys_model.derive.cable_drawing import (
    block_cables,
    cable_heading,
    core_text,
    drawn_pins,
    end_label,
    end_rows,
    row_links,
)
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import freeze, merge
from fransys_model.layout import (
    DERIVED_KINDS,
    BlockRow,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    EndStyle,
    layout_of,
    profile_of,
)

G = WIRING_GRID
_PROJECT: dict[str, Any] = {
    "title": "Cable engine",
    "number": "P-1010",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_CABLE, _MOTOR, _TB = "DEMO-CBL-4G1.5", "DEMO-MOTOR-4KW", "DEMO-TB-2.5"


def _design():
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return parts, d


@cache
def _flat() -> SimpleNamespace:
    """Strip -X1 (6 terminals) and -X2 (3), motors -M1 and -M2, and three cables.

    W1: X1:1..4 to M1 U, V, W, PE. W2: X1:5 to X1:6 (one item at both ends, CD-H5).
    W3: cores land on X2:3, X2:1, X2:2 (out of pin order), far end M2 U, V, W in order.
    """
    parts, d = _design()
    er, fld = d.location("ER", "Engine room"), d.location("FLD", "Field")
    g, gf = d.group("ER", "Cabinet"), d.group("FLD", "Field")
    x1, x2 = d.strip("X1", at=er), d.strip("X2", at=er)
    t1 = [x1.terminal(_TB, group=g) for _ in range(6)]
    t2 = [x2.terminal(_TB, group=g) for _ in range(3)]
    m1 = d.item(_MOTOR, tag="M1", at=fld, group=gf)
    m2 = d.item(_MOTOR, tag="M2", at=fld, group=gf)
    w1 = d.cable(_CABLE, tag="W1", at=er, group=g)
    for n, port in enumerate(("U", "V", "W", "PE"), start=1):
        w1.core(n, t1[n - 1].outer, m1[port])
    w2 = d.cable(_CABLE, tag="W2", at=er, group=g)
    w2.core(1, t1[4].outer, t1[5].outer)
    w3 = d.cable(_CABLE, tag="W3", at=er, group=g)
    for n, (near, far) in enumerate(((2, "U"), (0, "V"), (1, "W")), start=1):
        w3.core(n, t2[near].outer, m2[far])
    frozen, _ = number_pass(freeze(merge(parts, d.draft())))
    model, findings = lay_out_cables(frozen)
    ids = SimpleNamespace(w1=w1.id, w2=w2.id, w3=w3.id, m1=m1.id, m2=m2.id)
    return SimpleNamespace(frozen=frozen, model=model, findings=findings, ids=ids)


@cache
def _unit() -> SimpleNamespace:
    """A unit with strip -X5 and its own cable from -X5:1 to an external top-level motor."""
    parts, d = _design()
    fld, gf = d.location("FLD", "Field"), d.group("FLD", "Field")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, grp = cab.location("C1", "Cabinet"), cab.group("G1", "Group")
    terminal = cab.strip("X5", at=c1).terminal(_TB, group=grp)
    motor = d.item(_MOTOR, tag="M9", at=fld, group=gf, external=True)
    cable = cab.cable(_CABLE, name="w", at=c1)
    cable.core(1, terminal.outer, motor["U"])
    frozen, _ = number_pass(freeze(merge(parts, d.draft())))
    model, _ = lay_out_cables(frozen)
    return SimpleNamespace(model=model, cable=cable.id, motor=motor.id)


@cache
def _nested() -> SimpleNamespace:
    """Unit `outer` holds plug -P9 and unit `inner`; `inner`'s cable `w` runs -X5:2 to -P9:2.

    Copied minimal from test_cable_engine_units.py: the test directories are off `sys.path`.
    """
    parts, d = _design()
    outer = d.scope("pump1", at=d.location("ER", "Engine room")).unit(
        "outer", revision=1, interface="1"
    )
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    cab = outer.location("C1", "Cabinet")
    p9 = outer.item("DEMO-CONN-2P", tag="P9", at=cab, group=outer.group("OUT", "Outer"))
    inner = outer.scope("io", at=cab).unit("inner", revision=1, interface="1")
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    strip = inner.strip("X5", at=cab)
    terminals = [strip.terminal(_TB, group=inner.group("IN", "Inner")) for _ in range(2)]
    cable = inner.cable(_CABLE, name="w", at=cab)
    cable.core(1, terminals[1].inner, p9["2"])
    frozen, _ = number_pass(freeze(merge(parts, d.draft())))
    model, _ = lay_out_cables(frozen)
    return SimpleNamespace(model=model)


@cache
def _long_label() -> SimpleNamespace:
    """One core from strip -X1 to a motor whose end label, `+NORTHFARFIELDPUMPHOUSE-M1`, is far
    wider than its one-pin end box and than the cable box (test gap 1, acceptance 15)."""
    parts, d = _design()
    er, far = d.location("ER", "Engine room"), d.location("NORTHFARFIELDPUMPHOUSE", "Far field")
    g = d.group("ER", "Cabinet")
    terminal = d.strip("X1", at=er).terminal(_TB, group=g)
    motor = d.item(_MOTOR, tag="M1", at=far, group=g)
    cable = d.cable(_CABLE, tag="W1", at=er, group=g)
    cable.core(1, terminal.outer, motor["U"])
    frozen, _ = number_pass(freeze(merge(parts, d.draft())))
    model, _ = lay_out_cables(frozen)
    return SimpleNamespace(model=model, cable=cable.id, motor=motor.id)


def _block(model, cable, unit=None):
    """The block of `cable` in `unit`'s reading as (head, box, ends by item, wires)."""
    heads = [
        h for h in layout_of(model, CableBlock).values() if (h.subject, h.unit) == (cable, unit)
    ]
    if not heads:
        return None
    (head,) = heads
    ends = {e.item: e for e in layout_of(model, EndBox).values() if e.block == head.id}
    wires = [w for w in layout_of(model, CoreWire).values() if w.block == head.id]
    (box,) = (b for b in layout_of(model, CableBox).values() if b.block == head.id)
    return head, box, ends, wires


def _all_cable_records(model):
    for kind in (CableBlock, CableBox, EndBox, CoreWire):
        yield from layout_of(model, kind).values()


def test_drawable_block_written():
    """CD2/CD5: a two-end 4-core cable gets its whole block; the skip is only for the undrawable.

    Probe: the `drawable` skip widened to this block.
    """
    s = _flat()
    head, box, ends, wires = _block(s.model, s.ids.w1)
    assert box.block == head.id
    assert sorted(e.row.name for e in ends.values()) == ["BOTTOM", "TOP"]
    assert len(wires) == 4
    # W1, W2 (a cable of one row link, CD-H8 at V1) and W3 are drawn
    assert (len(layout_of(s.model, CableBlock)), len(layout_of(s.model, CableBox))) == (3, 3)
    assert s.findings == ()


def _cell_x(end, port):
    (cell,) = (c for c in end.pins if c.port == port)
    return cell.x


def test_wire_x_equals_its_cell_x():
    """CD5/CD6: each core's wire ends at the centre x of the pin cells it lands on, both ends.

    Probe: a pin cell's x moved by one grid unit.
    """
    s = _flat()
    _, _, ends, wires = _block(s.model, s.ids.w1)
    top = next(e for e in ends.values() if e.row is BlockRow.TOP)
    bottom = next(e for e in ends.values() if e.row is BlockRow.BOTTOM)
    cores = {c.conductor: c for c in block_cables(s.frozen, s.ids.w1, None)[0].cores}
    assert wires
    for wire in wires:
        core = cores[wire.conductor]
        ports = {core.end_a, core.end_b}
        (tp,) = ports & {c.port for c in top.pins}
        (bp,) = ports & {c.port for c in bottom.pins}
        assert wire.run_a[0].x == _cell_x(top, tp)
        assert wire.run_b[-1].x == _cell_x(bottom, bp)
        assert wire.text_x == _cell_x(top, tp)  # the core text is centred on its axis


def test_out_of_order_cores_draw_straight():
    """CD5/CD6, acceptance 2: cores landing out of pin order are still one vertical segment each.

    Probe: the end's pins laid out in pin order instead of core order.
    """
    s = _flat()
    _, _, ends, wires = _block(s.model, s.ids.w3)
    assert len(wires) == 3
    assert len(next(iter(ends.values())).pins) == 3
    for wire in wires:
        assert (len(wire.run_a), len(wire.run_b)) == (2, 2)
        assert len({p.x for p in (*wire.run_a, *wire.run_b)}) == 1


def _coordinates(model):
    for rec in _all_cable_records(model):
        if isinstance(rec, CableBlock):
            yield from (rec.width, rec.height, rec.pitch)
        elif isinstance(rec, (CableBox, EndBox)):
            yield from (rec.x, rec.y, rec.width, rec.height)
            yield from (pin.x for pin in getattr(rec, "pins", ()))
        else:
            for point in (*rec.run_a, *rec.run_b):
                yield from (point.x, point.y)
            yield from (rec.text_x, rec.text_y)


def test_every_coordinate_on_the_grid():
    """CD8, acceptance 5: every coordinate of every cable record is a multiple of 8.

    The nested model adds a blank end (STUB and height 0). Probe: a half-grid offset in the placer.
    """
    for model in (_flat().model, _unit().model, _nested().model):
        values = list(_coordinates(model))
        assert len(values) > 20
        assert [v for v in values if v % G] == []


def test_engine_measures_derives_text():
    """CD7, acceptance 6: box width and pitch come from `core_text` and `cable_heading` widths.

    The cores' texts are spelled out here, so a change to `core_text` breaks the match.
    Probe: a trailing space appended in `core_text`.
    """
    s = _flat()
    _, box, ends, _ = _block(s.model, s.ids.w1)
    cable = block_cables(s.frozen, s.ids.w1, None)[0]
    profile, _, _ = profile_and_sheet(s.frozen)
    h = profile.text_height
    texts = ["1 BN", "2 BK", "3 GY", "4 GNYE"]
    assert [core_text(c) for c in cable.cores] == texts
    widths = [text_width(t, height=h) for t in texts]
    heading = text_width(cable_heading(s.frozen, cable, None), height=h)
    pad = profile.marker_padding
    assert box.height >= max(widths) + 2 * pad  # the box holds its longest core text (N1)
    assert box.width == snap_up(max(heading + 2 * pad, *(e.width for e in ends.values())))
    assert box.width == max(e.width for e in ends.values())  # W1's columns are its cells
    top, bottom = end_rows(s.frozen, s.ids.w1, None)
    pins = [
        text_width(pin.marking, height=h)
        for item in (*top, *bottom)
        for pin in drawn_pins(s.frozen, s.ids.w1, item, None)
    ]
    assert _block(s.model, s.ids.w1)[0].pitch == block_pitch(max(pins))


def _style_of(model, cable, item, unit=None):
    return _block(model, cable, unit)[2][item].style


def test_by_others_end_dashed_only_in_the_absolute_reading():
    """CD10, acceptance 8: an external end is DASHED in the absolute reading, SOLID in the unit's.

    Probe: the by-others mark applied in every reading.
    """
    s = _unit()
    (unit,) = {h.unit for h in layout_of(s.model, CableBlock).values() if h.unit is not None}
    assert _style_of(s.model, s.cable, s.motor) is EndStyle.DASHED
    assert _style_of(s.model, s.cable, s.motor, unit) is EndStyle.SOLID


def test_a_cable_of_row_links_alone_draws_its_row_and_a_heading_only_box():
    """CD-H8 at V1, acceptance 26: W2 joins two pins of one strip; the block holds that row, one
    link on the box side, and the heading-only box under it. No run touches the box.

    Probe: route the link's core through the box.
    """
    s = _flat()
    _, box, ends, wires = _block(s.model, s.ids.w2)
    (end,) = ends.values()
    (wire,) = wires
    assert end.row is BlockRow.TOP
    assert box.y > max(p.y for p in (*wire.run_a, *wire.run_b))
    assert box.item == s.ids.w2
    assert wire.run_a[0].y == wire.run_b[0].y == end.y + end.height  # both pins, the row's edge
    assert wire.run_a[-1].y == wire.run_b[-1].y  # the straight run is level
    assert (wire.run_a[-1].x, wire.run_a[-1].y) == (wire.run_b[-1].x, wire.run_b[-1].y)
    assert (len(wire.run_a), len(wire.run_b)) == (
        3,
        2,
    )  # the encoding: the straight run is run_a's last piece
    assert s.findings == ()


def _texts(model, block):
    """(kind, x0, x1, y0, y1, record) per printed text of `block`, from the render contract."""
    profile, _, _ = profile_and_sheet(model)
    h, pad = profile.text_height, profile.marker_padding
    cables = {c.cable: c for c in block_cables(model, block.subject, block.unit)}
    cores = {c.conductor: c for cable in cables.values() for c in cable.cores}
    out = []
    for end in layout_of(model, EndBox).values():
        label = end_label(model, end.item, block.unit) if end.block == block.id else ""
        if label and end.style is not EndStyle.BLANK:
            w = text_width(label, height=h)
            y = end.y + end.height + pad if end.row is BlockRow.BOTTOM else end.y - pad - h
            x = end.x + (end.width - w) / 2
            out.append(("label", x, x + w, y, y + h, end))
    for box in layout_of(model, CableBox).values():
        if box.block == block.id and box.item in cables:
            w = text_width(cable_heading(model, cables[box.item], block.unit), height=h)
            out.append(("heading", box.x + pad, box.x + pad + w, box.y + pad, box.y + pad + h, box))
    links = set(row_links(model, block.subject, block.unit))
    for wire in layout_of(model, CoreWire).values():
        if wire.block == block.id:
            w = text_width(core_text(cores[wire.conductor]), height=h)
            if wire.conductor in links:  # L1: along the straight run, h high at its middle
                x0, y0 = wire.text_x - w / 2, wire.text_y - h / 2
                out.append(("link", x0, x0 + w, y0, y0 + h, None))
                continue
            y0 = wire.text_y - w / 2  # turned: it reads upward, h wide on its axis (N1)
            out.append(("core", wire.text_x - h / 2, wire.text_x + h / 2, y0, y0 + w, None))
    return out


def test_every_text_stays_inside_its_block():
    """CD7/CD8: every printed text lies inside its block; labels clear their end box, heading
    and core texts stay inside the cable box horizontally.

    Positive: texts of every kind are checked. Probe: `_origin` in place.py returning 0.
    """
    kinds = set()
    for model in (_flat().model, _unit().model, _nested().model, _long_label().model):
        for block in layout_of(model, CableBlock).values():
            (box,) = (b for b in layout_of(model, CableBox).values() if b.block == block.id)
            for kind, x0, x1, y0, y1, rec in _texts(model, block):
                kinds.add(kind)
                where = (kind, block.subject, x0, x1, y0, y1, block.width, block.height)
                assert x0 >= 0, where
                assert x1 <= block.width, where
                assert y0 >= 0, where
                assert y1 <= block.height, where
                if kind == "label":
                    assert (y1 <= rec.y) or (y0 >= rec.y + rec.height), where
                elif kind != "link":  # a link's text stands at its row, outside the box (L1)
                    assert x0 >= box.x, where
                    assert x1 <= box.x + box.width, where
                if kind == "core":  # N1: under the heading, inside the box
                    h, pad = (profile_of(model).text_height, profile_of(model).marker_padding)
                    assert y0 >= box.y + 2 * pad + h, where
                    assert y1 <= box.y + box.height, where
    assert kinds == {"label", "heading", "core", "link"}


def _records(model):
    return {
        kind: frozenset(layout_of(model, kind).values())
        for kind in (*DERIVED_KINDS, CableBlock, CableBox, EndBox, CoreWire)
    }


def test_cable_and_schematic_passes_commute():
    """CD2, Q3, acceptance 13: S,C,S,C and C,S,C,S give equal records; each pass keeps the other's.

    Probe: one kind tuple shared by both passes.
    """
    frozen = _flat().frozen
    sc, cs = frozen, frozen
    for _ in range(2):
        sc = lay_out_cables(lay_out_schematic(sc)[0])[0]
        cs = lay_out_schematic(lay_out_cables(cs)[0])[0]
    assert _records(sc) == _records(cs)
    assert sc.digests == cs.digests
    assert layout_of(sc, CableBlock)
    assert any(layout_of(sc, kind) for kind in DERIVED_KINDS)


def test_a_long_right_hand_label_sets_the_block_width():
    """Test gap 1, acceptance 15: the block reaches the right end of a label wider than its box,
    so pdf's size check sees the true width. Probe: `_right` without its label term."""
    s = _long_label()
    head, box, ends, _ = _block(s.model, s.cable)
    end = ends[s.motor]
    profile, _, _ = profile_and_sheet(s.model)
    w = text_width(end_label(s.model, s.motor, None), height=profile.text_height)
    right = end.x + (end.width + w) / 2
    assert right > max(box.x + box.width, *(e.x + e.width for e in ends.values()))
    assert head.width == snap_up(-(-int(2 * right) // 2))


def _segments(wire):
    for run in (wire.run_a, wire.run_b):
        yield from pairwise(run)


def _enters(a, b, rect):
    """Whether segment a-b (axis-parallel) has a point strictly inside `rect` (x0, x1, y0, y1)."""
    x0, x1, y0, y1 = rect
    lo_x, hi_x = sorted((a.x, b.x))
    lo_y, hi_y = sorted((a.y, b.y))
    return lo_x < x1 and hi_x > x0 and lo_y < y1 and hi_y > y0


def test_no_run_enters_the_cable_box_and_no_text_crosses_a_wire():
    """CD8 closed box, acceptance 18: every run stops at the cable box's edge; no text crosses
    a run. Positive: runs touch the box edges. Probe: one straight run through the box."""
    touching = 0
    for model in (_flat().model, _unit().model, _nested().model, _long_label().model):
        for block in layout_of(model, CableBlock).values():
            (box,) = (b for b in layout_of(model, CableBox).values() if b.block == block.id)
            inside = (box.x, box.x + box.width, box.y, box.y + box.height)
            wires = [w for w in layout_of(model, CoreWire).values() if w.block == block.id]
            segments = [seg for wire in wires for seg in _segments(wire)]
            texts = [(x0, x1, y0, y1) for _, x0, x1, y0, y1, _ in _texts(model, block)]
            for a, b in segments:
                assert not _enters(a, b, inside), (block.subject, a, b)
                assert not any(_enters(a, b, t) for t in texts), (block.subject, a, b)
                touching += {a.y, b.y} & {box.y, box.y + box.height} != set()
    assert touching > 10
