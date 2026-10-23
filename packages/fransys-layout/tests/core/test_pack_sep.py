"""Separation by overlapping y with hard and soft boxes (layout-0271)."""

import random

from options_fixtures import core_options

from fransys_layout.core.geometry import column_extent, overlaps
from fransys_layout.core.pack_sep import placed_cells, separation
from fransys_layout.core.values import Box, Lane, Options
lazy from fransys_layout.core.sym_values import Sym

from .pack_fixtures import elem, placed


def grid_up(value: int, grid: int) -> int:
    return -(-value // grid) * grid


def full_extent_separation(
    a_syms: tuple[str, ...], b_syms: tuple[str, ...], syms: dict[str, Sym], options: Options
) -> int:
    """The old rule: right reach of a plus left reach of b plus the gap."""
    la = (Lane(placed("a", *a_syms).lanes[0], 0),)
    lb = (Lane(placed("b", *b_syms).lanes[0], 0),)
    right = column_extent(syms, la, frozenset())[1]
    left = column_extent(syms, lb, frozenset())[0]
    return grid_up(right - left + options.column_gap_min, options.wiring_grid)


def test_a_tall_and_a_wide_column_pack_closer_than_their_full_extents() -> None:
    """a is a thin tall cell over a wide one; b is one wide cell level with the thin cell only."""
    thin = elem("thin", body=Box(-8, -50, 16, 100))
    wide = elem("wide", body=Box(-50, -16, 100, 32))
    syms = {s.id: s for s in (thin, wide)}
    options = core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    a, b = placed("a", "thin", "wide"), placed("b", "wide")
    full = full_extent_separation(("thin", "wide"), ("wide",), syms, options)
    packed = separation(a, b, syms, frozenset(), options)
    assert full == 112
    assert packed == 72
    assert packed < full


def test_cells_whose_text_slots_overlap_pack_at_hard_plus_soft_and_not_the_footprints() -> None:
    """Body 16, slots 12 a side: soft meets soft, so 16 + 12 + gap; stagger off, 40 + gap."""
    cell = elem("e", footprint=Box(-20, -16, 40, 32))
    syms = {"e": cell}
    a, b = placed("a", "e"), placed("b", "e")
    assert (
        separation(
            a,
            b,
            syms,
            frozenset(),
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
        == 40
    )
    assert (
        separation(
            a,
            b,
            syms,
            frozenset(),
            core_options(
                tag_stagger=False,
                label_gap=8,
                flip_turn="R180",
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
        == 48
    )


def random_sym(rng: random.Random, sym_id: str) -> Sym:
    """A symbol with a random body, keep-out inside the footprint and text slots."""
    bw, bh = rng.randrange(1, 6) * 8, rng.randrange(1, 6) * 8
    body = Box(-rng.randrange(0, bw + 1), -bh // 2, bw, bh)
    keep = Box(body.x - rng.randrange(0, 3) * 4, body.y, body.w + rng.randrange(0, 3) * 4, bh)
    foot = Box(keep.x - rng.randrange(0, 4) * 4, keep.y, keep.w + rng.randrange(0, 4) * 4, bh)
    return elem(sym_id, body=body, keepout=keep, footprint=foot)


def test_a_hard_box_never_overlaps_another_hard_box() -> None:
    """50 seeded column pairs: at the separation only soft boxes meet other soft boxes."""
    rng = random.Random(0)  # noqa: S311 - seeded test data
    options = core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    for _ in range(50):
        names_a = tuple(f"a{i}" for i in range(rng.randrange(1, 4)))
        names_b = tuple(f"b{i}" for i in range(rng.randrange(1, 4)))
        syms = {n: random_sym(rng, n) for n in (*names_a, *names_b)}
        a, b = placed("a", *names_a), placed("b", *names_b)
        sep = separation(a, b, syms, frozenset(), options)
        for ca in placed_cells(a, syms, frozenset(), options):
            for cb in placed_cells(b, syms, frozenset(), options):
                hard_b = Box(cb.hard.x + sep, cb.hard.y, cb.hard.w, cb.hard.h)
                soft_b = Box(cb.soft.x + sep, cb.soft.y, cb.soft.w, cb.soft.h)
                if ca.top < cb.bottom and cb.top < ca.bottom:
                    assert not overlaps(ca.hard, hard_b)
                    assert not overlaps(ca.hard, soft_b)
                    assert not overlaps(ca.soft, hard_b)


def test_separation_is_on_the_wiring_grid() -> None:
    """Whatever the box sizes, the answer is a multiple of the grid."""
    rng = random.Random(1)  # noqa: S311 - seeded test data
    for grid in (8, 16):
        options = core_options(
            wiring_grid=grid,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        )
        for _ in range(20):
            syms = {n: random_sym(rng, n) for n in ("x", "y")}
            assert (
                separation(placed("a", "x"), placed("b", "y"), syms, frozenset(), options) % grid
                == 0
            )
