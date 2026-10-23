"""The symdef layer's entry points on library symbols (layout-0316 D)."""

import pytest
from options_fixtures import core_options

from electrical_symbols import LIBRARY
from fransys_layout.core import CoreError
from fransys_layout.core.values import Box
from fransys_layout.symbols import (
    Ask,
    LibrarySymbol,
    Shape,
    TableAsk,
    library_symbol,
    marker_views,
    symbol_shape,
    symbol_views,
    with_marker,
)


def views(symbol, orients, **kw):
    return symbol_views(symbol, LIBRARY, Ask(orients, **kw))


def test_the_marker_box_is_measured_at_all_eight_orientations() -> None:
    views = marker_views(library_symbol(LIBRARY, "reference-marker"), LIBRARY)
    assert views["R0"] == Box(0, -8, 48, 16)
    assert len(views) == 8
    assert views["R90"] != views["R0"]
    assert (
        with_marker(
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
            library_symbol(LIBRARY, "reference-marker"),
            LIBRARY,
        ).marker
        == views
    )


@pytest.mark.parametrize("key", ["marker-arrow", "marker-arrow-turned", "marker-box"])
def test_each_marker_symbol_has_a_keepout_box_at_every_orientation(key) -> None:
    views = marker_views(library_symbol(LIBRARY, key), LIBRARY)
    assert len(views) == 8
    assert all(box.w > 0 and box.h > 0 for box in views.values())


def test_an_unknown_key_and_a_repeat_without_a_through_path_raise_naming_the_symbol() -> None:
    with pytest.raises(CoreError, match="no symbol 'nope'"):
        library_symbol(LIBRARY, "nope")
    with pytest.raises(CoreError, match="'earth' cannot be repeated 3 times"):
        library_symbol(LIBRARY, "earth", 3)


def test_a_repeated_symbol_has_one_pin_set_per_repeat() -> None:
    single = symbol_shape(library_symbol(LIBRARY, "circuit-breaker"), LIBRARY)
    triple = symbol_shape(library_symbol(LIBRARY, "circuit-breaker", 3), LIBRARY)
    assert len(triple.pins) == 3 * len(single.pins)


def _coil() -> tuple[LibrarySymbol, Shape]:
    symbol = library_symbol(LIBRARY, "coil")
    return symbol, symbol_shape(symbol, LIBRARY)


def test_the_text_widens_the_slot_and_the_label_is_that_slot() -> None:
    symbol, shape = _coil()
    order = list(shape.pins)
    plain = views(symbol, ("R0",), order=order, text_slot="tag", text="K1", text_height=8)
    long = views(
        symbol, ("R0",), order=order, text_slot="tag", text="K1234567.12345", text_height=8
    )
    assert plain.label.w == shape.slots["tag"].w
    assert long.label.w > plain.label.w
    assert long.views["R0"].footprint == plain.views["R0"].footprint  # text is no footprint (R327)
    assert long.views["R0"].keepout == plain.views["R0"].keepout  # the keep-out is as reserved


def test_a_missing_text_slot_gives_no_label() -> None:
    symbol = library_symbol(LIBRARY, "bridge-tick")
    drawn = views(symbol, ("R0",), order=[], text_slot="tag", text="X", text_height=8)
    assert (drawn.label.w, drawn.label.h) == (0, 0)


def test_the_pins_follow_the_given_order_at_each_orientation() -> None:
    symbol, shape = _coil()
    drawn = views(
        symbol,
        ("R0", "R180"),
        order=["out", "in"],
        text_slot="tag",
        text="K1",
        text_height=8,
    )
    assert drawn.views["R0"].pins == (shape.pins["out"], shape.pins["in"])
    assert drawn.views["R180"].pins[0].dy == -shape.pins["out"].dy


def test_a_strip_row_footprint_leaves_the_text_slot_out() -> None:
    symbol, shape = _coil()
    kw = {"order": list(shape.pins), "text_slot": "tag", "text": "K1", "text_height": 8}
    row = views(symbol, ("R0",), strip=True, **kw).views["R0"]
    held = views(symbol, ("R0",), **kw).views["R0"]
    assert held.row_footprint is None
    assert row.row_footprint is not None
    assert row.row_footprint.w < row.footprint.w


def _table(*texts: dict[str, str], at=(-56, 16)) -> TableAsk:
    return TableAsk(
        library_symbol(LIBRARY, "contact-row"), library_symbol(LIBRARY, "contact-head"), texts, at
    )


def _coil_with(table: TableAsk | None, orients=("R0", "R180")):
    symbol, shape = _coil()
    kw = {"order": list(shape.pins), "text_slot": "tag", "text": "K1", "text_height": 8}
    return views(symbol, orients, table=table, **kw)


def test_the_table_is_not_part_of_any_footprint() -> None:
    """R327: the table is an Anchor's outline; the coil's views are the same with or without it."""
    bare = _coil_with(None).views
    drawn = _coil_with(_table({"no": "13 /1.1", "nc": "21 /1.1"})).views
    assert drawn == bare


def test_the_table_is_as_wide_as_its_longest_text_and_its_head_is_always_set() -> None:
    short = _coil_with(_table({"no": "13 /1.1"})).table
    rows = [{"no": "13 /1.1"}] * 5 + [{"no": "13 /1.1 and a much longer text"}]
    long = _coil_with(_table(*rows)).table
    assert long.w > short.w
    assert short.h == 8 + 12 + 2  # a row, the titles and rule, the closing pad
    assert long.h == 6 * 8 + 12 + 2


def test_no_table_gives_no_table_view() -> None:
    assert _coil_with(None).table is None


def test_the_table_top_left_is_put_at_the_asked_point() -> None:
    table = _coil_with(_table({"no": "13 /1.1"}, at=(-56, 40))).table
    assert (table.x, table.y) == (-56, 40)


def test_no_r0_is_refused() -> None:
    symbol, _shape = _coil()
    with pytest.raises(CoreError, match="no R0"):
        views(symbol, ("R180",), order=[], text_slot="tag", text="K", text_height=8)


def _headed(*texts: dict[str, str], heading: str | None) -> TableAsk:
    head = "contact-head" if heading is None else "contact-head-headed"
    return TableAsk(
        library_symbol(LIBRARY, "contact-row"),
        library_symbol(LIBRARY, head),
        texts,
        (-56, 16),
        heading,
    )


def test_a_heading_makes_the_table_one_module_higher_and_wider_when_it_is_the_widest_text() -> None:
    cells = {"no": "13 /1.1", "nc": "21 /1.1"}
    plain = _coil_with(_headed(cells, heading=None)).table
    short = _coil_with(_headed(cells, heading="-K1")).table
    long = _coil_with(_headed(cells, heading="-U1-K1234567890123")).table
    assert short.h == plain.h + 8
    assert (short.w, short.x, short.y) == (plain.w, plain.x, plain.y)
    assert long.w > short.w
    assert long.h == short.h


def test_a_table_without_a_heading_is_the_unheaded_table() -> None:
    cells = {"no": "13 /1.1", "nc": "21 /1.1"}
    assert _coil_with(_headed(cells, heading=None)).table == _coil_with(_table(cells)).table
