"""The row graph: separation between columns, row width, justify, a card's pins and overflow."""

from itertools import pairwise

from fransys_layout.core.geometry import column_extent
from fransys_layout.core.pack import PlacedColumn, attachments
from fransys_layout.core.pack_row import RowSpec, row_width, solve_row
from fransys_layout.core.pack_sep import separation
from fransys_layout.core.values import Box, Lane, Options, Sym

from .pack_fixtures import boxpin_end, card, card_block, column, elem, free_block, lane, placed

NONE: frozenset[str] = frozenset()


def free_row(names: tuple[str, ...], syms: dict[str, Sym], options: Options) -> RowSpec:
    """One free column per name, each holding one cell of the same symbol name."""
    pcs = {f"c{i}": placed(f"c{i}", n) for i, n in enumerate(names)}
    block = free_block("f", tuple(pcs))
    return RowSpec(tuple(pcs), (block,), pcs, syms, NONE, options, {})


def test_two_free_columns_sit_at_the_separation() -> None:
    """Left-packed, the second column stands exactly `separation` right of the first."""
    syms = {"a": elem("a", footprint=Box(-20, -16, 40, 32)), "b": elem("b")}
    options = Options(justify=False)
    spec = free_row(("a", "b"), syms, options)
    x, _ = solve_row(spec, 1312)
    assert x["col:c1"] - x["col:c0"] == separation(
        spec.pcs["c0"], spec.pcs["c1"], syms, NONE, options
    )
    assert x["col:c0"] == options.margin.w + 20


def test_row_width_of_one_column_equals_its_extent() -> None:
    """The width leaves the left margin out, so a lone column measures its own footprint."""
    syms = {"a": elem("a", footprint=Box(-20, -16, 40, 32))}
    spec = free_row(("a",), syms, Options())
    lanes = (Lane(spec.pcs["c0"].lanes[0], 0),)
    lo, hi = column_extent(syms, lanes, NONE)
    assert row_width(spec) == hi - lo == 40


def test_row_width_counts_the_gap_between_columns() -> None:
    """A free column, then a card with no columns: width is the column, the gap, the card body."""
    syms = {"a": elem("a"), "box": card("box", 2)}
    pcs = {"c0": placed("c0", "a")}
    blocks = (free_block("f", ("c0",)), card_block("box", (), ()))
    options = Options()
    spec = RowSpec(("c0",), blocks, pcs, syms, NONE, options, {})
    assert row_width(spec) == 16 + options.column_gap_min + syms["box"].body.w


def test_justify_spreads_a_row_to_the_right_margin() -> None:
    """Four 100 G columns pack left; justify widens the three gaps up to the right margin."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    names = ("a",) * 4
    page_w = 800
    limit = page_w - Options().margin.w

    def right_edge(options: Options) -> int:
        spec = free_row(names, syms, options)
        return max(
            x + 50 for node, x in solve_row(spec, page_w)[0].items() if node.startswith("col:")
        )

    assert limit - 3 * 8 <= right_edge(Options(justify=True)) <= limit
    assert right_edge(Options(justify=False)) < limit - 100


def test_a_cards_attached_columns_stand_under_their_spread_pins() -> None:
    """Pins keep box_pin_pitch_min apart though their narrow columns would stand closer."""
    syms = {"box": card("box", 3), "a": elem("a", body=Box(-2, -16, 4, 32))}
    cols = tuple(column(f"c{i}", lane("a"), head=boxpin_end("box", f"p{i}")) for i in (1, 2, 3))
    block = card_block("box", tuple(c.id for c in cols), tuple((f"p{i}", "S") for i in (1, 2, 3)))
    attach = attachments(cols, {block.id: block})
    pcs = {c.id: PlacedColumn(c.id, (c.lanes[0].cells,), (0,), 0, flipped=False) for c in cols}
    options = Options(justify=False, box_pin_pitch_min=40)
    spec = RowSpec(tuple(pcs), (block,), pcs, syms, NONE, options, attach)
    x, _ = solve_row(spec, 1312)
    pins = [x[f"pin:box:p{i}"] for i in (1, 2, 3)]
    assert [b - a for a, b in pairwise(pins)] == [40, 40]
    assert [x[f"col:c{i}"] for i in (1, 2, 3)] == pins


def test_a_row_wider_than_the_page_comes_back_left_packed() -> None:
    """Positions are those of justify off; row_width exceeds the page and the caller reads it."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    page_w = 250
    spec = free_row(("a",) * 4, syms, Options(justify=True))
    off = free_row(("a",) * 4, syms, Options(justify=False))
    assert solve_row(spec, page_w)[0] == solve_row(off, page_w)[0]
    assert row_width(spec) > page_w - spec.options.margin.w


def test_a_fitting_row_has_no_overflow() -> None:
    """The overflow beside the positions is 0 when the row ends inside the page."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    spec = free_row(("a",) * 2, syms, Options(justify=True))
    assert solve_row(spec, 800)[1] == 0


def test_a_row_24_g_too_wide_reports_24() -> None:
    """The overflow is the G the left-packed row ends past the page's right margin."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    spec = free_row(("a",) * 4, syms, Options(justify=True))
    fits = row_width(spec) + spec.options.margin.w * 2
    x, overflow = solve_row(spec, fits - 24)
    assert overflow == 24
    assert x == solve_row(free_row(("a",) * 4, syms, Options(justify=False)), fits - 24)[0]
