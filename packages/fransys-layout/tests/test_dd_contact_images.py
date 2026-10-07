"""F5-C: undo tests for D7 (contact images) and D14 (their anchoring).

A coil's contact image is a `CROSS_REFERENCE` label with slot "contacts"; its text is read with
`label_text`, its box is rebuilt from that text with the same measurement the engine uses.
Fixtures: the layout package's cabinet (K1 contactor, K2, K8) and two 2CO relays on `demo_parts`.
"""

from functools import cache
from typing import TYPE_CHECKING

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document
from layout_cabinet import build_cabinet

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE, DEFAULT_SHEET
from fransys_layout.geometry import WIRING_GRID, Orientation, symbol_geometry, text_width
from fransys_model.derive.designation import own_designation_or_none
from fransys_model.derive.drawing_text import frame_column, frame_row, label_text, position_text
from fransys_model.kernel import freeze
from fransys_model.layout import (
    Label,
    LabelKind,
    LinkMarker,
    Page,
    Route,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_TEXT, _PAD = DEFAULT_PROFILE.text_height, DEFAULT_PROFILE.marker_padding


@cache
def _cabinet() -> Model:
    """The cabinet, laid out with the house profile."""
    return lay_out_schematic(freeze(build_cabinet()))[0]


@cache
def _relays() -> Model:
    """K1, K2: 2CO relays fed from one terminal; K1 uses both throws of its first contact.

    K2's coil returns through a breaker Q1, so its column stands lower than K1's.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(
        title="F5-C",
        number="P-5",
        customer="Example Co",
        revision=1,
        author="OJB",
    )
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1, group = d.location("C1", "Cabinet"), d.group("CTL", "Control")
    strip = d.strip("X1", at=c1)
    feed, zero1, zero2, out1, out2 = (strip.terminal("DEMO-TB-2.5", group=group) for _ in range(5))
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=group)
    k2 = d.item("DEMO-RLY-2CO-24", tag="K2", at=c1, group=group)
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    for relay, zero in ((k1, zero1), (k2, zero2)):
        wire(feed.inner, relay.fn("coil")["A1"])
        if relay is k2:
            wire(relay.fn("coil")["A2"], q1["1"])
            wire(q1["2"], zero.inner)
        else:
            wire(relay.fn("coil")["A2"], zero.inner)
        wire(feed.inner, relay.fn("co_1")["11"])
        wire(relay.fn("co_1")["14"], out1.inner)
        wire(feed.inner, relay.fn("co_2")["21"])  # layout-0112: an unwired contact is not drawn
        wire(relay.fn("co_2")["24"], out1.inner)
    wire(k1.fn("co_1")["12"], out2.inner)
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _designation(model: Model, placement: SymbolPlacement) -> str:
    item = items(model)[functions(model)[placement.function].item]
    return own_designation_or_none(model, item) or ""


def _images(model: Model) -> dict:
    """Coil designation -> its contact image label."""
    coils = {p.function: p for p in layout_of(model, SymbolPlacement).values()}
    return {
        _designation(model, coils[label.function]): label
        for label in layout_of(model, Label).values()
        if label.function in coils
        and label.kind is LabelKind.CROSS_REFERENCE
        and label.slot == "contacts"
    }


def _where(model: Model, placement: SymbolPlacement, reader: SymbolPlacement) -> str:
    """Where `placement` is drawn as `reader` prints it: cell only on its page, else p<n>:<cell>."""
    page = layout_of(model, Page)[placement.page]
    column = frame_column(DEFAULT_SHEET.content_width, DEFAULT_SHEET.frame_columns, placement.x)
    row = frame_row(DEFAULT_SHEET.content_height, DEFAULT_SHEET.frame_rows, placement.y)
    own = layout_of(model, Page)[reader.page].number
    return position_text(page.number, column, row, (), own_page=own)


def _placement(model: Model, tag: str, function: str) -> SymbolPlacement:
    (found,) = (
        p
        for p in layout_of(model, SymbolPlacement).values()
        if _designation(model, p) == tag and functions(model)[p.function].name == function
    )
    return found


def _box(model: Model, label: Label) -> tuple[int, int, int, int]:
    """The image's (x0, y0, x1, y1): two columns as wide as the longest entry, one row per line."""
    lines = label_text(model, label).split("\n")
    column = (
        max(text_width(part, height=_TEXT) for line in lines for part in line.split(" | "))
        + 2 * _PAD
    )
    return label.x, label.y, label.x + 2 * column, label.y + len(lines) * _TEXT + 3 * _PAD


def _geometry(placement: SymbolPlacement):
    """The library geometry of the symbol `placement` draws, in its orientation."""
    return symbol_geometry(
        placement.symbol,
        poles=placement.poles,
        orientation=Orientation(placement.orientation.value),
    )


def _lane_x(coil: SymbolPlacement) -> int:
    """The x of the coil's wire: its symbol origin plus its first port."""
    return coil.x + _geometry(coil).ports[0].at.x


# ---- D7: the image's content ---------------------------------------------------------------


def test_the_cabinet_coil_lists_every_contact_with_where_it_is_drawn() -> None:
    """D7: NO | NC columns, one entry per contact pair "1-2 /1.3", main contacts before aux."""
    # UNDO: fransys_model/derive/drawing_text.py contact_image: sort `no` descending, or
    # drop the `where` from the entry text.
    model = _cabinet()
    coil = _placement(model, "K1", "coil")
    main, aux = _placement(model, "K1", "main"), _placement(model, "K1", "aux")
    rows = label_text(model, _images(model)["K1"]).split("\n")
    assert rows == [
        "NO | NC",
        *(f"{pair} {_where(model, main, coil)} | " for pair in ("1-2", "3-4", "5-6")),
        f"13-14 {_where(model, aux, coil)} | ",
    ]


def test_a_changeover_contact_is_listed_in_both_columns() -> None:
    """D7: a 2CO relay's contact 11 appears as 11-14 under NO and 11-12 under NC."""
    # UNDO: fransys_model/derive/drawing_text.py contact_image, CONTACT_CO branch: append
    # only to `no` (drop the `nc.append`).
    model = _relays()
    where = {
        tag: _where(model, _placement(model, tag, "co_1"), _placement(model, tag, "coil"))
        for tag in ("K1", "K2")
    }
    for tag in ("K1", "K2"):
        rows = label_text(model, _images(model)[tag]).split("\n")
        second = _where(model, _placement(model, tag, "co_2"), _placement(model, tag, "coil"))
        assert rows == [
            "NO | NC",
            f"11-14 {where[tag]} | 11-12 {where[tag]}",
            f"21-24 {second} | 21-22 {second}",
        ]


def test_each_contact_cross_reference_line_carries_its_coils_position() -> None:
    """D7: the contact's own line under its tag names the coil's page and column."""
    # UNDO: stages/images.py `contact_images`: `RequestPartner(... x=home[s.function]
    # .at.x)` instead of `at.at.x` (label_text reads the partner x, not the request `text=`).
    for model, tag, functions_of in (
        (_cabinet(), "K1", ("main", "aux")),
        (_relays(), "K2", ("co_1", "co_2")),
    ):
        coil = _placement(model, tag, "coil")
        for name in functions_of:
            contact = _placement(model, tag, name)
            (line,) = (
                label
                for label in layout_of(model, Label).values()
                if label.function == contact.function
                and label.slot == "tag"
                and label.kind is LabelKind.CROSS_REFERENCE
            )
            assert label_text(model, line) == _where(model, coil, contact)
            assert [partner.x for partner in line.partners] == [coil.x]


def _centre_cell(model: Model, placement: SymbolPlacement, reader: SymbolPlacement) -> str:
    """The text for `placement`'s frame cell at its drawn body's centre, as `reader` prints it."""
    body = _geometry(placement).body
    centre_y = placement.y + body.y + body.height // 2
    page = layout_of(model, Page)[placement.page]
    column = frame_column(DEFAULT_SHEET.content_width, DEFAULT_SHEET.frame_columns, placement.x)
    row = frame_row(DEFAULT_SHEET.content_height, DEFAULT_SHEET.frame_rows, centre_y)
    return position_text(
        page.number, column, row, (), own_page=layout_of(model, Page)[reader.page].number
    )


def test_a_contacts_partner_text_names_the_cell_of_the_coils_drawn_body_centre() -> None:
    """RR-O5-FIX: the contact's coil position is the frame cell holding the coil body's centre."""
    # UNDO: derive/drawing_text.py `_partner_row`: `placement.y + 142` (one row down) fails the
    # cabinet K1 and the relays K1, K2.
    checked = 0
    for model, tag, functions_of in (
        (_cabinet(), "K1", ("main", "aux")),
        (_relays(), "K1", ("co_1", "co_2")),
        (_relays(), "K2", ("co_1", "co_2")),
    ):
        coil = _placement(model, tag, "coil")
        for name in functions_of:
            contact = _placement(model, tag, name)
            (line,) = (
                label
                for label in layout_of(model, Label).values()
                if label.function == contact.function
                and label.slot == "tag"
                and label.kind is LabelKind.CROSS_REFERENCE
            )
            assert label_text(model, line) == _centre_cell(model, coil, contact)
            checked += 1
    assert checked == 6


# ---- D7: where the image stands ---------------------------------------------------------------


def test_images_of_one_page_row_share_the_lowest_baseline_any_of_them_needs() -> None:
    """D7: coils on one row share one image y, lower than the higher coil's own foot needs."""
    # UNDO: stages/images.py `contact_images`, the row loop at its end: use
    # `label.box.y` instead of `max(one.box.y for one in row)`.
    model = _relays()
    images, keepouts = _images(model), {}
    for tag in ("K1", "K2"):
        coil = _placement(model, tag, "coil")
        keepouts[tag] = max(
            p.y + _geometry(p).keepout.y + _geometry(p).keepout.height
            for p in layout_of(model, SymbolPlacement).values()
            if p.page == coil.page and p.x == coil.x
        )
    assert _placement(model, "K1", "coil").y == _placement(model, "K2", "coil").y
    assert images["K1"].y == images["K2"].y
    needs = {tag: keepouts[tag] + _PAD for tag in images}
    assert needs["K1"] < needs["K2"] <= images["K2"].y  # K1's own foot is higher: it is lowered
    # the row's image stands at K2's own foot, the lowest need, and no lower (K2's coil is pushed
    # down by X1 over K1, V4, so a half-page bound would say nothing)
    assert images["K2"].y == needs["K2"]


def test_an_image_stands_under_its_coils_cells_and_clear_of_markers() -> None:
    """D7: room below the coil's column and its markers; no marker box under the image's box."""
    # UNDO: stages/images.py `contact_images`: `if False and below:` (the foot rule).
    # Only the foot rule is pinned: no fixture has a marker below a coil, so the `here` marker
    # loop (image pushed under a marker) is NOT exercised by this test.
    for model in (_cabinet(), _relays()):
        for tag, image in _images(model).items():
            coil = _placement(model, tag, "coil")
            x0, y0, x1, y1 = _box(model, image)
            column = [
                p
                for p in layout_of(model, SymbolPlacement).values()
                if p.page == coil.page and p.x == coil.x
            ]
            for p in column:
                k = _geometry(p).keepout
                assert y0 >= p.y + k.y + k.height, (tag, p.symbol)
            for m in layout_of(model, LinkMarker).values():
                if m.page == image.page and m.x < x1 and m.x + m.width > x0:
                    assert m.y + m.height <= y0 or m.y >= y1, (tag, m.x, m.y)


def test_no_wire_crosses_a_contact_image() -> None:
    """D7: no route segment enters the interior of any image box."""
    # UNDO: no single mutation fails this test. It fails only with all three together: image
    # centred on the lane (`x = lane - width // 2`), the foot rule dropped (`if False and
    # below`), and the image removed from the router's obstacles (stages/pagerun.py
    # `finish_page` `held` skipping slot "contacts"). It is a safety net, not a can-fail pin.
    checked = 0
    for model in (_cabinet(), _relays()):
        images = [(_box(model, image), image.page) for image in _images(model).values()]
        for (x0, y0, x1, y1), page in images:
            checked += 1
            for route in layout_of(model, Route).values():
                if route.page != page:
                    continue
                for a, b in zip(route.points, route.points[1:], strict=False):
                    low_x, high_x = sorted((a.x, b.x))
                    low_y, high_y = sorted((a.y, b.y))
                    assert not (low_x < x1 and high_x > x0 and low_y < y1 and high_y > y0), (
                        route.id,
                        (a.x, a.y),
                        (b.x, b.y),
                    )
    assert checked >= 4


# ---- D14: the image's near edge -------------------------------------------------------------


def test_an_image_keeps_one_offset_from_its_coils_wire_whatever_its_size() -> None:
    """D14: every image's left edge stands the same distance right of its coil's wire."""
    # UNDO: stages/images.py `contact_images`: `x = lane - width // 2` (centre it) or
    # `x = lane + width // 4`.
    offsets, sizes = set(), set()
    for model in (_cabinet(), _relays()):
        for tag, image in _images(model).items():
            offsets.add(image.x - _lane_x(_placement(model, tag, "coil")))
            x0, y0, x1, y1 = _box(model, image)
            sizes.add((x1 - x0, y1 - y0))
    assert len(sizes) >= 3
    assert len(offsets) == 1
    assert 0 < offsets.pop() <= WIRING_GRID
