"""F5-C: undo tests for D3 (stacking), D13/D14 (measured, anchored text) and D16 (house profile).

Everything is read from laid-out `layout.*` records; nothing here reads `ext`.
Fixtures are invented: the layout package's cabinet and a small relay/lamp design on the
`demo_parts` set.
"""

from collections import defaultdict
from functools import cache
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document
from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.geometry import WIRING_GRID, Orientation, symbol_geometry, text_width
from fransys_layout.stages.place import _reference_band
from fransys_model.derive.drawing_text import label_text
from fransys_model.kernel import freeze
from fransys_model.layout import (
    Label,
    LinkMarker,
    Page,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_AC_RAILS = {"L1": ("230", 0), "L2": ("230", 120), "L3": ("230", 240), "N": ("0", None)}
_DC_RAILS = {"24V": ("24", None), "+": ("24", None), "0V": ("0", None)}
_ROW_SPACING = 88  # D3, D16: the house value, 11 M
_PROJECT: dict[str, Any] = {
    "title": "F5-C",
    "number": "P-5",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


@cache
def _cabinet() -> Model:
    """The layout package's cabinet, laid out with the house profile (no authored profile)."""
    return lay_out_schematic(freeze(build_cabinet()))[0]


def _design(*, second_tag: str = "K2", relays: bool = True, lamp_rails: tuple[str, str] = ("", "")):
    """Two 2CO relays, each with its own feed terminal, or a lamp between two `lamp_rails` ones."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1, group = d.location("C1", "Cabinet"), d.group("CTL", "Control")
    strip = d.strip("X1", at=c1)
    wire = d.wiring(colour="BU", gauge="0.5")
    if not relays:
        a, b = (strip.terminal("DEMO-TB-2.5", group=group) for _ in range(2))
        lamp = d.item("DEMO-LAMP-24", tag="H1", at=c1, group=group)
        wire(a.inner, lamp["1"])
        wire(lamp["2"], b.inner)
        d.supply("AC", current="ac", rails=_AC_RAILS)
        d.supply("DC", current="dc", rails=_DC_RAILS)
        for name, end, rail in (("TOPN", a, lamp_rails[0]), ("BOTN", b, lamp_rails[1])):
            d.net(name, end.inner, cls="pe" if rail == "PE" else "power", potential=rail)
        return fr.build(parts, d.draft(), layout_trigger_document()).model
    feed1, feed2, zero1, zero2, out1, out2 = (
        strip.terminal("DEMO-TB-2.5", group=group) for _ in range(6)
    )
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=group)
    k2 = d.item("DEMO-RLY-2CO-24", tag=second_tag, at=c1, group=group)
    # each relay has its own feed terminal: two contacts between the same two nets would be
    # strapped in parallel (D1, layout-0060), K2's a side element of K1's
    for relay, feed, zero in ((k1, feed1, zero1), (k2, feed2, zero2)):
        wire(feed.inner, relay.fn("coil")["A1"])
        wire(relay.fn("coil")["A2"], zero.inner)
        wire(feed.inner, relay.fn("co_1")["11"])
        wire(relay.fn("co_1")["14"], out1.inner)
        wire(feed.inner, relay.fn("co_2")["21"])  # layout-0112: an unwired contact is not drawn
    wire(k1.fn("co_1")["12"], out2.inner)
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _geometry(placement: SymbolPlacement):
    """The library geometry of the symbol `placement` draws, in its orientation."""
    return symbol_geometry(
        placement.symbol,
        poles=placement.poles,
        orientation=Orientation(placement.orientation.value),
    )


def _by_key(model: Model) -> dict:
    """The placements of `model` by (item key, function name)."""
    return {
        (items(model)[functions(model)[p.function].item].key, functions(model)[p.function].name): p
        for p in layout_of(model, SymbolPlacement).values()
    }


def _keepouts(model: Model) -> dict:
    """Page id -> [(placement, top, bottom)]: a symbol's keep-out grown over its own text boxes."""
    labels = layout_of(model, Label).values()
    found = defaultdict(list)
    for s in layout_of(model, SymbolPlacement).values():
        if s.symbol == "generic-box":  # a box has no library geometry to read
            continue
        k = _geometry(s).keepout
        top, bottom = s.y + k.y, s.y + k.y + k.height
        for label in labels:
            owner = label.function
            if label.port is not None:
                owner = ports(model)[label.port].function
            if label.page == s.page and owner == s.function and label.slot != "contacts":
                top, bottom = min(top, label.y), max(bottom, label.y + DEFAULT_PROFILE.text_height)
        found[s.page].append((s, top, bottom))
    return found


def _columns(model: Model) -> list[list[tuple]]:
    """Every column of every page (symbols sharing an origin x), top to bottom."""
    columns = []
    for page_cells in _keepouts(model).values():
        by_x = defaultdict(list)
        for cell in page_cells:
            by_x[cell[0].x].append(cell)
        columns.extend(sorted(cells, key=lambda c: c[1]) for cells in by_x.values())
    return columns


# ---- D3: stacking through the engine -------------------------------------------------------


def test_cells_of_a_column_stand_one_row_spacing_below_the_keep_out_before() -> None:
    """D3: each cell sits `row_spacing` (88 G, to the grid) below the keep-out before it."""
    # UNDO: fransys_model/layout/formats.py `Profile.row_spacing: int = 32` (or
    # stages/place.py `_space` gap: 0).
    model = _cabinet()
    attached = {f.id for f in functions(model).values() if f.key[-1] == "terminal"}  # V4, R7 B8
    gaps = [
        b[1] - a[2]
        for cells in _columns(model)
        for a, b in pairwise(cells)
        if attached.isdisjoint((a[0].function, b[0].function))
    ]
    assert (
        len(gaps) >= 6
    )  # the cabinet's stacked columns (8 with the attached terminal's two pairs)
    assert all(_ROW_SPACING <= gap < _ROW_SPACING + WIRING_GRID for gap in gaps), gaps


def test_no_cell_is_pushed_to_the_page_foot_and_a_page_is_as_tall_as_its_tallest_column() -> None:
    """D3: columns stack from the top; the page ends where its tallest column ends."""
    # UNDO: stages/place.py `_space`: after the loop push each column's last block to the
    # content-box foot (`floor = sheet.content_height - block height`), the old fill.
    model = _cabinet()
    for page_id, page_cells in _keepouts(model).items():
        by_x = defaultdict(list)
        for cell in page_cells:
            by_x[cell[0].x].append(cell)
        feet = sorted(max(c[2] for c in cells) for cells in by_x.values())
        assert feet[-1] < 660, feet  # well above the foot of an 822 G content box
        assert feet[0] < feet[-1] or len(feet) == 1, (page_id, feet)
    page_one = min(layout_of(model, Page).values(), key=lambda p: p.number)
    tall = [c for c in _columns(model) if c[0][0].page == page_one.id and len(c) == 4]
    short = [c for c in _columns(model) if c[0][0].page == page_one.id and len(c) == 3]
    assert tall
    assert short
    assert max(c[-1][2] for c in short) < min(c[-1][2] for c in tall)


def test_a_column_of_only_boxes_and_terminals_stays_compact() -> None:
    """D3: a generic box over its terminal keeps the row gap, not the 88 G spacing."""
    # UNDO: stages/place.py: delete the `if all(cell.boxy ...): continue` skip in `_space` AND
    # break the `_blocks` glue (the terminal is an R7.1 attachment row; the two guards mask
    # each other, so either alone does not fail this test).
    model = _cabinet()
    placements = _by_key(model)
    box = placements[("cabinet", "h1"), "lamp"]
    below = [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.page == box.page and p.x == box.x and p.y > box.y
    ]
    assert box.symbol == "generic-box"
    assert [p.symbol for p in below] == ["terminal"]
    assert 0 < below[0].y - box.y < _ROW_SPACING


# ---- D16: the house profile ---------------------------------------------------------------


def test_the_house_row_spacing_is_88() -> None:
    """D16: `row_spacing` is 88 G (11 M) in the engine's house profile."""
    # UNDO: fransys_model/layout/formats.py: `Profile.row_spacing: int = 87`.
    assert DEFAULT_PROFILE.row_spacing == _ROW_SPACING


def _switch_chain(row_spacing: int | None = None, switch_count: int = 5):
    """Terminal, `switch_count` switches in series, terminal: the blocks of one column.

    With `row_spacing` the design authors a `layout.profile` of that spacing, else none.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    if row_spacing is not None:
        d.profile(row_spacing=row_spacing)
    c1, group = d.location("C1", "Cabinet"), d.group("CTL", "Control")
    strip = d.strip("X1", at=c1)
    top, bottom = (strip.terminal("DEMO-TB-2.5", group=group) for _ in range(2))
    switches = [
        d.item("DEMO-SWITCH-2P", tag=f"S{n}", at=c1, group=group).fn("sw")
        for n in range(1, switch_count + 1)
    ]
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(top.outer, switches[0]["A"])
    for above, below in pairwise(switches):
        wire(above["B"], below["A"])
    wire(switches[-1]["B"], bottom.inner)
    return fr.build(parts, d.draft(), layout_trigger_document())


def test_a_seven_block_column_ends_inside_the_page_at_the_house_row_spacing() -> None:
    """M11, D3, D16: a column too tall for the house spacing narrows evenly, ends inside the page.

    The column is a terminal, five make-contact switches and a terminal: six gaps, which at 88 G
    would end below the floor (the content box less the bottom band, M4). The column narrows
    its gaps evenly, to one value but for a grid of rounding, and not below `row_gap`, and ends
    above the bottom band with no `PAGE_OVERFULL`. The same design with an authored
    `layout.profile` of `row_spacing` 104 narrows to the same gaps: the fit sets them, not the
    spacing asked for.
    """
    # UNDO: stages/place.py `_stacked`: `return page, top, floor, gaps_of` after the first pass
    # (no M11 narrowing): the house run reports PAGE_OVERFULL.
    house = _switch_chain()
    (house_column,) = _columns(house.model)
    wide = _switch_chain(row_spacing=104)
    (wide_column,) = _columns(wide.model)

    def overfull(result) -> list:
        return [finding for finding in result.findings if finding.code == "PAGE_OVERFULL"]

    def gaps(column: list) -> list[int]:
        return [b[1] - a[2] for a, b in pairwise(column)]

    inputs = read_inputs(house.model)
    for result, column in ((house, house_column), (wide, wide_column)):
        assert overfull(result) == []
        assert len(column) == 7
        assert len({cell[0].page for cell in column}) == 1
        assert column[-1][2] <= inputs.sheet.content_height - _reference_band(
            inputs.sheet, inputs.profile
        )
    house_gaps = gaps(house_column)
    assert all(DEFAULT_PROFILE.row_gap <= gap < _ROW_SPACING for gap in house_gaps), house_gaps
    assert max(house_gaps) - min(house_gaps) <= WIRING_GRID, house_gaps
    assert gaps(wide_column) == house_gaps


def test_an_authored_row_spacing_moves_the_blocks_of_a_column() -> None:
    """model-0060: `Profile.row_spacing` is read from the model, so 96 G stacks each gap 8 G wider.

    The same five-block column (a column that fits at both spacings, so M11 narrows neither)
    is laid out twice, the house profile and one authored at 96 G: the keep-outs are identical,
    so every gap grows by exactly the 8 G the spacing grew by.
    """
    # UNDO: engines/schematic/read/house.py `to_stage_profile`: `row_spacing=88`.
    (house_column,) = _columns(_switch_chain(switch_count=3).model)
    (wide_column,) = _columns(_switch_chain(row_spacing=96, switch_count=3).model)

    def gaps(column: list) -> list[int]:
        return [b[1] - a[2] for a, b in pairwise(column)]

    assert len(house_column) == len(wide_column) == 5
    assert [w - h for w, h in zip(gaps(wide_column), gaps(house_column), strict=True)] == [8] * 4


_ORDER = ("L1", "L2", "L3", "24V", "N", "0V", "PE")
# no ("24V", "N") pair: a DC bar against an AC reference is stacked by V3, not by rank
_PAIRS = [pair for pair in pairwise(_ORDER) if pair != ("24V", "N")]


@pytest.mark.parametrize("swapped", [False, True])
@pytest.mark.parametrize(("higher", "lower"), _PAIRS)
def test_the_engine_puts_the_higher_potential_first(
    higher: str,
    lower: str,
    swapped: bool,  # noqa: FBT001 -- a parametrized flag, one case per value
) -> None:
    """D16: a load fed by two potentials draws the lower-rank one leftmost, whichever terminal."""
    # UNDO: derive/potential.py `_order_key`: return `(0, 0)` for every rail (all tie).
    rails = (lower, higher) if swapped else (higher, lower)
    placed = _by_key(_design(relays=False, lamp_rails=rails))
    at = {
        rails[0]: (
            placed[("X1", "terminal", "1"), "terminal"].x,
            placed[("X1", "terminal", "1"), "terminal"].y,
        ),
        rails[1]: (
            placed[("X1", "terminal", "2"), "terminal"].x,
            placed[("X1", "terminal", "2"), "terminal"].y,
        ),
    }
    assert at[higher] < at[lower]  # leftmost, or on top when a power symbol stacks the column


# ---- D13, D14: measured text kept at a fixed near edge ---------------------------------------


def _tag_of(model: Model, placement: SymbolPlacement) -> Label:
    """The TAG label of the function `placement` draws."""
    (label,) = (
        one
        for one in layout_of(model, Label).values()
        if one.function == placement.function and one.slot == "tag" and one.kind.value == "tag"
    )
    return label


def test_a_longer_tag_keeps_its_near_edge_and_pushes_the_column_by_the_width_difference() -> None:
    """D13, D14: the W tag's right edge stays 20 G off the coil; the pitch grows by the text."""
    # UNDO: stages/place.py `_cells`: keep the fixed tag slot in the keep-out (skip `grow_keepout`
    # and `_without_tag`) or stages/labels.py: centre a W text on its slot.
    short, long = _design(second_tag="K2"), _design(second_tag="K2LONGTAG")
    edges, pitches, widths = [], [], []
    for model, tag in ((short, "K2"), (long, "K2LONGTAG")):
        placed = _by_key(model)
        first, second = placed[("K1",), "coil"], placed[(tag,), "coil"]
        label = _tag_of(model, second)
        width = text_width(label_text(model, label), height=DEFAULT_PROFILE.text_height)
        edges.append(second.x - (label.x + width))
        pitches.append(second.x - first.x)
        widths.append(width)
    assert edges[0] == edges[1] > 0
    grown = widths[1] - widths[0]
    assert grown > 0
    assert grown <= pitches[1] - pitches[0] < grown + WIRING_GRID


@cache
def _relays() -> Model:
    return _design()


def _marker_offsets(model: Model) -> dict:
    """(side, facing) -> [(width, height, dx, dy)]: each marker's box corner against its port."""
    sym = {
        "A1": "in",
        "A2": "out",
        "11": "com",
        "21": "com",
        "12": "nc",
        "14": "no",
        "internal": "n",
    }
    placed = {p.function: p for p in layout_of(model, SymbolPlacement).values()}
    found = defaultdict(list)
    for marker in layout_of(model, LinkMarker).values():
        port = ports(model)[marker.port]
        s = placed[port.function]
        geometry = _geometry(s)
        at = next(p for p in geometry.ports if p.name == sym.get(port.name, "s"))
        found[marker.side, at.facing].append(
            (
                marker.width,
                marker.height,
                marker.x - (s.x + at.at.x),
                marker.y - (s.y + at.at.y),
            )
        )
    return found


def test_a_marker_box_keeps_its_near_edge_at_a_fixed_offset_whatever_its_thickness() -> None:
    """D14: markers of one side and facing sit at one offset from their port at any thickness.

    LD3 (c), decision layout-0089: a reference's box length is fixed per sheet format. On an N
    or S pin the box is vertical (M1) and its lines stand side by side (M3), so the dimension
    that still varies, with a reference's own line count (LD3 (d)), is the box's width, its
    thickness. The invariant -- the near edge sits at one fixed offset from the port, whatever
    the box's own size -- is checked on that width.
    """
    # UNDO: engines/schematic/write/markers.py `link_markers`, star record:
    # `x=one.box.x` (was `one.at.x`). The stored x/y is the port position,
    # so a centred box in stages/references/marker_boxes.py `marker_box` is
    # not seen by this test.
    groups = _marker_offsets(_relays())
    varied = [g for g in groups.values() if len({width for width, _, _, _ in g}) > 1]
    assert varied, "no marker group has two widths: the fixture stopped exercising D14"
    for group in groups.values():
        assert len({(dx, dy) for _, _, dx, dy in group}) == 1, group
