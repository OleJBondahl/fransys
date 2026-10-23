"""The row graph: separation between columns, row width, justify, a card's pins and overflow."""

from dataclasses import replace
from itertools import pairwise

from options_fixtures import core_options

from fransys_layout.core.geometry import column_extent
from fransys_layout.core.node_names import COL, col_node, pin_node
from fransys_layout.core.pack import PlacedColumn, attachments
from fransys_layout.core.pack_row import RowSpec, row_width, solve_row
from fransys_layout.core.pack_sep import separation
from fransys_layout.core.values import Box, Lane, Options
lazy from fransys_layout.core.sym_values import Sym

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
    options = core_options(
        justify=False,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    spec = free_row(("a", "b"), syms, options)
    x, _ = solve_row(spec, 1312)
    assert x[col_node("c1")] - x[col_node("c0")] == separation(
        spec.pcs["c0"], spec.pcs["c1"], syms, NONE, options
    )
    assert x[col_node("c0")] == options.margin.w + 20


def test_row_width_of_one_column_equals_its_extent() -> None:
    """The width leaves the left margin out, so a lone column measures its own footprint."""
    syms = {"a": elem("a", footprint=Box(-20, -16, 40, 32))}
    spec = free_row(
        ("a",),
        syms,
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    lanes = (Lane(spec.pcs["c0"].lanes[0], 0),)
    lo, hi = column_extent(syms, lanes, NONE)
    assert row_width(spec) == hi - lo == 40


def test_row_width_counts_the_gap_between_columns() -> None:
    """A free column, then a card with no columns: width is the column, the gap, the card body."""
    syms = {"a": elem("a"), "box": card("box", 2)}
    pcs = {"c0": placed("c0", "a")}
    blocks = (free_block("f", ("c0",)), card_block("box", (), ()))
    options = core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    spec = RowSpec(("c0",), blocks, pcs, syms, NONE, options, {})
    assert row_width(spec) == 16 + options.column_gap_min + syms["box"].body.w


def test_justify_spreads_a_row_to_the_right_margin() -> None:
    """Four 100 G columns pack left; justify widens the three gaps up to the right margin."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    names = ("a",) * 4
    page_w = 800
    limit = (
        page_w
        - core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ).margin.w
    )

    def right_edge(options: Options) -> int:
        spec = free_row(names, syms, options)
        return max(x + 50 for node, x in solve_row(spec, page_w)[0].items() if node.startswith(COL))

    assert (
        limit - 3 * 8
        <= right_edge(
            core_options(
                justify=True,
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            )
        )
        <= limit
    )
    assert (
        right_edge(
            core_options(
                justify=False,
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            )
        )
        < limit - 100
    )


def test_a_cards_attached_columns_stand_under_their_spread_pins() -> None:
    """Pins keep box_pin_pitch_min apart though their narrow columns would stand closer."""
    syms = {"box": card("box", 3), "a": elem("a", body=Box(-2, -16, 4, 32))}
    cols = tuple(column(f"c{i}", lane("a"), head=boxpin_end("box", f"p{i}")) for i in (1, 2, 3))
    block = card_block("box", tuple(c.id for c in cols), tuple((f"p{i}", "S") for i in (1, 2, 3)))
    attach = attachments(cols, {block.id: block})
    pcs = {c.id: PlacedColumn(c.id, (c.lanes[0].cells,), (0,), 0, flipped=False) for c in cols}
    options = core_options(
        justify=False,
        box_pin_pitch_min=40,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    spec = RowSpec(tuple(pcs), (block,), pcs, syms, NONE, options, attach)
    x, _ = solve_row(spec, 1312)
    pins = [x[pin_node("box", f"p{i}")] for i in (1, 2, 3)]
    assert [b - a for a, b in pairwise(pins)] == [40, 40]
    assert [x[col_node(f"c{i}")] for i in (1, 2, 3)] == pins


def test_a_row_wider_than_the_page_comes_back_left_packed() -> None:
    """Positions are those of justify off; row_width exceeds the page and the caller reads it."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    page_w = 250
    spec = free_row(
        ("a",) * 4,
        syms,
        core_options(
            justify=True,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    off = free_row(
        ("a",) * 4,
        syms,
        core_options(
            justify=False,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert solve_row(spec, page_w)[0] == solve_row(off, page_w)[0]
    assert row_width(spec) > page_w - spec.options.margin.w


def test_a_fitting_row_has_no_overflow() -> None:
    """The overflow beside the positions is 0 when the row ends inside the page."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    spec = free_row(
        ("a",) * 2,
        syms,
        core_options(
            justify=True,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert solve_row(spec, 800)[1] == 0


def test_a_row_24_g_too_wide_reports_24() -> None:
    """The overflow is the G the left-packed row ends past the page's right margin."""
    syms = {"a": elem("a", footprint=Box(-50, -16, 100, 32))}
    spec = free_row(
        ("a",) * 4,
        syms,
        core_options(
            justify=True,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    fits = row_width(spec) + spec.options.margin.w * 2
    x, overflow = solve_row(spec, fits - 24)
    assert overflow == 24
    assert (
        x
        == solve_row(
            free_row(
                ("a",) * 4,
                syms,
                core_options(
                    justify=False,
                    flip_turn="R180",
                    tag_stagger=True,
                    label_gap=8,
                    parallel_pitch=48,
                    driver_first=True,
                    arrow_sides=("E", "W"),
                ),
            ),
            fits - 24,
        )[0]
    )


def _two_edge_card(**extra) -> tuple[RowSpec, dict[str, Sym]]:
    """A card: p1, p2 on N under narrow columns, p3, p4 on S under columns wider on the left."""
    syms = {
        "box": card("box", 4),
        "a": elem("a", body=Box(-2, -16, 4, 32)),
        "b": elem("b", body=Box(-40, -16, 44, 32)),
    }
    heads = {"p1": "a", "p2": "a", "p3": "b", "p4": "b"}
    cols = tuple(column(p, lane(s), head=boxpin_end("box", p)) for p, s in heads.items())
    edges = (("p1", "N"), ("p2", "N"), ("p3", "S"), ("p4", "S"))
    block = card_block("box", tuple(c.id for c in cols), edges)
    attach = attachments(cols, {block.id: block})
    pcs = {c.id: PlacedColumn(c.id, (c.lanes[0].cells,), (0,), 0, flipped=False) for c in cols}
    options = core_options(
        box_pin_pitch_min=16,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
        **extra,
    )
    return RowSpec(tuple(pcs), (block,), pcs, syms, NONE, options, attach), syms


def _pin_xs(spec: RowSpec) -> list[int]:
    x, _ = solve_row(spec, 1312)
    return [x[pin_node("box", p)] for p in ("p1", "p2", "p3", "p4")]


def test_paired_edges_put_pin_k_of_each_over_one_x() -> None:
    """The S columns are wider on the left, which alone pushes the S pins right of the N pins."""
    apart, _ = _two_edge_card(justify=False)
    p1, p2, p3, p4 = _pin_xs(apart)
    assert (p3 - p1, p4 - p2) != (0, 0)
    paired, _ = _two_edge_card(justify=False, pin_pairs=(("N", "S"),))
    p1, p2, p3, p4 = _pin_xs(paired)
    assert (p1, p2) == (p3, p4)


def test_justify_cards_off_keeps_the_card_pitch_at_the_footprint_minimum() -> None:
    off, _ = _two_edge_card(justify_cards=False, pin_pairs=(("N", "S"),))
    on, _ = _two_edge_card(justify_cards=True, pin_pairs=(("N", "S"),))
    off_pins, on_pins = _pin_xs(off), _pin_xs(on)
    justify_off, _ = _two_edge_card(justify=False, pin_pairs=(("N", "S"),))
    assert off_pins == _pin_xs(justify_off)
    assert on_pins[1] - on_pins[0] > off_pins[1] - off_pins[0]


def test_a_pin_of_a_column_on_two_pins_is_not_paired() -> None:
    """p3 stands on a column that also holds p4: p1 and p3 do not share an x, and nothing raises."""
    spec, _ = _two_edge_card(justify=False, pin_pairs=(("N", "S"),))
    attach = {c: v for c, v in spec.attach.items() if c in ("p1", "p3")}
    pcs = {c: spec.pcs[c] for c in attach}
    two_pin = replace(spec, cols=tuple(attach), pcs=pcs, attach=attach)
    x, _ = solve_row(replace(two_pin, more_pins={"p3": (("p4", 0),)}), 1312)
    assert x[pin_node("box", "p1")] != x[pin_node("box", "p3")]
    x, _ = solve_row(two_pin, 1312)
    assert x[pin_node("box", "p1")] == x[pin_node("box", "p3")]


def test_edges_with_unequal_pin_counts_are_not_paired() -> None:
    """One N pin against three S pins is no half split: p3 keeps the x its own column gives it."""
    spec, _ = _two_edge_card(justify=False, pin_pairs=(("N", "S"),))
    edges = (("p3", "N"), ("p1", "S"), ("p2", "S"), ("p4", "S"))
    block = replace(spec.blocks[0], pin_edges=edges)
    x, _ = solve_row(replace(spec, blocks=(block,)), 1312)
    assert x[pin_node("box", "p3")] != x[pin_node("box", "p1")]


def test_a_pin_no_column_holds_is_not_paired() -> None:
    """p2 has no column: p2 and p4 do not share an x, and nothing raises; p1 and p3 still pair."""
    spec, _ = _two_edge_card(justify=False, pin_pairs=(("N", "S"),))
    attach = {c: v for c, v in spec.attach.items() if c != "p2"}
    pcs = {c: spec.pcs[c] for c in attach}
    x, _ = solve_row(replace(spec, cols=tuple(attach), pcs=pcs, attach=attach), 1312)
    assert x[pin_node("box", "p1")] == x[pin_node("box", "p3")]
    assert x[pin_node("box", "p2")] != x[pin_node("box", "p4")]
